from collections import OrderedDict
from bson.objectid import ObjectId
from sentence_transformers import SentenceTransformer, util
import html

from orangebook.merge import OrangeBookMap
from similarity.no_dependent_claim import dependent_to_independent_claim
from db.mongo import connect_mongo, update_db
from utils import misc
from utils.logging import getLogger

_logger = getLogger(__name__)

# Store name string and MongoDB collection object
_label_collection_name = None
_label_collection = None
_patent_collection_name = None
_patent_collection = None

# initialize OrangeBookMap
_ob = OrangeBookMap()

# initialize SentenceTransformer models
_device = None
# model = SentenceTransformer("allenai/scibert_scivocab_uncased", device=_device)
# model = SentenceTransformer("allenai/scibert_scivocab_cased", device = "cpu")
# model = SentenceTransformer("dmis-lab/biobert-large-cased-v1.1", device=_device)
# model = SentenceTransformer("stsb-distilbert-base", device=_device)
model = SentenceTransformer("stsb-distilroberta-base-v2", device=_device)

# common value is 512, longer sentences are truncated
# print("Max Sequence Length:", model.max_seq_length)
model.max_seq_length = 512


def add_patent_map(docs, application_numbers):
    """
    Add to each doc in docs a mapping to patents for each NDA

    Parameters:
        docs (list): list of label docs from MongoDB having the same
                     application_numbers
        application_numbers (list): a list of application numbers such as
                                    ['NDA204223',]
    """
    all_patents = [
        {
            "application_number": str(nda),
            "patents": _ob.get_patents(misc.get_num_in_str(nda)),
        }
        for nda in application_numbers
    ]
    for doc in docs:
        doc["nda_to_patent"] = all_patents
    return docs


def get_claims_in_patents_db(all_patents):
    """
    Returns an dict of OrderedDict {patent_str:OrderedDict([(claim_num,
    claim_text), ]), } from mongodb.  Order of claim number is important for
    references to preceding claims, so the inner dict must be an OrderedDict.

    Parameters:
        all_patents (list): example: ['4139619', '4596812']
    """
    # patent_dict is returned and has form {patent_str:{claim_num:claim_text,},}
    patent_dict = {}
    for patent in all_patents:
        claim_num_text_od = OrderedDict()
        # patent_from_collection ex: {'_id': ObjectId('unique_string'),
        # 'patent_number': '4139619', 'expiration_date': '1996-02-13',
        # 'claims': [{'claim_number': 1, 'claim_text': '1. A topical..',}]}
        patent_from_collection = _patent_collection.find_one(
            {"patent_number": str(patent)}, {"patent_number": 1, "claims": 1}
        )
        if not patent_from_collection:
            _logger.error(
                f"Unable to find: {str(patent)} in collection: "
                f"{_patent_collection_name}."
            )
            return {}
        elif "claims" not in patent_from_collection.keys():
            _logger.error(f"Patent: {str(patent)} missing 'claims' key.")
            return {}
        else:
            # claims is in form [{'claim_number': 1, 'claim_text': '...'},]
            claims = patent_from_collection["claims"]
            sorted(claims, key=lambda i: i["claim_number"])
            for claim in claims:
                claim_num_text_od[int(claim["claim_number"])] = html.unescape(
                    claim["claim_text"]
                )
        patent_dict[patent] = claim_num_text_od
    return patent_dict


def patent_claims_longhand_form_from_NDA(application_numbers):
    """
    Return dict of:
        {patent_str: {claim_num (int): [{'parent_clm': [independent_claim_num,
        ..., parent_claim_num, grand-parent_claim_num], 'text': claim_text}, ],
        }, }
    wherein the value assigned to claim_num is a list that contains all
    interpretation of that claim when written in long hand form, without any
    dependencies.

    Parameters:
        application_numbers (list): a list of application numbers such as
                                    ['NDA204223',]
    """
    # all_patents = [[patent_str,],]
    all_patents = [
        _ob.get_patents(misc.get_num_in_str(nda)) for nda in application_numbers
    ]
    # flatten all_patents into [patent_str,]
    all_patents = [j for i in all_patents for j in i]
    all_patents = list(set(all_patents))
    # patent_dict = {patent_str:OrderedDict([(claim_num, claim_text),]),}
    patent_dict = get_claims_in_patents_db(all_patents)
    # patent_longhand_dict is returned
    patent_longhand_dict = {}
    for patent, claim_od in patent_dict.items():
        patent_longhand_dict[patent] = dependent_to_independent_claim(
            claim_od, patent
        )
    return patent_longhand_dict


