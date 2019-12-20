import requests
from nltk.corpus import stopwords
import re
import nltk
import newspaper
from nltk.stem import SnowballStemmer
from html2text import html2text


class WebService:

    def __init__(self):
        pass

    async def tokenize_sentence(self, data):
        """
        :criteria: expects a dictionary of this structure:
        """
        tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
        html = tokenizer.tokenize(data)
        sentences = []
        for data in html:
            sentence_data = dict()
            sentence_data['html'] = data
            sentence_data['text'] = html2text(data)
            sentence_data['ml_techniques_found'] = []
            sentence_data['reg_techniques_found'] = []
            sentences.append(sentence_data)
        return sentences

    async def tokenize(self, s):
        """Function to remove stopwords from a sentence and return a list of words to match"""
        word_list = re.findall(r'\w+', s.lower())
        filtered_words = [word for word in word_list if word not in stopwords.words('english')]
        """Perform NLP Lemmatization and Stemming methods"""
        lemmed = []
        stemmer = SnowballStemmer('english')
        for i in filtered_words:
            lemmed.append(stemmer.stem(str(i)))
        return ' '.join(lemmed)

    @classmethod
    async def remove_html_markup_and_found(self, s):
        tag = False
        quote = False
        out = ""
        for c in s:
            if c == '<' and not quote:
                tag = True
            elif c == '>' and not quote:
                tag = False
            elif (c == '"' or c == "'") and tag:
                quote = not quote
            elif not tag:
                out = out + c
        sep = '!FOUND:'
        out = out.split(sep, 1)[0]
        return out

    async def get_url(self, url, returned_format=None):
        if returned_format == 'html':
            print('[!] HTML support is being refactored. Currently data is being returned plaintext')
        r = requests.get(url)

        b = newspaper.fulltext(r.text)
        if b:
            text = str(b).replace('\n', '<br>')
            print(type(text))
            return (text)
        else:
            return (None)

    async def get_url_old(self, url, returned_format='html'):
        """Function to download a webpage and return article title and content"""
        if returned_format == 'html':
            article = newspaper.Article(url, keep_article_html=True)
            article.download()
            article.parse()
            data = article.article_html

            return data

