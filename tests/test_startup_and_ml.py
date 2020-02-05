import os
import sys
import asyncio
import logging
import yaml
import pytest
import json
import random
import pickle

import aiohttp_jinja2
import jinja2
from aiohttp import web

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression

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
    json_tech = json.load(open("models/attack_dict.json", "r", encoding="utf_8"))
    list_of_techs = ['Indicator Removal from Tools', 'Windows Management Instrumentation', 'Screen Capture', 'System Owner/User Discovery', 'Credential Dumping', 'Audio Capture', 'Timestomp', 'Permission Groups Discovery', 'Email Collection', 'Data from Removable Media', 'Code Signing', 'Process Hollowing', 'Spearphishing Link', 'Security Software Discovery', 'Disabling Security Tools', 'Automated Collection', 'Clipboard Data', 'System Service Discovery', 'Network Share Discovery', 'Peripheral Device Discovery', 'System Information Discovery', 'Standard Application Layer Protocol', 'Scheduled Task', 'Execution through API', 'Custom Cryptographic Protocol', 'Replication Through Removable Media', 'Data from Local System', 'Deobfuscate/Decode Files or Information', 'Masquerading', 'Process Injection', 'DLL Search Order Hijacking', 'New Service', 'Application Window Discovery', 'Standard Cryptographic Protocol', 'Binary Padding', 'Remote Desktop Protocol', 'File Deletion', 'Modify Registry', 'Rundll32', 'Regsvr32', 'Spearphishing Attachment', 'Video Capture', 'Software Packing', 'System Network Configuration Discovery', 'Account Discovery', 'Connection Proxy', 'Command-Line Interface', 'Indicator Removal on Host', 'File and Directory Discovery', 'Data Staged', 'System Network Connections Discovery', 'Scripting', 'Web Service', 'User Execution', 'Process Discovery', 'Exfiltration Over Command and Control Channel', 'Registry Run Keys / Startup Folder', 'Shortcut Modification', 'Exfiltration Over Alternative Protocol', 'Data Obfuscation', 'Valid Accounts', 'DLL Side-Loading', 'Exploitation for Privilege Escalation', 'Obfuscated Files or Information', 'Data Compressed', 'Credentials in Files', 'Input Capture', 'Exploitation for Client Execution', 'Standard Non-Application Layer Protocol', 'Query Registry', 'Uncommonly Used Port', 'Bypass User Account Control', 'Data Encoding', 'Data Encrypted', 'Drive-by Compromise', 'Access Token Manipulation', 'Create Account', 'Remote System Discovery', 'Network Service Scanning', 'Remote File Copy', 'Fallback Channels', 'System Time Discovery', 'Service Execution', 'PowerShell', 'Custom Command and Control Protocol', 'Commonly Used Port', 'Windows Admin Shares']
    true_negs = ["This is a generic sentance","There aren't any relations to techniques in this senatnce","Random gibberish that blah blah blah!","Four score and seven years ago..."]
    #for tech in list_of_techs:
    i = random.randint(0,len(list_of_techs)-1) # randomize the selection for building
    cv,logreg = await ml_svc.build_models(list_of_techs[i],json_tech,true_negs)
    assert type(cv) is CountVectorizer
    assert type(logreg) is LogisticRegression
        #pass # test building model and saving it


@pytest.mark.asyncio
async def test_ml_performance():
    if os.path.isfile('models/model_dict.p'):
        model_dict = pickle.load(open('models/model_dict.p', 'rb'))

    pass # load model from store, test models performance

@pytest.mark.asyncio
async def test_delete_db(): # cleanup tests
    os.remove('database/tram.db')
    assert os.path.isfile("database/tram.db") == False