def patent_dict_of_dict_to_list_of_list(dict_of_dict):
    """
    Return list of list.  For example returns:
        [[patent_num, claim_num, parent_clm_list, claim_text],...]

    Wherein parent_clm_list is:
        [independent_claim_num, ..., parent_claim_num, grand-parent_claim_num]

    Parameters:
        dict_of_dict (dict): {patent_str: {claim_num (int): [{'parent_clm':
                    [independent_claim_num, ..., parent_claim_num,
                    grand-parent_claim_num], 'text': claim_text}, ], }, }

    """
    return_list = []
    for patent_num in dict_of_dict.keys():
        for claim_num, value_list in dict_of_dict[patent_num].items():
            for value_elem in value_list:
                return_list.append(
                    [
                        patent_num,
                        claim_num,
                        value_elem["parent_clm"],
                        value_elem["text"],
                    ]
                )
    return return_list


def get_list_of_additions(docs):
    """
    Return a list of distinct expanded_content from the additions of all docs
    in similar_label_docs in the form:
        [[expanded_content], ...]

    Parameters:
        docs (list): list of label docs from MongoDB having the same
                     application_numbers
    """
    return_list = []
    for doc in docs:
        if doc["additions"]:
            for value in doc["additions"].values():
                if value["expanded_content"] not in return_list:
                    return_list.append([value["expanded_content"]])
    return return_list


def preprocess(matrix, index, trunc_clm=False):
    """
    Takes as list of lists (in other words a matrix), and returns a list of
    pre-proposed sentences for all elements at the index specified for the
    inner list.

    For BERT models, dropping punctuation affects accuracy. See
    https://www.aclweb.org/anthology/2020.pam-1.15.pdf.  The BERT models
    should also handle case or uncased situations automatically.

    Bert models generally are not able to embed text with more than 512 tokens
    and will automatically truncate longer text inputs.  (The exception to rule
    is for models such as Longformer or Bert-AL, or Reformer. However Bert-AL
    and Reformer are unavailable as HuggingFace models, and Longformer performs
    poorly based on a few similarity test case examples.) To process longer
    claim text, this method can the end of the claim if trunc_clm is True. The
    end of the claims, when written in long hand form is more important, since
    it is generally where new claim subject matter is recited for dependent
    claims.

    Parameters:
        matrix (list): a list of lists
        index (int): index of inner list starting at 0.
        trunc_clm (bool): optional parameter to keep preamble and end of claim text
    """

    def remove_endline_plus_truncate(text, trunc_clm):
        text_split = text.split()
        if (
            trunc_clm
            and model.max_seq_length
            and len(text_split) > model.max_seq_length
        ):
            return " ".join(text_split[-model.max_seq_length :])
        else:
            return " ".join(text_split)

    return_list = [
        remove_endline_plus_truncate(row[index], trunc_clm) for row in matrix
    ]
    return return_list


def rank_and_score(docs, additions_list, patent_list, num_scores=3):
    """
    Returns a list of label docs in MongoDB format, wherein each doc includes
    doc['additions'][X]['scores'] if doc['additions'][X] exists.

    Example of doc['additions'][X]['scores']:
        [
            {
                patent_number: '5202128',
                claim_number: 6,
                parent_claim_numbers: [
                    1,
                    5
                ],
                score: 0.8
            },
        ]

    Parameters:
        docs (list): list of label docs from MongoDB having the same
                     application_numbers
        additions_list (list): [[expanded_content], ...]
        patent_list (list): [[patent_num, claim_num, parent_clm_list,
                             claim_text],..]
        num_scores (int): number of scores to include with each addition
    """
    # create 2 lists of cleaned texts (ex: [expanded_content,] or [claim_text,])
    additions = preprocess(additions_list, 0)
    claims = preprocess(patent_list, 3, True)

    # Compute embedding for both lists
    additions_embeddings = model.encode(
        additions,
        convert_to_tensor=True,
    )
    claims_embeddings = model.encode(
        claims,
        convert_to_tensor=True,
    )

    # Compute cosine-similarity for every additions to every claim
    cosine_scores = util.pytorch_cos_sim(
        additions_embeddings, claims_embeddings
    )
    cosine_scores = cosine_scores.tolist()
    indices_of_claims = list(range(len(claims)))

    # addition_to_score_index= {"expanded_content":[(score, index),]} wherein
    # (score, index) is sorted from highest to lowest score for each
    # "expanded_content"
    addition_to_score_index = {}
    for i in range(len(additions)):
        addition_to_score_index[additions_list[i][0]] = sorted(
            zip(cosine_scores[i], indices_of_claims), reverse=True
        )[:num_scores]

    for doc in docs:
        if doc["additions"]:
            for key, value in doc["additions"].items():
                score_index_list = addition_to_score_index[
                    value["expanded_content"]
                ]
                doc["additions"][key]["scores"] = [
                    {
                        "patent_number": patent_list[item[1]][0],
                        "claim_number": patent_list[item[1]][1],
                        "parent_claim_numbers": patent_list[item[1]][2],
                        "score": item[0],
                    }
                    for item in score_index_list
                ]
    return docs


