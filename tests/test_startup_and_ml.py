import os
import sys
import asyncio
import logging
import yaml
import pytest
import json
import random
import pickle
import pandas as pd
import numpy as np
import logging

import aiohttp_jinja2
import jinja2
from aiohttp import web

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

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
    list_of_techs = ['Indicator Removal from Tools', 'Windows Management Instrumentation', 'Screen Capture', 'System Owner/User Discovery', 'Credential Dumping', 'Audio Capture', 'Timestomp', 'Permission Groups Discovery',
     'Email Collection', 'Data from Removable Media', 'Code Signing', 'Process Hollowing', 'Spearphishing Link', 'Security Software Discovery', 'Disabling Security Tools', 'Automated Collection', 'Clipboard Data', 'System Service Discovery',
      'Network Share Discovery', 'Peripheral Device Discovery', 'System Information Discovery', 'Standard Application Layer Protocol', 'Scheduled Task', 'Execution through API', 'Custom Cryptographic Protocol', 
      'Replication Through Removable Media', 'Data from Local System', 'Deobfuscate/Decode Files or Information', 'Masquerading', 'Process Injection', 'DLL Search Order Hijacking', 'New Service', 'Application Window Discovery', 
      'Standard Cryptographic Protocol', 'Binary Padding', 'Remote Desktop Protocol', 'File Deletion', 'Modify Registry', 'Rundll32', 'Regsvr32', 'Spearphishing Attachment', 'Video Capture', 'Software Packing', 
      'System Network Configuration Discovery', 'Account Discovery', 'Connection Proxy', 'Command-Line Interface', 'Indicator Removal on Host', 'File and Directory Discovery', 'Data Staged', 'System Network Connections Discovery', 
      'Scripting', 'Web Service', 'User Execution', 'Process Discovery', 'Exfiltration Over Command and Control Channel', 'Registry Run Keys / Startup Folder', 'Shortcut Modification', 'Exfiltration Over Alternative Protocol', 
      'Data Obfuscation', 'Valid Accounts', 'DLL Side-Loading', 'Exploitation for Privilege Escalation', 'Obfuscated Files or Information', 'Data Compressed', 'Credentials in Files', 'Input Capture', 'Exploitation for Client Execution', 
      'Standard Non-Application Layer Protocol', 'Query Registry', 'Uncommonly Used Port', 'Bypass User Account Control', 'Data Encoding', 'Data Encrypted', 'Drive-by Compromise', 'Access Token Manipulation', 'Create Account', 
      'Remote System Discovery', 'Network Service Scanning', 'Remote File Copy', 'Fallback Channels', 'System Time Discovery', 'Service Execution', 'PowerShell', 'Custom Command and Control Protocol', 'Commonly Used Port', 'Windows Admin Shares']
    true_negs = ["This is a generic sentance","There aren't any relations to techniques in this senatnce","Random gibberish that blah blah blah!","Four score and seven years ago..."]
    #for tech in list_of_techs:
    i = random.randint(0,len(list_of_techs)-1) # randomize the selection for building
    cv,logreg = await ml_svc.build_models(list_of_techs[i],json_tech,true_negs)
    assert type(cv) is CountVectorizer
    assert type(logreg) is LogisticRegression
        #pass # test building model and saving it

