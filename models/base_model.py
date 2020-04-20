from node2vec import Node2Vec
import networkx as nx

from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.neighbors import KNeighborsClassifier
import sklearn.linear_model as lm
from sklearn.metrics import f1_score

import numpy as np

from tqdm import tqdm
import logging

class BaseModel:
    def __init__(self,X,y):
        self.X = X
        self.y = y

    def create_graph_matricies(self,y,classes):
        nodes = []
        for node in range(len(classes)):
            nodes.append(node)
        edges = []
        print('Getting edges...')
        weights = {}
        for row in tqdm(y):
            for i in range(len(row)):
                for j in range(len(row)):
                    if row[i]*row[j] == 1: # both labels are activated
                        if ([i,j] not in edges) and ([j,i] not in edges): # make self loops for single nodes
                            edges.append([i,j])
                        elif(([i,j] in edges) or ([j,i] in edges)):
                            if((i,j) in weights.keys()):
                                weights[(i,j)] += 1
                            else:
                                weights[(i,j)] = 1
        print('Edges complete')
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
                        vecs = np.array(model.wv.get_vector(str(j)))
                        count = 1
                    else:
                        vecs += model.wv.get_vector(str(j))
                        count += 1
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

    def extract_X(self):
        count_vec = CountVectorizer(max_features=2500)
        tfid = TfidfTransformer()
        all_counts = count_vec.fit_transform(self.X)
        self.X = tfid.fit_transform(all_counts)

    def extract_y(self):
        binarizer = MultiLabelBinarizer()
        y = binarizer.fit_transform(self.y.split("_")) # split y by each technique as it was inserted into the database
        classes = binarizer.classes_ # get fitted classes

        # construct the output graph to identify relationships between classes
        nodes,edges,weights = self.create_graph_matricies(y,classes)
        nx_graph = nx.Graph()
        nx_graph.add_nodes_from(nodes)
        nx_graph.add_edges_from(edges)

        # fit node2vec, get dimension reduced embeddings
        n2v = Node2Vec(nx_graph,dimensions=32,walk_length=30,num_walks=300,workers=12)
        model = n2v.fit(window=10, min_count=1, batch_words=8)

        # encode y to embeddings then train
        new_y = self.embedding_encode(y,model)
        rnc = self.train_embedder(new_y,y)
        lin_reg = lm.LinearRegression(n_jobs=-1)
        X_train = self.X.toarray()
        lin_reg.fit(X_train,new_y)
        logging.info("base_model: regression model fit")
        logging.info("base_model: testing model...")

        # test data using f1 score to give users some verbosity on how well the model performed
        test = lin_reg.predict(X_train)
        lab = self.embedding_decode(test,rnc)
        score = f1_score(y,lab,average='weighted')
        logging.info("f1 score on training data: {}".format(score))
