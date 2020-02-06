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

async def prep_test_data(tech_name, techniques, true_negatives):
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
    cv = CountVectorizer(max_features=2000)
    X = cv.fit_transform(df['text']).toarray()
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
        orig_score = {'Screen Capture':0.85,'Indicator Removal from Tools':1.0,'Windows Management Instrumentation':1.0,'System Owner/User Discovery':1.0,'Credential Dumping':1.0,'Audio Capture':1.0,'Timestomp':1.0,'Permission Groups Discovery':1.0,
        'Email Collection':1.0,'Data from Removable Media':1.0,'Code Signing':1.0,'Process Hollowing':1.0,'Spearphishing Link':1.0,'Security Software Discovery':1.0,'Disabling Security Tools':1.0,'Automated Collection':1.0,'Clipboard Data':1.0,
        'System Service Discovery':1.0,'Network Share Discovery':1.0,'Peripheral Device Discovery':1.0,'System Information Discovery':1.0,'Standard Application Layer Protocol':1.0,'Scheduled Task':1.0,'Execution through API':1.0,
        'Custom Cryptographic Protocol':1.0,'Replication Through Removable Media':1.0,'Data from Local System':1.0,'Deobfuscate/Decode Files or Information':1.0,'Masquerading':1.0,'Process Injection':1.0,'DLL Search Order Hijacking':1.0,
        'New Service':1.0,'Application Window Discovery':1.0,'Standard Cryptographic Protocol':1.0,'Binary Padding':1.0,'Remote Desktop Protocol':1.0,'File Deletion':1.0,
        'Modify Registry':1.0,'Rundll32':1.0,'Regsvr32':1.0,'Spearphishing Attachment':1.0,'Video Capture':1.0,'Software Packing':1.0,'System Network Configuration Discovery':1.0,
        'Account Discovery':1.0,'Connection Proxy':1.0,'Command-Line Interface':1.0,'Indicator Removal on Host':1.0,'File and Directory Discovery':1.0,
        'Data Staged':1.0,'System Network Connections Discovery':1.0,'Scripting':1.0,'Web Service':1.0,'User Execution':1.0,'Process Discovery':1.0,'Exfiltration Over Command and Control Channel':1.0,
        'Registry Run Keys / Startup Folder':1.0,'Shortcut Modification':1.0,'Exfiltration Over Alternative Protocol':1.0,'Data Obfuscation':1.0,'Valid Accounts':1.0,
        'DLL Side-Loading':1.0,'Exploitation for Privilege Escalation':0.87,'Obfuscated Files or Information':1.0,'Data Compressed':1.0,'Credentials in Files':1.0,
        'Input Capture':1.0,'Exploitation for Client Execution':1.0,'Standard Non-Application Layer Protocol':1.0,'Query Registry':1.0,'Uncommonly Used Port':1.0,
        'Bypass User Account Control':1.0,'Data Encoding':1.0,'Data Encrypted':1.0,'Drive-by Compromise':1.0,'Access Toekn Manipulation':0.77,'Create Account':1.0,
        'Remote System Discovery':1.0,'File and Directory DiscoveryNetwork Service Scanning':1.0,'Remote File Copy':1.0,'Fallback Channels':1.0,'System Time Discovery':1.0,
        'Service Execution':1.0,'PowerShell':1.0,'Custom Command and Control Protocol':1.0,'Commonly User Port':1.0,'Windows Admin Shares':1.0}
        for i in list_of_techs:
            X_test,y_test = await prep_test_data(i,json_tech,true_negs)
            cv,logreg = model_dict[i]
            score_check = orig_score[i]
            score = logreg.score(X_test,y_test)
            assert score >= score_check[i]
            # result_score = original_score_value_from_file
            # assert score >= result_score
    pass # load model from store, test models performance
    # assert score 

@pytest.mark.asyncio
async def test_delete_db(): # cleanup tests
    os.remove('database/tram.db')
    assert os.path.isfile("database/tram.db") == False
