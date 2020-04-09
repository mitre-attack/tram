import pytest
import asyncio

import sys, os
sys.path.append(os.path.realpath(os.path.dirname(__file__)+"/.."))

from handlers.web_api import WebAPI
from service.data_svc import DataService
from service.web_svc import WebService
from service.reg_svc import RegService
from service.ml_svc import MLService
from service.rest_svc import RestService

from database.dao import Dao

import base64

dao = Dao(os.path.join('database', 'tram.db'))
web_svc = WebService()
reg_svc = RegService(dao=dao)
data_svc = DataService(dao=dao, web_svc=web_svc)
ml_svc = MLService(web_svc=web_svc, dao=dao)
rest_svc = RestService(web_svc, reg_svc, data_svc, ml_svc, dao)


@pytest.mark.asyncio
async def test_word_ingest():
    in_data = 'blahblahblahbase64'
    with open("tests/test_report.docx",'rb') as f:
        base = base64.b64encode(f.read())
    in_data += str(base)
    criteria = {'file':in_data}
    await rest_svc.insert_word(criteria=criteria)
    output = await dao.get('reports',dict(title="Test Report"))
    assert output[0]['content'] == "This report is a test. No need to use it for anything else. Bye."
    assert output[0]['title'] == "Test Report"
    new_crit = {'file':base}
    await rest_svc.insert_word(criteria=new_crit)
    output = await dao.get('reports',dict(title="Test Report"))
    assert output[0]['content'] == "This report is a test. No need to use it for anything else. Bye."
    assert output[0]['title'] == "Test Report"