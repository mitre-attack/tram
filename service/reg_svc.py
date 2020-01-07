import re


class RegService:

    # Service to analyze the text file against the attack-dict to find matches
    def __init__(self, dao):
        self.dao = dao

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
            attack_tid = attack_uid[0]['tid']
            await self.dao.insert('report_sentence_hits',
                                  dict(uid=sentence_id, attack_uid=attack_technique,
                                       attack_technique_name=attack_technique_name, report_uid=report_id, attack_tid = attack_tid))