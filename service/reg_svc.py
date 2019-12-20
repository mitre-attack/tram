import re


class RegService:

    # Service to analyze the text file against the attack-dict to find matches
    def __init__(self, dao):
        self.dao = dao

    def similar_word_matcher(self, attack_dict, sentence, items_to_search):
        """Main function that performs matching. Requires attack_dict and tokenized data"""
        # This var is for particular strings that have a high level of error rates. Manually managed for the time being.
        blacklisted_similar_words = ['at']
        # Master dictionary to have a summary of where all the hits occured. Will eventually feedback into the ML models
        context_hits = {}
        # List of only the hit item. This is for support with the docx writer functionality
        only_hits = []
        for technique, details in attack_dict.items():
            # print(technique)
            if details['id'] in items_to_search:
                print('[!] Checking: {}'.format(details['id']))
                # Section for particular item coloring. Currently red for technique, and blue for software
                if details['id'].upper().startswith('T'):
                    highligt_color = 'red'
                elif details['id'].upper().startswith('S'):
                    highligt_color = 'blue'
                # Ensure that a similar_words key exists
                if 'similar_words' in details:
                    # collapse down all similar words so that we mitigate duplicate hits
                    similar_words = [x.lower() for x in details['similar_words']]
                    similar_words.sort(key=len, reverse=True)
                    similar_words = list(set(similar_words))
                    for word in similar_words:
                        # for index,sen in document.items():
                        if word not in blacklisted_similar_words:
                            if word.lower() in sentence.lower():
                                print('[#] Found: {}-{}'.format(details['id'], details['name']))
                                # This is a hacky way of making sure that the matched words start with our keywords.... e.g. making sure "tor" doesn't hit on "actor"
                                # Testing with trailing space -- need to add logic to only do this for software
                                if ' {} '.format(word.lower()) in sentence.lower():
                                    only_hits.append("{}-{}".format(details['id'], details['name']))
                                    # We use a regex sub in order to get around .replace() case sensitivity.
                                    insensitive_re = re.compile(re.escape(word.upper()), re.IGNORECASE)
                                    sentence = insensitive_re.sub(
                                        "<font color='{}'><b>>{}></b></font><b> {}</b>".format(highligt_color,
                                                                                               details['id'], word),
                                        sentence)

                                    # We add the hit to the context_hits dict
                                    if "{}-{}".format(details['id'], details['name']) not in context_hits:
                                        context_hits["{}-{}".format(details['id'], details['name'])] = [sentence]
                                    else:
                                        if sentence not in context_hits["{}-{}".format(details['id'], details['name'])]:
                                            context_hits["{}-{}".format(details['id'], details['name'])].append(
                                                sentence)
                                else:
                                    print('[!] Skipping match of similar word: "{}" for missing a leading space'.format(
                                        word))
                else:
                    print('[!] Error, {} is missing the "similar_words" key, skipping technique'.format(details['id']))
        # Here is where we insert the "pretty name" of the technique. The reason we don't do this earlier is incase the technique name contains strings that other techiniques queue off of
        for technique, details in attack_dict.items():
            if '>{}>'.format(technique) in sentence:
                sentence = sentence.replace('>{}>'.format(technique), ">{}-{}>".format(technique, details['name']))
        return (sentence, context_hits, only_hits)

    @classmethod
    def find_techniques(self, jupyter_doc_markup, list_of_sentences, techniques_found, techniques, list_of_legacy):
        for senid in range(0, len(jupyter_doc_markup)):
            jupyter_doc_markup[senid], _, hit_names = self.similar_word_matcher(self, techniques,
                                                                                jupyter_doc_markup[senid],
                                                                                list_of_legacy)
            if hit_names:
                for hit in hit_names:
                    sen = list_of_sentences[senid]
                    if hit not in techniques_found[sen]:
                        techniques_found[sen].append(hit)

    def analyze_document(self, regex_pattern, sentence):
        cleaned_sentence = sentence['text']
        if re.findall(regex_pattern['regex_pattern'], cleaned_sentence, re.IGNORECASE):
            print('Found {} in {}'.format(regex_pattern, cleaned_sentence))
            return True
        else:
            return False

    @classmethod
    def analyze_html(self, regex_patterns, html_sentences):
        for regex_pattern in regex_patterns:
            count = 0
            for sentence in html_sentences:
                sentence_analysis = self.analyze_document(self, regex_pattern, sentence)
                if sentence_analysis:
                    html_sentences[count]['reg_techniques_found'].append(regex_pattern['attack_uid'])
                count += 1
        return html_sentences

    async def reg_techniques_found(self, report_id, sentence):
        sentence_id = await self.dao.insert('report_sentences',
                                            dict(report_uid=report_id, text=sentence['text'],
                                                 html=sentence['html'], found_status="true"))
        for technique in sentence['reg_techniques_found']:
            attack_uid = await self.dao.get('attack_uids', dict(name=technique))
            if not attack_uid:
                attack_uid = await self.dao.get('attack_uids', dict(tid=technique))
                if not attack_uid:
                    attack_uid = await self.dao.get('attack_uids', dict(uid=technique))
            attack_technique = attack_uid[0]['uid']
            attack_technique_name = '{} (r)'.format(attack_uid[0]['name'])
            await self.dao.insert('report_sentence_hits',
                                  dict(uid=sentence_id, attack_uid=attack_technique,
                                       attack_technique_name=attack_technique_name, report_uid=report_id))