from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.model_selection import train_test_split
#from sklearn.linear_model import LogisticRegression
from skmultilearn.problem_transform import ClassifierChain
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import MultiLabelBinarizer

from urllib.request import pathname2url
import os
from time import sleep

import spacy
import pandas as pd
import numpy as np
import redis
import pickle
import hashlib
import logging
import asyncio

import sqlite3

import time

from models.base_model import BaseModel

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

    def save_current_model(self,model):
        '''
        description: loads models dictionary into redis
        input: dictionary of scikit-learn LogisticRegression models with attack_uid as keys
        output: nil
        '''
        print("retrain_svc: Saving model to redis")
        r = redis.Redis(host=self.redis_ip, port=self.redis_port, db=0)
        model_dump = pickle.dumps(model)
        model_hash = hashlib.md5(model_dump).hexdigest()
        r.set("model",model_dump)
        r.set("model_hash",model_hash)

    def check_redis(self):
        '''
        description: checks redis to see if a model exists
        input: nil
        output: model if it does exist, and None if it doesn't
        '''
        r = redis.Redis(host=self.redis_ip,port=self.redis_port,db=0)
        try:
            _ = r.get("model_hash")
            model = r.get("model")
            return model
        except Exception:
            print("retrain_svc: No model in the redis store")
            return None

    def extract_data(self,in_data,sentances,labels,key):
        '''
        description: Creates the training data dictionary
        input: input data, output sentances, output labels, key for input data
        output: X sentances, y labels
        '''
        if(key != 'sentence'):
            for t in in_data:
                labels.append(t['labels'])
                sentances.append(t[key])
        else:
            for t in in_data:
                labels.append(t['uid'])
                sentances.append(t[key])
            
        return sentances,labels

    def get_training_data(self): # gets and assembles a dictionary of training data from the database
        '''
        description: Gets training data from database, and outputs two arrays, an array of sentances, and an array of corresponding labels
        input: nil
        output: X sentences, y labels
        '''
        print("retrain_svc: Getting data from sql")
        loop = asyncio.get_event_loop()
        while(True):
            try:
                true_positives = loop.run_until_complete(self.dao.get('true_positives')) # Grab all training data from database
                false_positives = loop.run_until_complete(self.dao.get('false_positives'))
                false_negatives = loop.run_until_complete(self.dao.get('false_negatives'))
                true_negatives = loop.run_until_complete(self.dao.get('true_negatives'))
                if(len(true_positives) <= 100 or len(true_negatives) <= 1000): # wait until database is fully populated
                    sleep(60)
                    continue
                else:
                    break
            except Exception as e:
                continue

        training_sents = []
        training_labels = []

        print("retrain_svc: Formatting Sentances")

        training_sents,training_labels = self.extract_data(true_positives,training_sents,training_labels,'true_positive') # Assemble dictionary for training data
        training_sents,training_labels = self.extract_data(false_positives,training_sents,training_labels,'false_positive')
        training_sents,training_labels = self.extract_data(false_negatives,training_sents,training_labels,'false_negative')
        training_sents,training_labels = self.extract_data(true_negatives,training_sents,training_labels,'sentence')
        #training_data = self.modify_training_dict(training_data,true_negatives,'tn','sentence')

        return training_sents,training_labels

    def train_model(self,training_data):
        '''
        description: method to handle training models loaded from the models directory
        input: tuple of training data in form (X,y)
        output: model object
        '''
        X,y = training_data
        model = BaseModel()
        model.train(X,y)
        return model


    def train(self): 
        '''
        description: "main" function, all other functions are initiated and run out of here
        input: nil
        output: nil
        '''
        # on startup, check redis for model, if no model exists, train the model immediatly
        redis_out = self.check_redis()
        if(redis_out == None):
            raw_data = self.get_training_data()
            model = self.train_model(raw_data)
            self.save_current_model(model)
        while(True):
            time_check = time.localtime(time.time())
            if(time_check[3] == 12 and time_check[4] == 0): # kick off training at noon and midnight
                raw_data = self.get_training_data()
                #print(raw_data)
                model = self.train_model(raw_data) #self.train_on_data(raw_data)
                self.save_current_model(model)
                print("retrain_svc: Retraining task finished")
            else:
                time.sleep(10)

    def handler(self):
        self.train()