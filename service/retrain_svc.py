import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
import spacy as sp
import redis


class RetrainingService:
    def __init__(self):
        self.redis_ip = 'localhost'
        self.redis_port = 6379

    def save_current_model(self):
        r = redis.Redis(host=self.redis_ip, port=self.redis_port, db=0)
        
    

    def bucket_words(self):
        pass
    
    def feature_extraction(self):
        pass

    def train(self):
        pass