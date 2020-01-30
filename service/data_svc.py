import re
import json
import logging
from taxii2client import Collection
from stix2 import TAXIICollectionSource, Filter


def defang_text(text):
    """
    Function to normalize quoted data to be sql compliant
    :param text: Text to be defang'd
    :return: Defang'd text
    """
    text = text.replace("'", "''")
    text = text.replace('"', '""')
    return text


class DataService:

    def __init__(self, dao, web_svc):
        self.dao = dao
        self.web_svc = web_svc

    async def reload_database(self, schema='conf/schema.sql'):
        """
        Function to reinitialize the database with the packaged schema
        :param schema: SQL schema file to build database from
        :return: nil
        """
        with open(schema) as schema:
            await self.dao.build((schema.read()))

    async def insert_attack_stix_data(self):
        """
        Function to pull stix/taxii information and insert in to the local db
        :return: status code
        """
        logging.info('Downloading ATT&CK data from STIX/TAXII...')
        attack = {}
        collection = Collection("https://cti-taxii.mitre.org/stix/collections/95ecc380-afe9-11e4-9b6c-751b66dd541e/")
        tc_source = TAXIICollectionSource(collection)
        filter_objs = {"techniques": Filter("type", "=", "attack-pattern"),
                       "groups": Filter("type", "=", "intrusion-set"), "malware": Filter("type", "=", "malware"),
                       "tools": Filter("type", "=", "tool"), "relationships": Filter("type", "=", "relationship")}
        for key in filter_objs:
            attack[key] = tc_source.query(filter_objs[key])
        references = {}

        # add all of the patterns and dictionary keys/values for each technique and software
        for i in attack["techniques"]:
            references[i["id"]] = {"name": i["name"], "id": i["external_references"][0]["external_id"],
                                   "example_uses": [],
                                   "description": i['description'].replace('<code>', '').replace('</code>', '').replace(
                                       '\n', '').encode('ascii', 'ignore').decode('ascii'),
                                   "similar_words": [i["name"]]}

        for i in attack["relationships"]:
            if i["relationship_type"] == 'uses':
                if 'attack-pattern' in i["target_ref"]:
                    use = i["description"]
                    # remove unnecessary strings, fix unicode errors
                    use = use.replace('<code>', '').replace('</code>', '').replace('"', "").replace(',', '').replace(
                        '\t', '').replace('  ', ' ').replace('\n', '').encode('ascii', 'ignore').decode('ascii')
                    find_pattern = re.compile('\[.*?\]\(.*?\)')  # get rid of att&ck reference (name)[link to site]
                    m = find_pattern.findall(use)
                    if len(m) > 0:
                        for j in m:
                            use = use.replace(j, '')
                            if use[0:2] == '\'s':
                                use = use[3:]
                            elif use[0] == ' ':
                                use = use[1:]
                    # combine all the examples to one list
                    references[i["target_ref"]]["example_uses"].append(use)

        for i in attack["malware"]:
            if 'description' not in i:  # some software do not have description, example: darkmoon https://attack.mitre.org/software/S0209
                continue
            else:
                references[i["id"]] = {"id": i['id'], "name": i["name"], "description": i["description"],
                                       "examples": [], "example_uses": [], "similar_words": [i["name"]]}
        for i in attack["tools"]:
            references[i["id"]] = {"id": i['id'], "name": i["name"], "description": i["description"], "examples": [],
                                   "example_uses": [], "similar_words": [i["name"]]}

        attack_data = references
        logging.info("Finished...now creating the database.")

        cur_uids = await self.dao.get('attack_uids') if await self.dao.get('attack_uids') else []
        cur_items = [i['uid'] for i in cur_uids]
        for k, v in attack_data.items():
            if k not in cur_items:
                await self.dao.insert('attack_uids', dict(uid=k, description=defang_text(v['description']), tid=v['id'],
                                                          name=v['name']))
                if 'regex_patterns' in v:
                    [await self.dao.insert('regex_patterns', dict(uid=k, regex_pattern=defang_text(x))) for x in
                     v['regex_patterns']]
                if 'similar_words' in v:
                    [await self.dao.insert('similar_words', dict(uid=k, similar_word=defang_text(x))) for x in
                     v['similar_words']]
                if 'false_negatives' in v:
                    [await self.dao.insert('false_negatives', dict(uid=k, false_negative=defang_text(x))) for x in
                     v['false_negatives']]
                if 'false_positives' in v:
                    [await self.dao.insert('false_positives', dict(uid=k, false_positive=defang_text(x))) for x in
                     v['false_positives']]
                if 'true_positives' in v:
                    [await self.dao.insert('true_positives', dict(uid=k, true_positive=defang_text(x))) for x in
                     v['true_positives']]
                if 'example_uses' in v:
                    [await self.dao.insert('true_positives', dict(uid=k, true_positive=defang_text(x))) for x in
                     v['example_uses']]
        logging.info('[!] DB Item Count: {}'.format(len(await self.dao.get('attack_uids'))))

    async def insert_attack_json_data(self, buildfile):
        """
        Function to read in the enterprise attack json file and insert data into the database
        :param buildfile: Enterprise attack json file to build from
        :return: nil
        """
        cur_items = [x['uid'] for x in await self.dao.get('attack_uids')]
        logging.debug('[#] {} Existing items in the DB'.format(len(cur_items)))
        with open(buildfile, 'r') as infile:
            attack_dict = json.load(infile)
            loaded_items = {}
            # Extract all TIDs
            for item in attack_dict['objects']:
                if 'external_references' in item:
                    # Filter down
                    if any(x for x in item['external_references'] if x['source_name'] == 'mitre-attack'):
                        items = [x['external_id'] for x in item['external_references'] if
                                 x['source_name'] == 'mitre-attack']
                        if len(items) == 1:
                            tid = items[0]
                            # Add in
                            if tid.startswith('T') and not tid.startswith('TA'):
                                if item['type'] == "attack-pattern":
                                    loaded_items[item['id']] = {'id': tid, 'name': item['name'],
                                                                'examples': [],
                                                                'similar_words': [],
                                                                'description': item['description'],
                                                                'example_uses': []}
                        else:
                            logging.critical('[!] Error: multiple MITRE sources: {} {}'.format(item['id'], items))
            # Extract uses for all TIDs
            for item in attack_dict['objects']:
                if item['type'] == 'relationship':
                    if item["relationship_type"] == 'uses':
                        if 'description' in item:
                            normalized_example = item['description'].replace('<code>', '').replace('</code>',
                                       '').replace('\n', '').encode('ascii', 'ignore').decode('ascii')
                            # Remove att&ck reference (name)[link to site]
                            normalized_example = re.sub('\[.*?\]\(.*?\)', '', normalized_example)
                            if item['target_ref'].startswith('attack-pattern'):
                                if item['target_ref'] in loaded_items:
                                    loaded_items[item['target_ref']]['example_uses'].append(normalized_example)
                                else:
                                    logging.critical('[!] Found target_ref not in loaded data: {}'.format(item['target_ref']))
        logging.debug("[#] {} Techniques found in input file".format(len(loaded_items)))
        # Deduplicate input data from existing items in the DB
        to_add = {x: y for x, y in loaded_items.items() if x not in cur_items}
        logging.debug('[#] {} Techniques found that are not in the existing database'.format(len(to_add)))
        for k, v in to_add.items():
            await self.dao.insert('attack_uids', dict(uid=k, description=defang_text(v['description']), tid=v['id'],
                                                      name=v['name']))
            if 'example_uses' in v:
                [await self.dao.insert('true_positives', dict(uid=k, true_positive=defang_text(x))) for x in
                 v['example_uses']]

    async def status_grouper(self, status):
        reports = await self.dao.get('reports', dict(current_status=status))
        for report in reports:
            report.update(dict(link="/edit/{}".format(report['title'])))
        return reports

    async def last_technique_check(self, criteria):
        await self.dao.delete('report_sentence_hits', dict(uid=criteria['sentence_id'], attack_uid=criteria['attack_uid']))
        number_of_techniques = await self.dao.get('report_sentence_hits', dict(uid=criteria['sentence_id']))
        if len(number_of_techniques) == 0:
            await self.dao.update('report_sentences', 'uid', criteria['sentence_id'], dict(found_status='false'))
            return dict(status='true')
        else:
            return dict(status='false', id=criteria['sentence_id'])

    async def build_sentences(self, report_id):
        sentences = await self.dao.get('report_sentences', dict(report_uid=report_id))
        for sentence in sentences:
            sentence['hits'] = await self.dao.get('report_sentence_hits', dict(uid=sentence['uid']))
            if await self.dao.get('true_positives', dict(sentence_id=sentence['uid'])):
                sentence['confirmed'] = 'true'
            else:
                sentence['confirmed'] = 'false'
        return sentences

    async def get_techniques(self):
        techniques = await self.dao.get('attack_uids')
        return techniques

    async def get_confirmed_techniques(self, report_id):
        # The SQL select join query to retrieve the confirmed techniques for the report from the database
        select_join_query = (
            f"SELECT report_sentences.uid, report_sentence_hits.attack_uid, report_sentence_hits.report_uid, report_sentence_hits.attack_tid, true_positives.true_positive " 
            f"FROM ((report_sentences INNER JOIN report_sentence_hits ON report_sentences.uid = report_sentence_hits.uid) " 
            f"INNER JOIN true_positives ON report_sentence_hits.uid = true_positives.sentence_id AND report_sentence_hits.attack_uid = true_positives.uid) " 
            f"WHERE report_sentence_hits.report_uid = {report_id} "
            f"UNION "
            f"SELECT report_sentences.uid, report_sentence_hits.attack_uid, report_sentence_hits.report_uid, report_sentence_hits.attack_tid, false_negatives.false_negative " 
            f"FROM ((report_sentences INNER JOIN report_sentence_hits ON report_sentences.uid = report_sentence_hits.uid) " 
            f"INNER JOIN false_negatives ON report_sentence_hits.uid = false_negatives.sentence_id AND report_sentence_hits.attack_uid = false_negatives.uid) " 
            f"WHERE report_sentence_hits.report_uid = {report_id}")
        # Run the SQL select join query
        hits = await self.dao.raw_select(select_join_query)
        techniques = []
        for hit in hits:
            # For each confirmed technique returned,
            # create a technique object and add it to the list of techniques.
            technique = {}
            technique['score'] = 1
            technique['techniqueID'] = hit['attack_tid'] 
            technique['comment'] = hit['true_positive']
            techniques.append(technique)
        # Return the list of confirmed techniques
        return techniques

    async def ml_reg_split(self, techniques):
        list_of_legacy, list_of_techs = [], []
        for k, v in techniques.items():
            try:
                if len(v['example_uses']) > 8:
                    list_of_techs.append(v['name'])
                else:
                    list_of_legacy.append(v['id'])
            except:
                print(v)
        return list_of_legacy, list_of_techs

