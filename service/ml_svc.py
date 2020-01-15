import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
import os, pickle, random
import nltk
import logging
import asyncio


class MLService:

    # Service to perform the machine learning against the pickle file
    def __init__(self, web_svc, dao):
        self.web_svc = web_svc
        self.dao = dao

    async def build_models(self, tech_name, techniques, true_negatives):
        """Function to build Logistic Regression Classification models based off of the examples provided"""
        lst1, lst2, false_list, sampling = [], [], [], []
        getuid = ""
        len_truelabels = 0

        for k, v in techniques.items():
            if v['name'] == tech_name:
                for i in v['example_uses']:
                    lst1.append(self.web_svc.tokenize(self, i))
                    lst2.append(True)
                    len_truelabels += 1
                    getuid = k
                # collect the false_positive samples here too, which are the incorrectly labeled texts from reviewed reports, we will include these in the Negative Class.
                for fp in v['false_positives']:
                    sampling.append(fp)
            else:
                for i in v['example_uses']:
                    false_list.append(self.web_svc.tokenize(self, i))

        # at least 90% of total labels for both classes, use this for determining how many labels to use for classifier's negative class
        kval = int((len_truelabels * 10))

        # make first half random set of true negatives that have no relation/label to ANY technique
        sampling.extend(random.choices(true_negatives, k=kval))

        # do second random half set, these are true/positive labels for OTHER techniques, use list obtained from above
        sampling.extend(random.choices(false_list, k=kval))

        # Finally, create the Negative Class for this technique's classification model, include False as the labels for this training data
        for false_label in sampling:
            lst1.append(self.web_svc.tokenize(self, false_label))
            lst2.append(False)

        # convert into a dataframe
        df = pd.DataFrame({'text': lst1, 'category': lst2})

        # build model based on that technique
        cv = CountVectorizer(max_features=2000)
        X = cv.fit_transform(df['text']).toarray()
        y = df['category']
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
        logreg = LogisticRegression(max_iter=2500, solver='lbfgs')
        logreg.fit(X_train, y_train)

        print("{} - {}".format(tech_name, logreg.score(X_test, y_test)))
        return (cv, logreg)

    async def analyze_document(self, cv, logreg, sentences):
        cleaned_sentences = [await self.web_svc.tokenize(i['text']) for i in sentences]

        df2 = pd.DataFrame({'text': cleaned_sentences})
        Xnew = cv.transform(df2['text']).toarray()
        await asyncio.sleep(0.01)
        y_pred = logreg.predict(Xnew)
        df2['category'] = y_pred.tolist()
        return df2

    async def build_pickle_file(self, list_of_techs, techniques, force=False):
        if not os.path.isfile('models/model_dict.p') or force:
            model_dict = {}
            total = len(list_of_techs)
            count = 1
            print(
                "Building Classification Models.. This could take anywhere from ~30-60+ minutes. Please do not close terminal.")
            for i in list_of_techs:
                print('[#] Building.... {}/{}'.format(count, total))
                count += 1
                model_dict[i] = self.build_models(self, i, techniques)
            print('[#] Saving models to pickled file: model_dict.p')
            pickle.dump(model_dict, open('models/model_dict.p', 'wb'))
        else:
            print('[#] Loading models from pickled file: model_dict.p')
            model_dict = pickle.load(open('models/model_dict.p', 'rb'))
        return model_dict

    async def analyze_html(self, list_of_techs, model_dict, list_of_sentences):
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


