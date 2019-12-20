import os
import argparse
import asyncio
import logging

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
async def background_tasks(build):
    if build:
        await data_svc.reload_database()
        await data_svc.insert_attack_data()


@asyncio.coroutine
async def init(address, port):
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
    await web.TCPSite(runner, address, port).start()


def main(host, port, build=False):
    loop = asyncio.get_event_loop()
    loop.create_task(background_tasks(build))
    loop.run_until_complete(init(host, port))
    try:
        logging.debug('server starting: %s:%s' % (host, port))
        loop.run_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Welcome to the system')
    parser.add_argument('-H', '--host', required=False, default='0.0.0.0')
    parser.add_argument('-P', '--port', required=False, default=9999)
    parser.add_argument('-fb', '--force_build', required=False, default=False, action='store_true')
    args = parser.parse_args()
    logging.getLogger().setLevel('DEBUG')

    dao = Dao(os.path.join('database', 'tram.db'))

    if not os.path.isfile(os.path.join('database', 'tram.db')) or args.force_build:
        build = True
    else:
        build = False

    web_svc = WebService()
    reg_svc = RegService(dao=dao)
    data_svc = DataService(dao=dao, web_svc=web_svc)
    ml_svc = MLService(web_svc=web_svc, dao=dao)
    rest_svc = RestService(web_svc, reg_svc, data_svc, ml_svc, dao)
    services = dict(dao=dao, data_svc=data_svc, ml_svc=ml_svc, reg_svc=reg_svc, web_svc=web_svc, rest_svc=rest_svc)
    website_handler = WebAPI(services=services)
    main(args.host, args.port, build=build)

