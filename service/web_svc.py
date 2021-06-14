import asyncio
import newspaper
import nltk
import re
import requests

from bs4 import BeautifulSoup
from html2text import html2text
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer

# Abbreviated words for sentence-splitting
ABBREVIATIONS = {'dr', 'vs', 'mr', 'mrs', 'ms', 'prof', 'inc', 'fig', 'e.g', 'i.e', 'u.s'}


class WebService:
    def __init__(self):
        self.tokenizer_sen = nltk.data.load('tokenizers/punkt/english.pickle')
        try:
            self.tokenizer_sen._params.abbrev_types.update(ABBREVIATIONS)
        except AttributeError:
            pass

    async def map_all_html(self, url_input):
        a = newspaper.Article(url_input, keep_article_html=True)
        a.download()
        a.parse()
        results, plaintext, htmltext, images, seen_images = [], [], [], [], []
        images = await self._collect_all_images(a.images)
        plaintext = await self._extract_text_as_list(a.text)
        htmltext = await self._extract_html_as_list(a.article_html)

        # Loop through pt one by one, matching its line with a forward-advancing pointer on the html
        counter = 0
        for pt in plaintext:
            await asyncio.sleep(0.01)
            words = pt.split(' ')
            first_word = words[0]
            text_match_found = False
            image_found = False
            for forward_advancer in range(counter, len(htmltext)):
                if 'src=' in htmltext[forward_advancer] and htmltext[forward_advancer] not in seen_images and image_found is False:
                    # Found an image, put it in data but don't advance incase there's text.
                    soup = BeautifulSoup(htmltext[forward_advancer], 'html.parser')
                    source = soup.img['src']
                    img_dict = await self._match_and_construct_img(images, source)

                    results.append(img_dict)
                    seen_images.append(source)
                    image_found = True
        
                if first_word in htmltext[forward_advancer]:
                    # Found the matching word, put the text into the data.
                    res_dict = dict()
                    if '<h' in htmltext[forward_advancer]:
                        res_dict = await self._construct_text_dict(pt, 'header')
                    elif '<li' in htmltext[forward_advancer]:
                        res_dict = await self._construct_text_dict(pt, 'li')
                    else: 
                        res_dict = await self._construct_text_dict(pt, 'p')
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
        # A list where final_html_sentence_idxs[x] = y means final_html[x] contains data for sentences[y]
        final_html_sentence_idxs = []
        # Set for all the sentence index positions we have added to final_html
        seen_sentence_idxs = set()
        # Iterate through each html element to match it to its sentence and build final html
        for element in original_html:
            if element['tag'] == 'img' or element['tag'] == 'header':
                final_element = await self._build_final_image_dict(element)
                final_html.append(final_element)
                # This isn't a sentence but reflect something has been added to final_html by adding -1
                final_html_sentence_idxs.append(-1)
                continue
            # element is a full html element, can contain multiple lines
            # separate by each sentence
            html_sentences = self.tokenizer_sen.tokenize(element['text'])
            for single_sentence in html_sentences:
                # Use first few words to find matches amongst the sentences list
                words = single_sentence.split(' ')
                hint = words[0] + ' ' + words[1] + ' ' + words[2] if len(words) > 2 else words[0]
                # Iterate through sentences to find if the hint is in it and the sentence is one not added before
                for s_idx, sentence in enumerate(sentences):
                    if hint in sentence['text'] and s_idx not in seen_sentence_idxs:
                        final_element = self._build_final_html_text(sentence, single_sentence, element['tag'])
                        final_html.append(final_element)
                        # Make note of the index position in sentences has been added to final_html
                        final_html_sentence_idxs.append(s_idx)
                        seen_sentence_idxs.add(s_idx)
                        break
        # Before finishing, we can add any missing sentences
        # All possible sentence index positions
        all_sentence_idxs = set(range(len(sentences)))
        # Missing position positions = all minus seen
        missing_sentence_idxs = sorted(all_sentence_idxs - seen_sentence_idxs)
        # Go through each missing index position
        for sen_idx in missing_sentence_idxs:
            try:
                # Get the position in final_html of sentences[sen_idx-1] and +1 to add after previous sentence
                insert_pos = final_html_sentence_idxs.index(max(0, sen_idx - 1)) + 1
            except ValueError:  # case where missing sentence is first sentence so we'll insert at index 0
                insert_pos = 0
            # Build element dictionary for this sentence
            missing_elem = self._build_final_html_text(sentences[sen_idx], sentences[sen_idx]['text'], 'p')
            # Insert it into final_html
            final_html[insert_pos:0] = [missing_elem]
            # Update corresponding final_html_sentence_idxs to state where this sen_idx now is
            final_html_sentence_idxs[insert_pos:0] = [sen_idx]
        return final_html

    def tokenize_sentence(self, data):
        """
        :criteria: expects a dictionary of this structure:
        """
        html = self.tokenizer_sen.tokenize(data)
        sentences = []
        for current in html:
            # Further split by break tags as this might misplace highlighting in the front end
            no_breaks = [x for x in current.split('<br>') if x]
            for fragment in no_breaks:
                sentence_data = dict()
                sentence_data['html'] = fragment
                sentence_data['text'] = html2text(fragment)
                sentence_data['ml_techniques_found'] = []
                sentence_data['reg_techniques_found'] = []
                sentences.append(sentence_data)
        return sentences

    @staticmethod
    async def tokenize(s):
        """Function to remove stopwords from a sentence and return a list of words to match"""
        word_list = re.findall(r'\w+', s.lower())
        filtered_words = [word for word in word_list if word not in stopwords.words('english')]
        """Perform NLP Lemmatization and Stemming methods"""
        lemmed = []
        stemmer = SnowballStemmer('english')
        for i in filtered_words:
            await asyncio.sleep(0.001)
            lemmed.append(stemmer.stem(str(i)))
        return ' '.join(lemmed)

    @staticmethod
    async def remove_html_markup_and_found(s):
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

    @staticmethod
    async def get_url(url, returned_format=None):
        if returned_format == 'html':
            print('[!] HTML support is being refactored. Currently data is being returned plaintext')
        r = requests.get(url)
        await asyncio.sleep(0.01)

        b = newspaper.fulltext(r.text)
        return str(b).replace('\n', '<br>') if b else None

    @staticmethod
    async def _build_final_image_dict(element):
        final_element = dict()
        final_element['uid'] = element['uid']
        final_element['text'] = element['text']
        final_element['tag'] = element['tag']
        final_element['found_status'] = element['found_status']
        final_element['hits'] = None
        final_element['confirmed'] = 'false'
        return final_element


    @staticmethod
    def _build_final_html_text(sentence, single_sentence, tag):
        final_element = dict()
        final_element['uid'] = sentence['uid']
        final_element['text'] = single_sentence
        final_element['tag'] = tag
        final_element['found_status'] = sentence['found_status']
        final_element['hits'] = sentence['hits']
        final_element['confirmed'] = sentence['confirmed']
        return final_element

    @staticmethod
    async def _collect_all_images(image_set):
        images = []
        for image in image_set:
            images.append(image)
        return images

    @staticmethod
    async def _extract_text_as_list(plaintext_doc):
        plaintext = []
        for pt_line in plaintext_doc.split('\n'):
            if pt_line != '':
                plaintext.append(pt_line)
        return plaintext

    @staticmethod
    async def _extract_html_as_list(html_doc):
        htmltext = []
        for html_line in html_doc.split('\n'):
            htmltext.append(html_line)
        return htmltext

    @staticmethod
    async def _match_and_construct_img(images, source):
        for i in range(0, len(images)):
            if source in images[i]:
                source = images[i]
        img_dict = dict()
        img_dict['text'] = source
        img_dict['tag'] = 'img'
        img_dict['found_status'] = False
        img_dict['ml_techniques_found'] = []
        img_dict['res_techniques_found'] = []
        return img_dict

    @staticmethod
    async def _construct_text_dict(plaintext, tag):
        res_dict = dict()
        res_dict['text'] = plaintext
        res_dict['tag'] = tag
        res_dict['found_status'] = False
        res_dict['ml_techniques_found'] = []
        res_dict['res_techniques_found'] = []
        return res_dict
