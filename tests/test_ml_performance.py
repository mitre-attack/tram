import pytest
import os

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

def test_performance():
    pass # create method to evaluate the performance of the classifier