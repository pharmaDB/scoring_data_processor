from collections import OrderedDict
import os
import re
from bson.objectid import ObjectId
import spacy

from orangebook.merge import OrangeBookMap
from similarity.no_dependent_claim import dependent_to_independent_claim
from db.mongo import connect_mongo
from utils.logging import getLogger

_logger = getLogger(__name__)

# Set up MongoDb Connection
_db = connect_mongo()
_label_collection = _db["labels"]
_patent_collection = _db["patents"]

# initialize OrangeBookMap
_ob = OrangeBookMap()

# Load scispaCy Models
# Need tokenizer for similarity. Other processing pipeline component do not
# affect results and can be excluded. scispaCy similarity is based on
# word2vec.See https://spacy.io/usage/linguistic-features# vectors-similarity
# Lemmatization is not important when using word2vec which runs on raw corpus
# (see
# https://stackoverflow.com/questions/23877375/word2vec-lemmatization-of-corpus-before-training)
# en_core_sci_lg_nlp = spacy.load(
#     "resources/models/en_core_sci_lg-0.4.0/en_core_sci_lg/en_core_sci_lg-0.4.0",
#     exclude=["tagger", "parser", "ner", "lemmatizer", "textcat", "custom"])
# en_core_sci_lg_nlp=None

# set number of processes for nlp.pipe for spaCy
N_PROCESS = 3

_RESOURCE_FOLDER = "resources"


def get_lines_in_file(file_name):
    ''' Returns a list of a lines in a file
    '''
    if os.path.exists(file_name):
        f = open(file_name, "r")
        completed_label_id = [line.strip() for line in f if line.strip()]
        f.close()
        return completed_label_id
    else:
        return []


def append_to_file(file_name, line):
    ''' Append line to end of file
    '''
    if os.path.exists(file_name):
        # append if already exists
        with open(file_name, 'a') as f:
            f.write("\n")
            f.write(line)
    else:
        # make a new file if non-existant
        if not os.path.exists(os.path.dirname(file_name)):
            os.makedirs(os.path.dirname(file_name))
        with open(file_name, 'w') as f:
            f.write(line)
    _logger.info(f"Appended to file: {file_name} line: {line}")


def get_num_in_str(text):
    ''' Return number for word composed of letter and number (ex: 'NDA019501')
    '''
    return int(re.match(r"([a-z]+)([0-9]+)", text, re.I).groups()[1])


def get_claims_in_patents_db(all_patents):
    '''
    Returns an OrderedDict of {patent_str:{claim_num:claim_text,},} from
    mongodb

    Parameters:
        all_patents (list): example: ['4139619', '4596812']
    '''
    # patent_od is returned and has form {patent_str:{claim_num:claim_text,},}
    patent_od = OrderedDict()
    for patent in all_patents:
        # claim_num_text_od = {claim_num:claim_text,}
        claim_num_text_od = OrderedDict()

        # patent_from_collection ex: {'_id':
        # ObjectId('6067476bedf3333608f5fe01'), 'patent_number': '4139619',
        # 'expiration_date': '1996-02-13', 'claims': [{'claim_number': 1,
        # 'claim_text': '1. A topical..',}]}
        patent_from_collection = _patent_collection.find_one(
            {'patent_number': str(patent)}, {
                'patent_number': 1,
                'claims': 1
            })
        # print(patent_from_collection)

        if not patent_from_collection:
            _logger.error(
                f"Unable to find: {str(patent)} in _patent_collection.")
        elif 'claims' not in patent_from_collection.keys():
            _logger.error(f"Patent: {str(patent)} missing 'claims' key.")
        else:
            # claims is in form [{'claim_number': 1, 'claim_text': '...'},]
            claims = patent_from_collection['claims']
            sorted(claims, key=lambda i: i['claim_number'])

            for claims in claims:
                claim_num_text_od[int(
                    claims['claim_number'])] = claims['claim_text']

        patent_od[patent] = claim_num_text_od
    return patent_od


def patent_claims_to_longhand(od):
    '''
    Return OrderedDict of {patent_str:{claim_num (int):[{'parent_clm':
    [independent_claim, ..., grand-parent_claim , parent_claim,],'text':
    claim_text},],},}

    Parameters:
        od (OrderedDict): {patent_str:{claim_num:claim_text,},}
    '''
    return_od = OrderedDict()
    for patent, claim_od in od.items():
        return_od[patent] = dependent_to_independent_claim(claim_od)
    return return_od


