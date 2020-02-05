import pytest
import os
from sklearn.model_selection import train_test_split
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


@pytest.mark.asyncio
async def test_performance():
    # take from true positives table
    # split data in to train test
    # train data on model
    # test data compare
    training_data = await dao.get('true_positives')
    for i in training_data:
        print(i)
    #X_train,X_test,y_train,y_test = train_test_split(training_data)
    pass # create method to evaluate the performance of the classifier