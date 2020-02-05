import os
import sys
import asyncio
import logging
import yaml
import pytest

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

dao = Dao(os.path.join('database', 'tram.db'))

web_svc = WebService()
reg_svc = RegService(dao=dao)
data_svc = DataService(dao=dao, web_svc=web_svc)
ml_svc = MLService(web_svc=web_svc, dao=dao)
rest_svc = RestService(web_svc, reg_svc, data_svc, ml_svc, dao)
services = dict(dao=dao, data_svc=data_svc, ml_svc=ml_svc, reg_svc=reg_svc, web_svc=web_svc, rest_svc=rest_svc)
website_handler = WebAPI(services=services)

@pytest.mark.asyncio
async def test_config_build():
    with open('conf/config.yml') as c:
        config = yaml.safe_load(c)
        conf_build = config['build']
        host = config['host']
        port = config['port']
        assert conf_build == True
        assert host == '0.0.0.0'
        assert port == 9999
        taxii_local = config['taxii-local']
        json_file = os.path.join('models', config['json_file'])
        attack_dict = None
        assert json_file == 'models/enterprise-attack.json'
        assert taxii_local == 'taxii-server'
        if conf_build:
            build = True
            if taxii_local == 'local-json' and bool(os.path.isfile(json_file)):
                logging.debug("Will build model from static file")
                attack_dict = os.path.abspath(json_file)

@pytest.mark.asyncio
async def test_bg_tasks_online():
    await data_svc.reload_database()
    await data_svc.insert_attack_stix_data()
    criteria = dict(name='Mimikatz')
    check = await dao.get('attack_uids',criteria=criteria)
    assert check[0]['description'] == "[Mimikatz](https://attack.mitre.org/software/S0002) is a credential dumper capable of obtaining plaintext Windows account logins and passwords, along with many other features that make it useful for testing the security of networks. (Citation: Deply Mimikatz) (Citation: Adsecurity Mimikatz Guide)"

@pytest.mark.asyncio
async def test_build_model():
    pass # test building model and saving it


@pytest.mark.asyncio
async def test_ml_performance():
    pass # load model from store, test models performance

@pytest.mark.asyncio
async def test_delete_db(): # cleanup
    os.remove('database/tram.db')
    assert os.path.isfile("database/tram.db") == False