def add_nlp_doc(od):
    '''
    Return OrderedDict of {patent_str:{claim_num (int):[{'parent_clm':
        [independent_claim, ..., grand-parent_claim , parent_claim,],'text':
        claim_text, 'nlp_doc':nlp_doc_object},],},}

    Note the addition of the key and value 'nlp_doc':nlp_doc_object in the
    return object that missing from the parameter.

    Parameters:
        od (OrderedDict): {patent_str:{claim_num (int):[{'parent_clm':
                           [independent_claim, ..., grand-parent_claim ,
                           parent_claim,],'text': claim_text},],},}
    '''
    # get all claim_text from od in order in a list
    claim_text_list = []
    for patent in od.keys():
        for claim in od[patent].keys():
            for elem in od[patent][claim]:
                claim_text_list.append(elem['text'])

    # perform nlp.pipe() operation
    claim_text_nlp_values = list(
        en_core_sci_lg_nlp.pipe(claim_text_list, n_process=N_PROCESS))

    if len(claim_text_list) != len(claim_text_nlp_values):
        _logger.error(
            f"Mismatch between count of results from nlp.pipe() {len(claim_text_nlp_values)} and count of claim_text_list {len(claim_text_list)}."
        )

    # put all values in claim_text_nlp_values back into the od
    i = 0
    for patent in od.keys():
        for claim in od[patent].keys():
            for elem in od[patent][claim]:
                elem['nlp_doc'] = claim_text_nlp_values[i]
                i += 1
    return od


def get_claims_in_label_db(label_doc):
    '''
    Returns OrderedDict with {section_title:section_text,...} for
    a label from mongoDB

    Parameters:
        label_doc (dict): label doc from mongoDB
    '''
    return_od = OrderedDict()
    if 'sections' not in label_doc.keys():
        _logger.error(
            f"'sections' missing for label _id: {str(label_doc['_id'])}; set_id: {label_doc['set_id']}; spl_id: {label_doc['spl_id']}; spl_version: {label_doc['spl_version']}; published_date: {label_doc['published_date']}"
        )
    else:
        for section in label_doc['sections']:
            return_od['name'] = section['text']
    return return_od


def convert_label_text_to_nlp(label_section_od):
    '''
    Returns OrderedDict with {section_title:nlp_doc,...} for a label, wherein
    nlp_doc is the doc object after running through spaCy nlp

    Parameters:
        label_section_od (OrderedDict): {section_title:section_text,...}
    '''
    # turn section text from label into spaCy Doc object using nlp.pipe for
    # improved speed
    label_section_nlp_values = list(
        en_core_sci_lg_nlp.pipe(label_section_od.values(),
                                n_process=N_PROCESS))
    # label_section_vector_od={section_title:nlp_doc,}
    label_section_vector_od = OrderedDict(
        zip(label_section_od.keys(), label_section_nlp_values))
    return label_section_vector_od


def score_label_to_patent(label_section_od, patent_od):
    '''
    Computes similarity scores and returns OrderedDict of
    {section_title:[(patent_num, claim_num, parent_claims,
    similarity_score),...],...}, for a single label, wherein each (patent_num,
    claim_num, parent_claims, similarity_score) for a label section, as defined
    by section_title, is sorted from the most similar to most dissimilar claim.

    Parameters:
        label_section_od (OrderedDict):  {section_title:nlp_doc,...}
        patent_od (OrderedDict):  {patent_str:{claim_num
                (int):[{'parent_clm': [independent_claim, ...,
                grand-parent_claim , parent_claim,],'text': claim_text,
                'nlp_doc':nlp_doc_object},],},}
    '''
    # perform similarity comparison
    print("**label_section_od", label_section_od)
    print("**patent_od", patent_od)
    return_od = OrderedDict()
    for title in label_section_od.keys():
        section_nlp = label_section_od[title]
        if section_nlp:
            patent_claim_similarity_list = []
            for patent_str in patent_od.keys():
                for claim_num in patent_od[patent_str].keys():
                    # similarity_highest stores highest similarity for the many
                    # interpretation of a claim
                    similarity_highest = 0
                    parent_clm_w_highest_sim = []
                    for item in patent_od[patent_str][claim_num]:
                        similarity = section_nlp.similarity(item['nlp_doc'])
                        if similarity > similarity_highest:
                            similarity_highest = similarity
                            parent_clm_w_highest_sim = item['parent_clm']
                    patent_claim_similarity_list.append(
                        (patent_str, claim_num, parent_clm_w_highest_sim,
                         similarity_highest))
            # sort by similarity value
            patent_claim_similarity_list.sort(key=lambda x: x[3], reverse=True)
            return_od[title] = patent_claim_similarity_list
        else:
            return_od[title] = []

    print("return_od", return_od)
    return return_od


