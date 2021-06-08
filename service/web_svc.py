import asyncio
import logging
import newspaper
import nltk
import re
import requests

from bs4 import BeautifulSoup
from html2text import html2text
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer

# The different ways a sentence can end
SENTENCE_DELIMITERS = ['.', '!', '?']
# A sentence may also have these characters after a delimiter (e.g. end of a quote)
OPTIONAL_SENTENCE_DELIMITERS = ['"', '\'']
# Build a regex to detect these delimiters by `([part-1][part-2]?\s)`
# part-1 -> there must be an occurrence of one of these delimiters
# part-2 -> optional: there might be an occurrence of one of these delimiters; add ? after this
# \s -> A space before the next sentence
# (...) -> using capturing parentheses to store which delimiters occurred for a sentence
SENTENCE_DELIMITER_REGEX = '([' + ''.join([re.escape(x) for x in SENTENCE_DELIMITERS]) + ']' \
                           + '[' + ''.join([re.escape(x) for x in OPTIONAL_SENTENCE_DELIMITERS]) + ']?\\s)'


class WebService:

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
        # Sets for all the sentence uids and for those we have added to final_html
        all_sentence_uids, seen_uids = set(), set()
        report_uid = ''
        # Initially populate all_sentence_uids
        for sentence in sentences:
            all_sentence_uids.add(sentence['uid'])
            report_uid = sentence['report_uid']
        # Iterate through each html element to match it to its sentence and build final html
        for element in original_html:
            if element['tag'] == 'img' or element['tag'] == 'header':
                final_element = await self._build_final_image_dict(element)
                final_html.append(final_element)
                continue
            # element is a full html element, can contain multiple lines
            # separate by each sentence
            html_sentences = re.split(SENTENCE_DELIMITER_REGEX, element['text'])
            html_sentences = self._restore_periods_on_sentences(html_sentences)
            for single_sentence in html_sentences:
                # Use first few words to find matches amongst the sentences list
                words = single_sentence.split(' ')
                hint = words[0] + ' ' + words[1] + ' ' + words[2] if len(words) > 2 else words[0]
                # Iterate through sentences to find if the hint is in it and its uid is one not added before
                for sentence in sentences:
                    if hint in sentence['text'] and sentence['uid'] not in seen_uids:
                        final_element = await self._build_final_html_text(sentence, single_sentence, element['tag'])
                        final_html.append(final_element)
                        seen_uids.add(final_element['uid'])
                        break
        # Before finishing, we can report if any sentences are missing
        missing_uids = all_sentence_uids - seen_uids
        if len(missing_uids) < 5:
            missing_sentences = [x['text'] for x in sentences if x['uid'] in missing_uids]
            for missing in missing_sentences:
                logging.warning('Sentence \'' + missing[:20] + '...\' missing from html.')
        else:
            logging.warning(str(len(missing_uids)) + ' sentences missing from html for report ' + str(report_uid) + '.')
        return final_html

    @staticmethod
    async def tokenize_sentence(data):
        """
        :criteria: expects a dictionary of this structure:
        """
        tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
        html = tokenizer.tokenize(data)
        sentences = []
        for data in html:
            # Further split by break tags as this might misplace highlighting in the front end
            no_breaks = [x for x in data.split('<br>') if x]
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
    async def _build_final_html_text(sentence, single_sentence, tag):
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

    @staticmethod
    def _restore_periods_on_sentences(sentence_list):
        sen_len = len(sentence_list)
        # If the list is length 0 or 1, return as is
        if sen_len < 2:
            return sentence_list
        else:
            # The last sentence will have the period already there
            last = sentence_list[-1]
            new_sentence_list = []
            """
            Every sentence (apart from the last) will have its period in the neighbouring element.
            This is because SENTENCE_DELIMITER_REGEX uses capturing brackets hence the pattern causing the split
            e.g. '.' will be an element in sentence_list. Therefore this means sentence_list will have an odd number 
            of elements: for x sentences, sentence_list will have 2x elements (original element plus neighbouring 
            element for period) + 1 (plus 1 for last element with its period already there). 
            2x + 1 will always be odd.
            If for any reason sen_len is not odd, something has gone wrong -> report as a warning and add periods 
            back to the sentences the old way.
            """
            if sen_len % 2 == 0:
                logging.warning('Restored periods on sentence \'' + sentence_list[0][:20]
                                + '...\' did not work as expected. This may not load properly.')
                # Add a '.' to each sentence
                new_sentence_list = [sentence_list[i] + '.' for i in range(sen_len-1)]
            else:
                # Else concatenate the sentence with its neighbouring element to include its period
                for i in range(0, sen_len-1, 2):
                    new_sentence_list.append(sentence_list[i] + sentence_list[i+1].strip())
            # Finally, add the last element that didn't need concatenation
            new_sentence_list.append(last)
            return new_sentence_list
