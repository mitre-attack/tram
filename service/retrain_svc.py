from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.model_selection import train_test_split
#from sklearn.linear_model import LogisticRegression
from skmultilearn.problem_transform import ClassifierChain
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import MultiLabelBinarizer

import spacy
import pandas as pd
import numpy as np
import redis
import pickle
import hashlib
import logging
import asyncio

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

    def save_current_model(self,models):
        '''
        description: loads models dictionary into redis
        input: dictionary of scikit-learn LogisticRegression models with attack_uid as keys
        output: nil
        '''
        logging.info("retrain_svc: Saving model to redis")
        r = redis.Redis(host=self.redis_ip, port=self.redis_port, db=0)
        model_dump = pickle.dumps(models)
        model_hash = hashlib.md5(model_dump).hexdigest()
        r.set("model",model_dump)
        r.set("model_hash",model_hash)

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
        logging.info("retrain_svc: Getting data from sql")
        loop = asyncio.get_event_loop()
        true_positives = loop.run_until_complete(self.dao.get('true_positives')) # Grab all training data from database
        false_positives = loop.run_until_complete(self.dao.get('false_positives'))
        false_negatives = loop.run_until_complete(self.dao.get('false_negatives'))
        true_negatives = loop.run_until_complete(self.dao.get('true_negatives'))
        training_sents = []
        training_labels = []

        logging.info("retrain_svc: Formatting Sentances")

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

    '''
    def train_on_data(self,training_dict): # new training on data involves technique specific
        
        #description: method to train the boosted logistic regression models
        #input: training data
        #output: dictionary of models (boosted classifier)
        
        cv = CountVectorizer(max_features=2500)
        tft = TfidfTransformer()

        logging.info("retrain_svc: initiate training")
        # build graph for y labels


        for j in training_dict:
            X_data = []
            y_data = []
            i = training_dict[j]

            len_pos = len([i for i in y_data if i == True])
            len_neg = len(y_data) - len_pos
            
            if(True in y_data and False in y_data):
                X_train,X_test,y_train,y_test = train_test_split(np.array(X_data),np.array(y_data),test_size=0.1)
                if(True in y_train and False in y_train):
                    clf = ClassifierChain(GaussianNB()) #LogisticRegression(max_iter=2500, solver='lbfgs')
                    word_counts = cv.fit_transform(X_train)
                    tfidf = tft.fit_transform(word_counts)
                    logging.info("retrain_svc: Fitting uid [{}] to model".format(j))
                    clf.fit(tfidf,y_train)
                    test_counts = cv.transform(X_test)
                    test_tfidf = tft.transform(test_counts)
                    #clf.score(test_counts,y_test)
                    print("retrain_svc: Accuracy on test set = {}".format(clf.score(test_tfidf,y_test)))
                    models[j] = (word_counts,clf)
        return models
        '''

    def train(self): 
        '''
        description: "main" function, all other functions are initiated and run out of here
        input: nil
        output: nil
        '''
        while(True):
            time_check = time.localtime(time.time())
            #if(time_check[3] == 12 and time_check[4] == 0): # kick off training at noon and midnight
            raw_data = self.get_training_data()
            #print(raw_data)
            models = self.train_model(raw_data) #self.train_on_data(raw_data)
            self.save_current_model(models)
            logging.info("retrain_svc: Retraining task finished")
            #else:
            #    time.sleep(10)

    def handler(self):
        self.train()