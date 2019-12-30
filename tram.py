import os
import sys
import argparse
import asyncio
import logging
import traceback

import aiohttp_jinja2
import jinja2
from aiohttp import web

from handlers.web_api import WebAPI
from service.data_svc import DataService
from service.web_svc import WebService
from service.reg_svc import RegService
from service.ml_svc import MLService
from service.rest_svc import RestService

from database.dao import Dao


@asyncio.coroutine
async def background_tasks(build=None, buildfile=None):
    """
    Function to run background tasks at startup

    :param build: Expects 'taxii' or 'json' to specify the build type.
                    If none is specified, then no action will be taken.
    :param buildfile: Expects a path to the enterprise attack json if the 'json' build method is called.
    :return: nil
    """
    if build:
        await data_svc.reload_database()
        if build == 'taxii':
            try:
                await data_svc.insert_attack_stix_data()
            except Exception as exc:
                logging.critical('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
                                 'COULD NOT CONNECT TO TAXII SERVERS: {}\nPLEASE UTILIZE THE OFFLINE CAPABILITY FLAG '
                                 '"-FF" FOR OFFLINE DATABASE BUILDING\n'
                                 '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'.format(exc))
                sys.exit()
        elif build == 'json' and buildfile:
            await data_svc.insert_attack_json_data(buildfile)


@asyncio.coroutine
async def init(host, port):
    """
    Function to initialize the aiohttp app

    :param host: Address to reach webserver on
    :param port: Port to listen on
    :return: nil
    """
    logging.info('server starting: %s:%s' % (host, port))
    app = web.Application()

    app.router.add_route('GET', '/', website_handler.index)
    app.router.add_route('GET', '/edit/{file}', website_handler.edit)
    app.router.add_route('GET', '/about', website_handler.about)
    app.router.add_route('*', '/rest', website_handler.rest_api)
    app.router.add_route('GET', '/export/{file}', website_handler.pdf_export)
    app.router.add_static('/theme/', 'webapp/theme/')

    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('webapp/html'))

    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, host, port).start()


def main(host, port, build=False, buildfile=None):
    """
    Main function to start app
    :param host: Address to reach webserver on
    :param port: Port to listen on
    :param build: Expects 'taxii' or 'json' to specify the build type.
                    If none is specified, then no action will be taken.
    :param buildfile: Expects a path to the enterprise attack json if the 'json' build method is called.
    :return: nil
    """
    loop = asyncio.get_event_loop()
    loop.create_task(background_tasks(build=build, buildfile=buildfile))
    loop.create_task(ml_svc.check_nltk_packs())
    loop.run_until_complete(init(host, port))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Welcome to the system')
    parser.add_argument('-H', '--host', required=False, default='0.0.0.0', help='Define the host for the application '
                                                                                'to listen on')
    parser.add_argument('-P', '--port', required=False, default=9999, help='Define the port to listen on')
    parser.add_argument('-fb', '--force_build', required=False, default=False, action='store_true', help='Force a '
                                                                                                     'Database rebuild')
    parser.add_argument('-ff', '--force_file', help='Input your enterprise att&ck json file from here: ' +
                        'https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json' +
                        ' for offline database building',
                        metavar='file')
    args = parser.parse_args()
    logging.getLogger().setLevel('DEBUG')

    dao = Dao(os.path.join('database', 'tram.db'))

    build, buildfile = None, None
    # Check for force build from offline file
    if args.force_file and bool(os.path.isfile(os.path.abspath(args.force_file))):
        logging.debug("Building model from static file")
        args.force_build = True
        attack_dict = os.path.abspath(args.force_file)
        build, buildfile = 'json', attack_dict

    else:
        # Added 'not' before isfile; the logic was backwards and would always evaluate to True if the file DID exist
        if (not os.path.isfile(os.path.join('database', 'tram.db')) or args.force_build):
            build, buildfile = 'taxii', None

    # Start services and initiate main function
    web_svc = WebService()
    reg_svc = RegService(dao=dao)
    data_svc = DataService(dao=dao, web_svc=web_svc)
    ml_svc = MLService(web_svc=web_svc, dao=dao)
    rest_svc = RestService(web_svc, reg_svc, data_svc, ml_svc, dao)
    services = dict(dao=dao, data_svc=data_svc, ml_svc=ml_svc, reg_svc=reg_svc, web_svc=web_svc, rest_svc=rest_svc)
    website_handler = WebAPI(services=services)
    main(args.host, args.port, build=build, buildfile=buildfile)

