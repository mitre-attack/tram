import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
import os, pickle, random
import nltk
import logging
import asyncio
import redis
from tqdm import tqdm


class MLService:

    # Service to perform the machine learning against the pickle file
    def __init__(self, web_svc, dao):
        self.web_svc = web_svc
        self.dao = dao
        self.redis_ip = 'localhost'
        self.redis_port = 6379

    async def load_model(self):
        r = redis.Redis(host=self.redis_ip,port=self.redis_port,db=0)
        try:
            model_dump = r.get("model")
            model = pickle.loads(model_dump)
        except Exception:
            print("Error loading model, either redis is down, or the model has not been trained yet")
        return model

    async def analyze_html(self, model, list_of_sentences):
        logging.info("analyzing sentances with model...")
        for i in tqdm(list_of_sentences):
            #print(i['text'])
            await asyncio.sleep(0.01)
            labels = model.predict([i['text']])
            #print(labels)
            if("NO_TECHNIQUE" in labels[0]):
                i['ml_techniques_found'] = []
            else:
                i['ml_techniques_found'] = labels[0]
        return list_of_sentences
        '''
        for i in list_of_techs:
            cv, logreg = model_dict[i]
            final_df = await self.analyze_document(cv, logreg, list_of_sentences)
            count = 0
            for vals in final_df['category']:
                await asyncio.sleep(0.001)
                if vals == True:
                    list_of_sentences[count]['ml_techniques_found'].append(i)
                count += 1
        return list_of_sentences
        '''



    async def analyze_document(self, cv, model, sentences):
        cleaned_sentences = [await self.web_svc.tokenize(i['text']) for i in sentences]

        df2 = pd.DataFrame({'text': cleaned_sentences})
        Xnew = cv.transform(df2['text']).toarray()
        await asyncio.sleep(0.01)
        y_pred = model.predict(Xnew)
        df2['category'] = y_pred.tolist()
        return df2


    async def ml_techniques_found(self, report_id, sentence):
        sentence_id = await self.dao.insert('report_sentences',
                                            dict(report_uid=report_id, text=sentence['text'], html=sentence['html'],
                                                 found_status="true"))
        for technique in sentence['ml_techniques_found']:
            attack_uid = await self.dao.get('attack_uids', dict(name=technique))
            if not attack_uid:
                attack_uid = await self.dao.get('attack_uids', dict(tid=technique))
            attack_technique = attack_uid[0]['uid']
            attack_technique_name = '{} (m)'.format(attack_uid[0]['name'])
            attack_tid = attack_uid[0]['tid']
            await self.dao.insert('report_sentence_hits',
                                  dict(uid=sentence_id, attack_uid=attack_technique,
                                       attack_technique_name=attack_technique_name, report_uid=report_id, attack_tid = attack_tid))

    async def get_true_negs(self):
        true_negs = await self.dao.get('true_negatives')
        true_negatives = []
        for i in true_negs:
            true_negatives.append(i['sentence'])
        return true_negatives

    async def combine_ml_reg(self, ml_analyzed_html, reg_analyzed_html):
        analyzed_html = []
        index = 0
        for sentence in ml_analyzed_html:
            sentence['reg_techniques_found'] = reg_analyzed_html[index]['reg_techniques_found']
            analyzed_html.append(sentence)
            index += 1
        return analyzed_html

    async def check_nltk_packs(self):
        try:
            nltk.data.find('tokenizers/punkt')
            logging.info('[*] Found punkt')
        except LookupError:
            logging.warning('Could not find the punkt pack, downloading now')
            nltk.download('punkt')
        try:
            nltk.data.find('corpora/stopwords')
            logging.info('[*] Found stopwords')
        except LookupError:
            logging.warning('Could not find the stopwords pack, downloading now')
            nltk.download('stopwords')

