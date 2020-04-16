import yaml
import os
import logging
import uvicorn

from fastapi import FastAPI
from service.handler import ServiceHandler
from handlers.api import api_core

from service.retrain_svc import RetrainingService
app = FastAPI()


@app.on_event("startup")
async def startup_event():
    if(os.path.isfile('database/tram.db')):
        build = False
    else:
        build = True

    if(build):
        if taxii_local == 'local-json' and bool(os.path.isfile(json_file)):
            logging.debug("Will build model from static file")
            attack_dict = os.path.abspath(json_file)
            await handler.data_svc.reload_database()
            await handler.data_svc.insert_attack_json_data(attack_dict)
        else:
            await handler.data_svc.reload_database()
            await handler.data_svc.insert_attack_stix_data()


def main(host, port, taxii_local=False, build=False, json_file=None):
    app.mount("/", api_core)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == '__main__':

    with open('conf/config.yml') as conf:
        config = yaml.safe_load(conf)
        conf_build = config['build']
        config_host = config['host']
        config_port = config['port']
        taxii_local = config['taxii-local']
        json_file = os.path.join('models', config['json_file'])
        attack_dict = None
    handler = ServiceHandler()
    main(config_host, config_port, taxii_local=taxii_local, json_file=attack_dict)