def setup_MongoDB(
    label_collection_name, patent_collection_name, alt_db_name=""
):
    """
    This method sets up the MongoDB connection for all methods for this module.

    Parameters:
        label_collection_name (String): name of the label collection
        patent_collection_name (String): name of the patent collection
        alt_db_name (String): this is an optional argument that will set the
                    db_name to a value other than the value in the .env file.
    """
    db = connect_mongo(alt_db_name)
    global _label_collection_name, _label_collection
    global _patent_collection_name, _patent_collection
    _label_collection_name = label_collection_name
    _label_collection = db[label_collection_name]
    _patent_collection_name = patent_collection_name
    _patent_collection = db[patent_collection_name]


def additions_in_diff_against_previous_label(docs):
    """
    Add additions back to each diff_against_previous_label['text'][X][0] that
    is 1.  This feature is requested by the front end.

    Parameters:
    docs (list): list of sorted label docs from mongodb having the same
                 application_numbers
    """
    for doc in docs:
        if doc["additions"]:
            for diff in doc["diff_against_previous_label"]:
                for text in diff["text"]:
                    if text[0] == 1 and len(text) > 2 and text[2]:
                        text = text[:3]
                        text.append(doc["additions"][text[2]])


def run_similarity(
    label_collection_name,
    patent_collection_name,
    processed_label_ids_file,
    processed_nda_file,
    unprocessed_label_ids_file,
    unprocessed_nda_file,
    alt_db_name="",
):
    """
    This method calls other methods in this module and tracks completed label
    IDs and completed NDA numbers.

    Parameters:
        label_collection_name (String): name of the label collection
        patent_collection_name (String): name of the patent collection
        processed_label_ids_file (Path): location to store processed ids
        processed_nda_file (Path): location to store processed NDAs
        alt_db_name (String): this is an optional argument that will set the
                    db_name to a value other than the value in the .env file.
    """

    setup_MongoDB(
        label_collection_name,
        patent_collection_name,
    )

    # open processed_label_id_file and return a list of processed _id string
    processed_label_ids = misc.get_lines_in_file(processed_label_ids_file)

    # get list of label_id strings excluding any string in processed_label_id
    all_label_ids = [
        x
        for x in [str(y) for y in _label_collection.distinct("_id", {})]
        if x not in processed_label_ids
    ]

    label_index = 0

    # loop through all_label_ids, popping off label_ids after diffing sections
    while len(all_label_ids) > 0:
        if label_index >= len(all_label_ids):
            # all labels were traversed, remaining labels have no
            # application_numbers; store unprocessed label_ids to disk
            misc.append_to_file(unprocessed_label_ids_file, all_label_ids)
            break

        # pick label_id
        label_id_str = str(all_label_ids[label_index])

        # get a list of NDA numbers (ex. ['NDA019501',]) associated with _id
        application_numbers = _label_collection.find_one(
            {"_id": ObjectId(label_id_str)},
            {"_id": 0, "application_numbers": 1},
        )["application_numbers"]

        if not application_numbers:
            # if label doesn't have application number skip for now
            label_index += 1
            continue

        # find all other docs with the same list of NDA numbers
        # len(similar_label_docs) is at least 1
        similar_label_docs = list(
            _label_collection.find({"application_numbers": application_numbers})
        )

        similar_label_docs = add_patent_map(
            similar_label_docs, application_numbers
        )
        patent_dict = patent_claims_longhand_form_from_NDA(application_numbers)
        # patent_list = [[patent_num, claim_num, parent_clm_list, claim_text],]
        patent_list = patent_dict_of_dict_to_list_of_list(patent_dict)
        # additions_list = [expanded_content, expanded_content...]
        additions_list = get_list_of_additions(similar_label_docs)

        if patent_list:
            similar_label_docs = rank_and_score(
                similar_label_docs, additions_list, patent_list
            )

            additions_in_diff_against_previous_label(similar_label_docs)

            update_db(_label_collection_name, similar_label_docs, alt_db_name)

            similar_label_docs_ids = [str(x["_id"]) for x in similar_label_docs]

            # remove similar_label_docs_ids from all_label_ids
            all_label_ids = [
                x for x in all_label_ids if x not in similar_label_docs_ids
            ]
            # store processed_label_ids & processed application_numbers to disk
            misc.append_to_file(
                processed_label_ids_file, similar_label_docs_ids
            )
            misc.append_to_file(
                processed_nda_file, str(application_numbers)[1:-1]
            )
        else:
            similar_label_docs_ids = [str(x["_id"]) for x in similar_label_docs]

            # remove similar_label_docs_ids from all_label_ids
            all_label_ids = [
                x for x in all_label_ids if x not in similar_label_docs_ids
            ]
            # store unprocessed label_ids & unprocessed application_numbers to
            # disk
            misc.append_to_file(
                unprocessed_label_ids_file, similar_label_docs_ids
            )
            misc.append_to_file(
                unprocessed_nda_file, str(application_numbers)[1:-1]
            )
