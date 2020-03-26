from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.model_selection import train_test_split
#from sklearn.linear_model import LogisticRegression
from skmultlearn.problem_transform import ClassifierChain
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

    def modify_training_dict(self,training_dict,in_data,dict_key,in_key):
        '''
        description: Creates the training data dictionary
        input: training data dictionary, data to put in dictionary, training dictionary key, input data key
        output: training dictionary
        '''
        for t in in_data:
            t_uid = t['uid']
            if(t_uid not in training_dict.keys()):
                training_dict[t_uid] = {dict_key:[]}
            elif(dict_key not in training_dict[t_uid].keys()):
                training_dict[t_uid][dict_key] = []
            else:
                training_dict[t_uid][dict_key].append(t[in_key])
        return training_dict

    def get_training_data(self): # gets and assembles a dictionary of training data from the database
        '''
        description: Gets training data from database, and outputs a dictionary of scema {'attack_uid':{'accuracy_type' (fp, tp, ...)}}
        input: nil
        output: dictionary of dictionaries
        '''
        logging.info("retrain_svc: Getting data from sql")
        loop = asyncio.get_event_loop()
        true_positives = loop.run_until_complete(self.dao.get('true_positives')) # Grab all training data from database
        false_positives = loop.run_until_complete(self.dao.get('false_positives'))
        false_negatives = loop.run_until_complete(self.dao.get('false_negatives'))
        true_negatives = loop.run_until_complete(self.dao.get('true_negatives'))
        training_data = {}

        logging.info("retrain_svc: Creating training dict")
        training_data = self.modify_training_dict(training_data,true_positives,'tp','true_positive') # Assemble dictionary for training data
        training_data = self.modify_training_dict(training_data,false_positives,'fp','false_positive')
        training_data = self.modify_training_dict(training_data,false_negatives,'fn','false_negative')
        training_data = self.modify_training_dict(training_data,true_negatives,'tn','sentence')

        return training_data

    def fill_arrays(self,i,X,y,key):
        '''
        description: helper function to fill training data arrays
        input: inner training dictionary data, X_data, y_data, inner dictionary key
        output: X_data,y_data
        '''
        try:
            for t in i[key]:
                X.append(t)
                if(key == 'fp' or key == 'tn'):
                    y.append(False)
                else:
                    y.append(True)
        except Exception:
            _=0
        return X,y

    def create_negative_training_set(self,training_dict,num_pos_examples,current_num_neg,key):
        '''
        description: Creates a set of training data containing only negative training examples
        input: training data, number of positive examples in training data for key, current number of negative
        examples for key, key (attack_uid to train on)
        output: negative example training data 
        '''
        # make sure negative examples are the same length as positive examples
        # grab data from other positive examples but ensure that they aren't the same key
        # Get data from precreated training dict
        # Also get examples from sentances that aren't related to attack at all (maybe load into redis and pull from there)
        # split negative examples on 70-30 split, 30% are positive examples 70% are normal sentances

        unrelated_sentances = ["You're good at English when you know the difference between a man eating chicken and a man-eating chicken.",
        "Pair your designer cowboy hat with scuba gear for a memorable occasion.","When nobody is around, the trees gossip about the people who have walked under them.",
        "The three-year-old girl ran down the beach as the kite flew behind her.","Nothing seemed out of place except the washing machine in the bar.",
        "The pigs were insulted that they were named hamburgers.","Weather is not trivial - it's especially important when you're standing in it.",
        "Sometimes it is better to just walk away from things and go back to them later when you’re in a better frame of mind.",
        "The quick brown fox jumps over the lazy dog.","I think I will buy the red car, or I will lease the blue one.",
        "Don't step on the broken glass.","Would you rather be the best player on a horrible team or the worst player on a great team?",
        "The snow-covered path was no help in finding his way out of the backcountry.","What was your least favorite subject in school?",
        "Joe made the sugar cookies; Susan decorated them.","The opportunity of a lifetime passed before him as he tried to decide between a cone or a cup.",
        "He was disappointed when he found the beach to be so sandy and the sun so sunny."]

        to_get = num_pos_examples-current_num_neg

        neg_attack_num = round(to_get*0.333)
        attack_keys = list(training_dict.keys())
        #print(attack_keys)
        negative_examples = []

        for _ in range(neg_attack_num):
            neg_key = np.random.choice(attack_keys)
            while(neg_key == key or len(training_dict[neg_key]['tp']) == 0): # make sure key is not the positive example key
                neg_key = np.random.choice(attack_keys)
            negative_examples.append(np.random.choice(training_dict[neg_key]['tp']))
            
        for _ in range(to_get-neg_attack_num): # loop through the number of total wanted minu the number already retrieved
            negative_examples.append(np.random.choice(unrelated_sentances))
        #falses = [False*len(negative_examples)]
        return negative_examples

    def train_on_data(self,training_dict): # new training on data involves technique specific
        '''
        description: method to train the boosted logistic regression models
        input: training data
        output: dictionary of models (boosted classifier)
        '''
        cv = CountVectorizer(max_features=500)
        tft = TfidfTransformer()

        models = {}
        logging.info("retrain_svc: initiate training")
        for j in training_dict:
            X_data = []
            y_data = []
            i = training_dict[j]
            
            X_data,y_data = self.fill_arrays(i,X_data,y_data,'tp')
            X_data,y_data = self.fill_arrays(i,X_data,y_data,'fn')
            X_data,y_data = self.fill_arrays(i,X_data,y_data,'fp')
            X_data,y_data = self.fill_arrays(i,X_data,y_data,'tn')

            len_pos = len([i for i in y_data if i == True])
            len_neg = len(y_data) - len_pos

            negative_values = self.create_negative_training_set(training_dict,len_pos,len_neg,j)
            for i in negative_values:
                X_data.append(i)
                y_data.append(False)
            #X_data.extend(negative_values)
            #y_data.extend(falses)
            
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

    def train(self): 
        '''
        description: "main" function, all other functions are initiated and run out of here
        input: nil
        output: nil
        '''
        while(True):
            time_check = time.localtime(time.time())
            if(time_check[3] == 12 and time_check[4] == 0): # kick off training at noon and midnight
                raw_data = self.get_training_data()
                models = self.train_on_data(raw_data)
                self.save_current_model(models)
                logging.info("retrain_svc: Retraining task finished")
            else:
                time.sleep(10)

    def handler(self):
        self.train()