from service.data_svc import DataService
from service.web_svc import WebService
from service.reg_svc import RegService
from service.ml_svc import MLService
from service.rest_svc import RestService
from service.retrain_svc import RetrainingService
from database.dao import Dao
import os

class ServiceHandler:

    def __init__(self):
        self.dao = Dao(os.path.join('database', 'tram.db'))

        self.web_svc = WebService()
        self.reg_svc = RegService(dao=self.dao)
        self.retrain_svc = RetrainingService(dao=self.dao)
        self.data_svc = DataService(dao=self.dao, web_svc=self.web_svc)
        self.ml_svc = MLService(web_svc=self.web_svc, dao=self.dao)
        self.rest_svc = RestService(self.web_svc, self.reg_svc, self.data_svc, self.ml_svc, self.dao)
