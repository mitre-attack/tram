from node2vec import Node2Vec
import networkx as nx

from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.neighbors import KNeighborsClassifier
import sklearn.linear_model as lm
from sklearn.metrics import f1_score

import spacy

import numpy as np

from tqdm import tqdm
import logging

class BaseModel:
    def __init__(self):
        self.model = None# lm.LinearRegression(n_jobs=-1)
        self.rnc = None
        self.classes = None
        self.tfid = None
        self.count_vec = None

    def create_graph_matricies(self,y,classes):
        nodes = []
        for node in range(len(classes)):
            nodes.append(node)
        matrix = np.zeros((len(classes),len(classes)))
        edges = []
        print('Getting edges...')
        weights = {}
        for row in tqdm(y):
            for i in range(len(row)):
                for j in range(len(row)):
                    if row[i]*row[j] == 1: # both labels are activated 
                        matrix[i,j] += 1
                        if ([i,j] not in edges) and ([j,i] not in edges): # make self loops for single nodes
                            edges.append([i,j])
                        elif(([i,j] in edges) or ([j,i] in edges)):
                            if((i,j) in weights.keys()):
                                weights[(i,j)] += 1
                            else:
                                weights[(i,j)] = 1
        print('Edges complete')
        #to get frequency we'll divide by number of appearances
        return nodes,edges,weights

    def embedding_encode(self,y, model):
        # for each hot vector in y, dot product with corresponding word embedding
        # try averaging word2vecs
        out_y = []
        for i in y:
            vecs = []
            count = 0
            for j in range(len(i)):
                if(i[j]):
                    if(len(vecs) == 0):
                        try:
                            vecs = np.array(model.wv.get_vector(str(j)))
                            count = 1
                        except:
                            print("Vocab not found error")
                            print(j)
                            try:
                                print(self.classes[j])
                            except:
                                print("Index out of range error")
                    else:
                        try:
                            vecs += model.wv.get_vector(str(j))
                            count += 1
                        except:
                            print("Vocab not found error")
                            print(j)
                            try:
                                print(self.classes[j])
                            except:
                                print("Index error")
            if(len(vecs) != 0):
                out_y.append(vecs/count)
            else:
                out_y.append(np.zeros(32))
        return np.array(out_y)

    def train_embedder(self,y_embed,y,k=5):
        rnc = KNeighborsClassifier(n_neighbors=k,n_jobs=-1)
        print('Fitting...')
        rnc.fit(y_embed,y)
        return rnc

    def embedding_decode(self,y_embed,rnc):
        print('Decoding embedding')
        predicted_labels = rnc.predict(y_embed)
        print('Finished')
        return predicted_labels

    def extract_X(self,X):
        nlp = spacy.load('en_core_web_md')
        new_X = []
        for i in tqdm(X):
            temp = []
            for sent in nlp(i).sents:
                for tok in sent:
                    if(not tok.is_stop):
                        temp.append(tok.text)
            new_X.append(' '.join(temp))
        count_vec = CountVectorizer(max_features=2500)
        tfid = TfidfTransformer()
        all_counts = count_vec.fit_transform(new_X)
        data = tfid.fit_transform(all_counts)
        self.count_vec = count_vec
        self.tfid = tfid
        return data

    def extract_X_for_prediction(self,X):
        nlp = spacy.load('en_core_web_md')
        new_X = []
        for i in tqdm(X):
            temp = []
            for sent in nlp(i).sents:
                for tok in sent:
                    if(not tok.is_stop):
                        temp.append(tok.text)
            new_X.append(' '.join(temp))
        all_counts = self.count_vec.transform(new_X)
        return self.tfid.transform(all_counts)

    def extract_y(self,y):
        binarizer = MultiLabelBinarizer()
        new_y = []
        for i in y:
            if(i == "NO_TECHNIQUE"):
                new_y.append([i])
            else:
                new_y.append(i.split("_"))
        Y = binarizer.fit_transform(new_y) # split y by each technique as it was inserted into the database
        self.classes = binarizer.classes_ # get fitted classes
        # construct the output graph to identify relationships between classes
        nodes,edges,weights = self.create_graph_matricies(Y,self.classes)
        nx_graph = nx.Graph()
        nx_graph.add_nodes_from(nodes)
        nx_graph.add_edges_from(edges)

        # fit node2vec, get dimension reduced embeddings
        N2V = Node2Vec(nx_graph,dimensions=32,walk_length=30,num_walks=300,workers=1)
        n2v = N2V.fit(window=10, min_count=1, batch_words=8)
        return Y,n2v

    def train(self,X,y):
        ext_X = self.extract_X(X)
        ext_y,n2v = self.extract_y(y)
        # encode y to embeddings then train
        new_y = self.embedding_encode(ext_y,n2v)
        self.rnc = self.train_embedder(new_y,ext_y)
        X_train = ext_X.toarray()
        self.model = lm.LinearRegression()
        print("base_model: fitting regression model")
        self.model.fit(X_train,new_y)
        print("base_model: regression model fit")
        print("base_model: testing model...")

        # test data using f1 score to give users some verbosity on how well the model performed
        test = self.model.predict(X_train)
        lab = self.embedding_decode(test,self.rnc)
        score = f1_score(ext_y,lab,average='weighted')
        print("f1 score on training data: {}".format(score))

    def predict(self,X):
        if(self.model == None):
            print("ERROR: Model needs to be trained first")
            return None
        ext_X = self.extract_X_for_prediction(X)
        output = self.model.predict(ext_X)
        decoded_output = self.embedding_decode(output,self.rnc)
        full_out = []
        for i in decoded_output:
            temp = []
            for j in range(len(i)):
                if(i[j]):
                    temp.append(self.classes[j])
            full_out.append(temp)
        return full_out