async def prep_test_data(tech_name, techniques, true_negatives,cv):
    lst1, lst2, false_list, sampling = [], [], [], []
    getuid = ""
    len_truelabels = 0

    for k, v in techniques.items():
        if v['name'] == tech_name:
            for i in v['example_uses']:
                lst1.append(await web_svc.tokenize(i))
                lst2.append(True)
                len_truelabels += 1
                getuid = k
            # collect the false_positive samples here too, which are the incorrectly labeled texts from reviewed reports, we will include these in the Negative Class.
            #for fp in v['false_positives']:
            #    sampling.append(fp)
        else:
            for i in v['example_uses']:
                false_list.append(await web_svc.tokenize(i))

    # at least 90% of total labels for both classes, use this for determining how many labels to use for classifier's negative class
    kval = int((len_truelabels * 10))
    #true_negatives.extend("this is a sentance that has no techniques in it.")
    #for i in true_negatives:
    #    sampling.append(i)
    # make first half random set of true negatives that have no relation/label to ANY technique
    sampling.extend(random.choices(true_negatives)) # , k=kval))

    # do second random half set, these are true/positive labels for OTHER techniques, use list obtained from above
    sampling.extend(random.choices(false_list, k=kval))

    # Finally, create the Negative Class for this technique's classification model, include False as the labels for this training data
    for false_label in sampling:
        lst1.append(await web_svc.tokenize(false_label))
        lst2.append(False)

    # convert into a dataframe
    df = pd.DataFrame({'text': lst1, 'category': lst2})

    # build model based on that technique
    #cv = CountVectorizer(max_features=2000)
    X = cv.transform(df['text']).toarray()
    y = df['category']
    _, X_test, _, y_test = train_test_split(X, y, test_size=0.1)
    return X_test,y_test