def upload_score_to_db(label_doc, similarity_od):
    '''
    Upload data from similiarity_od to mongoDB

    Parameters:
        label_doc (dict): label doc from mongoDB
        similarity_od (OrderedDict): {section_title:[(patent_num, claim_num,
                                      [parent_claims,], similarity_score),],}
    '''
    # add scores to section
    sections = label_doc['sections']
    for section in sections:
        title = section['name']
        try:
            similarity_list = similarity_od[title]
        except KeyError:
            _logger.error(f"Unable to find {title} in similarity_od: {str(similarity_od)[:500]}.  Will not update label id: {str(label_doc['_id'])}; set_id: {label_doc['set_id']}; spl_id: {label_doc['spl_id']}; spl_version: {label_doc['spl_version']}; published_date: {label_doc['published_date']}")
            return
        scores = []
        for i in range(5):
            # select the top 5 similarity results
            scores.append({
                'patentNumber': similarity_list[0],
                'claimNumber': similarity_list[1],
                'parentClaimNumbers': similarity_list[2],
                'score': similarity_list[3]
            })
        section['scores'] = scores
    label_doc['sections'] = sections
    result = _label_collection.replace_one({'_id': label_doc['_id']},
                                           label_doc)
    if result.matched_count < 1:
        _logger.error(
            f"Unable to update scores for label id: {str(label_doc['_id'])}; set_id: {label_doc['set_id']}; spl_id: {label_doc['spl_id']}; spl_version: {label_doc['spl_version']}; published_date: {label_doc['published_date']}"
        )
    else:
        _logger.info(f"Uploaded to DB label_doc: {str(label_doc)[:500]}")
    return


def process_similarity():
    # open log of processed label_id
    processed_label_id_file = os.path.join(_RESOURCE_FOLDER,
                                           'processed_id.txt')
    processed_label_id = get_lines_in_file(processed_label_id_file)

    # get list of all label _id excluding _id already processed
    all_label_id = [
        x for x in [str(y) for y in _label_collection.distinct("_id", {})]
        if x not in processed_label_id
    ]

    # loop through all_label_id
    while len(all_label_id) > 0:
        label_id_str = str(all_label_id[0])

        # get a list of NDA numbers (ex. ['NDA019501',]) associated with _id
        label_doc_application_numbers = _label_collection.find_one(
            {"_id": ObjectId(label_id_str)}, {
                '_id': 0,
                'application_numbers': 1
            })['application_numbers']

        # find all other docs with the same list of NDA numbers
        similar_label_docs = list(
            _label_collection.find(
                {"application_numbers": label_doc_application_numbers}))

        # all_patents = [[patent_str,],]
        all_patents = [
            _ob.get_patents(get_num_in_str(nda))
            for nda in label_doc_application_numbers
        ]
        # flatten all_patents into [patent_str,]
        all_patents = [j for i in all_patents for j in i]

        # patent_od = OrderedDict of {patent_str:{claim_num:claim_text,},}
        patent_od = get_claims_in_patents_db(all_patents)

        # claims_longhand_od = {patent_str:{claim_num (int):[{'parent_clm':
        #           [independent_claim, ..., grand-parent_claim ,
        #           parent_claim,],'text': claim_text},],},}
        claims_longhand_od = patent_claims_to_longhand(patent_od)

        # claims_longhand_with_nlp_od = {patent_str:{claim_num
        #           (int):[{'parent_clm': [independent_claim, ...,
        #           grand-parent_claim , parent_claim,],'text': claim_text,
        #           'nlp_doc':nlp_doc_object},],},}
        claims_longhand_with_nlp_od = add_nlp_doc(claims_longhand_od)

        for label_doc in similar_label_docs:
            _logger.info(
                    f"Processing Label id: {str(label_doc['_id'])}; application_number: {str(label_doc['application_numbers'])}; set_id: {label_doc['set_id']}; spl_id: {label_doc['spl_id']}; spl_version: {label_doc['spl_version']}; published_date: {label_doc['published_date']}"
            )

            # each label_doc consists of ex: {'_id':
            #       ObjectId('606731ccb4c4250dc86cc9ec'),
            #       'application_numbers': ['NDA019501'], 'set_id':
            #       '8bf0000c-95f3-4a4d-830b-f5ac1539823d', 'spl_id':
            #       '9474298e-9c69-490e-98a5-46b0f4e69b83', 'spl_version': '1',
            #       'published_date': '2016-12-19', 'sections': [{'name':
            #       name_text, 'text', text},]}

            label_id_str = str(label_doc['_id'])

            # label_section_od = {section_title:section_text,}
            label_section_od = get_claims_in_label_db(label_doc)

            # label_section_vector_od = {section_title:nlp_doc,}
            label_section_vector_od = convert_label_text_to_nlp(
                label_section_od)

            # score all labels to patents with same NDA numbers
            similarity_od = score_label_to_patent(label_section_vector_od,
                                                  claims_longhand_with_nlp_od)

            # upload similarity_od to mongodb for particular label
            upload_score_to_db(label_doc, similarity_od)

            try:
                all_label_id.remove(label_id_str)
                # record successful update to the database in record
                append_to_file(processed_label_id_file, str(label_id_str))
            except ValueError:
                _logger.error(
                    f"Unable to remove label_id_str: {label_id_str} from all_label_id"
                )


