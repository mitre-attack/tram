import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
import spacy as sp
import redis
import pickle
import logging


'''
Retraining service:
retrains the model off of current data, then saves model to redis store
functionality: Loads training data from sql store, filters X and y data into "buckets" for each
boosted classifier, extracts features on X data (CountVectorizor currently), trains boosted classifiers
on each respective bucket of data, saves data to redis store
'''

class RetrainingService:
    def __init__(self,dao):
        self.redis_ip = 'localhost'
        self.redis_port = 6379
        self.dao = dao

    async def save_current_model(self,models):
        logging.info("retrain_svc: Saving model to redis")
        r = redis.Redis(host=self.redis_ip, port=self.redis_port, db=0)
        model_dump = pickle.dumps(models)
        r.set("model",model_dump)

    async def modify_training_dict(self,training_dict,in_data,dict_key,in_key):
        for t in in_data:
            t_uid = t['uid']
            if(t_uid not in training_dict.keys()):
                training_dict[t_uid] = {dict_key:[]}
            elif(dict_key not in training_dict[t_uid].keys()):
                training_dict[t_uid][dict_key] = []
            else:
                training_dict[t_uid][dict_key].append(t[in_key])
        return training_dict

    async def get_training_data(self):
        logging.info("retrain_svc: Getting data from sql")
        true_positives = await self.dao.get('true_positives')
        false_positives = await self.dao.get('false_positives')
        false_negatives = await self.dao.get('false_negatives')
        true_negatives = await self.dao.get('true_negatives')
        training_data = {}

        logging.info("retrain_svc: Creating training dict")
        training_data = await self.modify_training_dict(training_data,true_positives,'tp','true_positive')
        training_data = await self.modify_training_dict(training_data,false_positives,'fp','false_positive')
        training_data = await self.modify_training_dict(training_data,false_negatives,'fn','false_negative')
        training_data = await self.modify_training_dict(training_data,true_negatives,'tn','sentence')


        '''
        for t in true_positives:
            t_uid = t['uid']
            if(t_uid not in training_data.keys()):
                training_data[t_uid] = {'tp':[]}
            elif('tp' not in training_data[t_uid].keys()):
                training_data[t_uid]['tp'] = []
            else:
                training_data[t_uid]['tp'].append(t['true_positive'])
        for p in false_positives:
            p_uid = p['uid']
            if(p_uid not in training_data.keys()):
                training_data[p_uid] = {'fp':[]}
            elif('fp' not in training_data[p_uid].keys()):
                training_data[p_uid]['fp'] = []
            else:
                training_data[p_uid]['fp'].append(p['false_positive'])
        for n in false_negatives:
            n_uid = n['uid']
            if(n_uid not in training_data.keys()):
                training_data[n_uid] = {'fn':[]}
            elif('fn' not in training_data[n_uid].keys()):
                training_data[n_uid]['fn'] = []
            else:
                training_data[n_uid]['fn'].append(n['false_negative'])
        for n in true_negatives:
            n_uid = n['uid']
            if(n_uid not in training_data.keys()):
                training_data[n_uid] = {'tn':[]}
            elif('tn' not in training_data[n_uid].keys()):
                training_data[n_uid]['tn'] = []
            else:
                training_data[n_uid]['tn'].append(n['true_negative'])
        '''
        return training_data

    async def train_on_data(self,training_dict):
        cv = CountVectorizer()
        models = {}
        logging.info("retrain_svc: initiate training")
        for i in training_dict:
            clf = LogisticRegression(max_iter=2500, solver='lbfgs')
            X_data = []
            y_data = []
            for t in i['tp']:
                y_data.append(True)
                X_data.append(t)
            for t in i['fn']:
                y_data.append(True)
                X_data.append(t)
            for f in i['fp']:
                y_data.append(False)
                X_data.append(f)
            for f in i['tn']:
                y_data.append(False)
                X_data.append(f)
            word_counts = cv.fit_transform(X_data)
            logging.info("retrain_svc: Fitting uid [{}] to model".format(i))
            clf.fit(word_counts,y_data)
            models[i] = clf
        return models

    async def train(self): 
        raw_data = await self.get_training_data()
        models = await self.train_on_data(raw_data)
        await self.save_current_model(models)
        logging.info("retrain_svc: Retraining task finished")