@pytest.mark.asyncio
async def test_ml_performance():
    if os.path.isfile('models/model_dict.p'):
        json_tech = json.load(open("models/attack_dict.json", "r", encoding="utf_8"))
        model_dict = pickle.load(open('models/model_dict.p', 'rb'))
        list_of_techs = ['Indicator Removal from Tools', 'Windows Management Instrumentation', 'Screen Capture', 'System Owner/User Discovery', 'Credential Dumping', 'Audio Capture', 'Timestomp', 'Permission Groups Discovery',
        'Email Collection', 'Data from Removable Media', 'Code Signing', 'Process Hollowing', 'Spearphishing Link', 'Security Software Discovery', 'Disabling Security Tools', 'Automated Collection', 'Clipboard Data', 'System Service Discovery',
        'Network Share Discovery', 'Peripheral Device Discovery', 'System Information Discovery', 'Standard Application Layer Protocol', 'Scheduled Task', 'Execution through API', 'Custom Cryptographic Protocol', 
        'Replication Through Removable Media', 'Data from Local System', 'Deobfuscate/Decode Files or Information', 'Masquerading', 'Process Injection', 'DLL Search Order Hijacking', 'New Service', 'Application Window Discovery', 
        'Standard Cryptographic Protocol', 'Binary Padding', 'Remote Desktop Protocol', 'File Deletion', 'Modify Registry', 'Rundll32', 'Regsvr32', 'Spearphishing Attachment', 'Video Capture', 'Software Packing', 
        'System Network Configuration Discovery', 'Account Discovery', 'Connection Proxy', 'Command-Line Interface', 'Indicator Removal on Host', 'File and Directory Discovery', 'Data Staged', 'System Network Connections Discovery', 
        'Scripting', 'Web Service', 'User Execution', 'Process Discovery', 'Exfiltration Over Command and Control Channel', 'Registry Run Keys / Startup Folder', 'Shortcut Modification', 'Exfiltration Over Alternative Protocol', 
        'Data Obfuscation', 'Valid Accounts', 'DLL Side-Loading', 'Exploitation for Privilege Escalation', 'Obfuscated Files or Information', 'Data Compressed', 'Credentials in Files', 'Input Capture', 'Exploitation for Client Execution', 
        'Standard Non-Application Layer Protocol', 'Query Registry', 'Uncommonly Used Port', 'Bypass User Account Control', 'Data Encoding', 'Data Encrypted', 'Drive-by Compromise', 'Access Token Manipulation', 'Create Account', 
        'Remote System Discovery', 'Network Service Scanning', 'Remote File Copy', 'Fallback Channels', 'System Time Discovery', 'Service Execution', 'PowerShell', 'Custom Command and Control Protocol', 'Commonly Used Port', 'Windows Admin Shares']        
        
        true_negs = ["This is a generic sentance","There aren't any relations to techniques in this senatnce","Random gibberish that blah blah blah!","Four score and seven years ago..."]
        orig_score = {'Screen Capture':0.85,'Indicator Removal from Tools':0.90,'Windows Management Instrumentation':0.90,'System Owner/User Discovery':0.90,'Credential Dumping':0.90,'Audio Capture':0.90,'Timestomp':0.90,'Permission Groups Discovery':0.90,
        'Email Collection':0.90,'Data from Removable Media':0.90,'Code Signing':0.90,'Process Hollowing':0.90,'Spearphishing Link':0.90,'Security Software Discovery':0.90,'Disabling Security Tools':0.90,'Automated Collection':0.90,'Clipboard Data':0.90,
        'System Service Discovery':0.90,'Network Share Discovery':0.90,'Peripheral Device Discovery':0.90,'System Information Discovery':0.90,'Standard Application Layer Protocol':0.90,'Scheduled Task':0.90,'Execution through API':0.90,
        'Custom Cryptographic Protocol':0.90,'Replication Through Removable Media':0.90,'Data from Local System':0.90,'Deobfuscate/Decode Files or Information':0.90,'Masquerading':0.90,'Process Injection':0.90,'DLL Search Order Hijacking':0.90,
        'New Service':0.90,'Application Window Discovery':0.90,'Standard Cryptographic Protocol':0.90,'Binary Padding':0.90,'Remote Desktop Protocol':0.90,'File Deletion':0.90,
        'Modify Registry':0.90,'Rundll32':0.90,'Regsvr32':0.90,'Spearphishing Attachment':0.90,'Video Capture':0.90,'Software Packing':0.90,'System Network Configuration Discovery':0.90,
        'Account Discovery':0.90,'Connection Proxy':0.90,'Command-Line Interface':0.90,'Indicator Removal on Host':0.90,'File and Directory Discovery':0.90,
        'Data Staged':0.90,'System Network Connections Discovery':0.90,'Scripting':0.90,'Web Service':0.90,'User Execution':0.90,'Process Discovery':0.90,'Exfiltration Over Command and Control Channel':0.90,
        'Registry Run Keys / Startup Folder':0.90,'Shortcut Modification':0.90,'Exfiltration Over Alternative Protocol':0.90,'Data Obfuscation':0.90,'Valid Accounts':0.90,
        'DLL Side-Loading':0.90,'Exploitation for Privilege Escalation':0.87,'Obfuscated Files or Information':0.90,'Data Compressed':0.90,'Credentials in Files':0.90,
        'Input Capture':0.90,'Exploitation for Client Execution':0.90,'Standard Non-Application Layer Protocol':0.90,'Query Registry':0.90,'Uncommonly Used Port':0.90,
        'Bypass User Account Control':0.90,'Data Encoding':0.90,'Data Encrypted':0.90,'Drive-by Compromise':0.90,'Access Token Manipulation':0.77,'Create Account':0.90,
        'Remote System Discovery':0.90,'File and Directory DiscoveryNetwork Service Scanning':0.90,'Remote File Copy':0.90,'Fallback Channels':0.90,'System Time Discovery':0.90,
        'Service Execution':0.90,'PowerShell':0.90,'Custom Command and Control Protocol':0.90,'Commonly User Port':0.90,'Windows Admin Shares':0.90}
        count = 0
        for i in list_of_techs:
            cv,logreg = model_dict[i]
            X_test,y_test = await prep_test_data(i,json_tech,true_negs,cv)
            
            score_check = orig_score[i]
            score = logreg.score(X_test,y_test)
            print("Testing {} score: {} target score: {}".format(i,score,score_check))
            if score >= score_check:
                count += 1
        logging.critical("Total scores met: {} target: {}".format(count,len(orig_score)))
        assert count >= len(orig_score)-3
            # result_score = original_score_value_from_file
            # assert score >= result_score
    pass # load model from store, test models performance
    # assert score 

@pytest.mark.asyncio
async def test_delete_db(): # cleanup tests
    os.remove('database/tram.db')
    assert os.path.isfile("database/tram.db") == False