def process_similarity_simplified():
    # open log of processed label_id
    processed_label_id_file = os.path.join(_RESOURCE_FOLDER,
                                           'processed_id.txt')
    processed_label_id = get_lines_in_file(processed_label_id_file)

    # get list of all label _id excluding _id already processed
    all_label_id = [
        x for x in [str(y) for y in _label_collection.distinct("_id", {})]
        if x not in processed_label_id
    ]

    # loop through all_label_id
    while len(all_label_id) > 0:
        label_id_str = str(all_label_id[0])

        # get a list of NDA numbers (ex. ['NDA019501',]) associated with _id
        label_doc_application_numbers = _label_collection.find_one(
            {"_id": ObjectId(label_id_str)}, {
                '_id': 0,
                'application_numbers': 1
            })['application_numbers']

        # find all other docs with the same list of NDA numbers
        similar_label_docs = list(
            _label_collection.find(
                {"application_numbers": label_doc_application_numbers}))

        # all_patents = [[patent_str,],]
        all_patents = [
            _ob.get_patents(get_num_in_str(nda))
            for nda in label_doc_application_numbers
        ]
        # flatten all_patents into [patent_str,]
        all_patents = [j for i in all_patents for j in i]

        # patent_od = OrderedDict of {patent_str:{claim_num:claim_text,},}
        patent_od = get_claims_in_patents_db(all_patents)

        # claims_longhand_od = {patent_str:{claim_num (int):[{'parent_clm':
        #           [independent_claim, ..., grand-parent_claim ,
        #           parent_claim,],'text': claim_text},],},}
        claims_longhand_od = patent_claims_to_longhand(patent_od)

        # claims_longhand_with_nlp_od = {patent_str:{claim_num
        #           (int):[{'parent_clm': [independent_claim, ...,
        #           grand-parent_claim , parent_claim,],'text': claim_text,
        #           'nlp_doc':nlp_doc_object},],},}
        claims_longhand_with_nlp_od = add_nlp_doc(claims_longhand_od)

        for label_doc in similar_label_docs:
            _logger.info(
                    f"Processing Label id: {str(label_doc['_id'])}; application_number: {str(label_doc['application_numbers'])}; set_id: {label_doc['set_id']}; spl_id: {label_doc['spl_id']}; spl_version: {label_doc['spl_version']}; published_date: {label_doc['published_date']}"
            )

            # each label_doc consists of ex: {'_id':
            #       ObjectId('606731ccb4c4250dc86cc9ec'),
            #       'application_numbers': ['NDA019501'], 'set_id':
            #       '8bf0000c-95f3-4a4d-830b-f5ac1539823d', 'spl_id':
            #       '9474298e-9c69-490e-98a5-46b0f4e69b83', 'spl_version': '1',
            #       'published_date': '2016-12-19', 'sections': [{'name':
            #       name_text, 'text', text},]}

            label_id_str = str(label_doc['_id'])

            # label_section_od = {section_title:section_text,}
            label_section_od = get_claims_in_label_db(label_doc)

            # label_section_vector_od = {section_title:nlp_doc,}
            label_section_vector_od = convert_label_text_to_nlp(
                label_section_od)

            # score all labels to patents with same NDA numbers
            similarity_od = score_label_to_patent(label_section_vector_od,
                                                  claims_longhand_with_nlp_od)

            # upload similarity_od to mongodb for particular label
            upload_score_to_db(label_doc, similarity_od)

            try:
                all_label_id.remove(label_id_str)
                # record successful update to the database in record
                append_to_file(processed_label_id_file, str(label_id_str))
            except ValueError:
                _logger.error(
                    f"Unable to remove label_id_str: {label_id_str} from all_label_id"
                )
