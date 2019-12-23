import requests
from nltk.corpus import stopwords
import re
import nltk
import newspaper
from nltk.stem import SnowballStemmer
from html2text import html2text
import bs4
from bs4 import BeautifulSoup
from urllib.parse import urlparse


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
        position = 0
        for data in html:
            position += 1
            sentence_data = dict()
            sentence_data['html'] = data
            sentence_data['text'] = html2text(data)
            sentence_data['ml_techniques_found'] = []
            sentence_data['reg_techniques_found'] = []
            sentences.append(sentence_data)
            # print("TOKEN: ", data)
            # print("Number of sentences added: ", position)
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

    # async def find_full_source(self, images, source):
    #     """"Expected input: images - list of full sources (including hostname); source - partial url (no hostname) """
    #     for i in range(0, len(images)):
    #         if source in images[i]:
    #             return images[i]
    #     return source

    async def map_all_html(self, url_input):
        a = newspaper.Article(url_input, keep_article_html=True)
        a.download()
        a.parse()
        results = []
        plaintext = []
        htmltext = []
        images = []

        # Collect all images in a list
        for image in a.images:
            images.append(image)

        # Collect all the text lines in both pt and html
        for pt_line in a.text.split('\n'):
            if pt_line != '':
                plaintext.append(pt_line)

        for html_line in a.article_html.split('\n'):
            htmltext.append(html_line)

        # Loop through pt one by one, matching its line with a forward-advancing pointer on the html
        counter = 0
        seen_images = []
        for pt in plaintext:
            words = pt.split(' ')
            first_word = words[0]
            text_match_found = False
            image_found = False
            for forward_advancer in range(counter, len(htmltext)):
                if '<h' in htmltext[forward_advancer]:
                    print('Found a header')
                if 'src=' in htmltext[forward_advancer] and htmltext[
                    forward_advancer] not in seen_images and image_found is False:
                    # Found an image, put it in data but don't advance incase there's text.
                    soup = BeautifulSoup(htmltext[forward_advancer], 'html.parser')
                    source = soup.img['src']
                    # full_source = await find_full_source(images, source)
                    for i in range(0, len(images)):
                        if source in images[i]:
                            source = images[i]

                    img_dict = dict()
                    img_dict['text'] = source
                    img_dict['tag'] = 'img'
                    img_dict['found_status'] = False
                    img_dict['ml_techniques_found'] = []
                    img_dict['res_techniques_found'] = []

                    results.append(img_dict)
                    seen_images.append(source)
                    image_found = True
                if first_word in htmltext[forward_advancer]:
                    # Found the matching word, put the text into the data.
                    res_dict = dict()
                    res_dict['text'] = pt
                    res_dict['tag'] = 'p'
                    res_dict['found_status'] = False
                    res_dict['ml_techniques_found'] = []
                    res_dict['res_techniques_found'] = []
                    results.append(res_dict)
                    counter = forward_advancer + 1
                    text_match_found = True
                    break
            if image_found is True and text_match_found is False:
                # Didn't find matching text, but found an image. Image is misplaced.
                seen_images = seen_images[:-1]
                results = results[:-1]
        return results

    async def build_final_html(self, original_html, sentences):
        final_html = []
        for element in original_html:
            if element['tag'] == 'img':
                final_element = dict()
                final_element['uid'] = element['uid']
                final_element['text'] = element['text']
                final_element['tag'] = element['tag']
                final_element['found_status'] = element['found_status']
                final_element['hits'] = None
                final_element['confirmed'] = 'false'
                final_html.append(final_element)
                continue

            # element is a full html element, can contain multiple lines
            # separate by each sentence FIXTHIS naming
            tokens = element['text'].split('. ')
            for token in tokens:
                token_found = False
                # print(token)
                words = token.split(' ')
                hint = words[0] + ' ' + words[1] + ' ' + words[2] if len(words) > 2 else words[0]
                for sentence in sentences:
                    if hint in sentence['text']:
                        token_found = True
                        final_element = dict()
                        final_element['uid'] = sentence['uid']
                        final_element['text'] = token
                        final_element['tag'] = 'p'
                        final_element['found_status'] = sentence['found_status']
                        final_element['hits'] = sentence['hits']
                        final_element['confirmed'] = sentence['confirmed']
                        final_html.append(final_element)
                        break
        return final_html

