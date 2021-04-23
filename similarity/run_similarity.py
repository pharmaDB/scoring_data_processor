from collections import OrderedDict
from bson.objectid import ObjectId

from orangebook.merge import OrangeBookMap
from similarity.no_dependent_claim import dependent_to_independent_claim
from db.mongo import connect_mongo, update_db

from utils import misc
from utils.logging import getLogger

_logger = getLogger(__name__)

# Store name string and MongoDB collection object for Label collection
_label_collection_name = None
_label_collection = None
_patent_collection_name = None
_patent_collection = None

# initialize OrangeBookMap
_ob = OrangeBookMap()


def get_claims_in_patents_db(all_patents):
    """
    Returns an OrderedDict of {patent_str:{claim_num:claim_text,},} from
    mongodb

    Parameters:
        all_patents (list): example: ['4139619', '4596812']
    """
    # patent_od is returned and has form {patent_str:{claim_num:claim_text,},}
    patent_od = OrderedDict()
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
                "{patent_collection_name}."
            )
        elif "claims" not in patent_from_collection.keys():
            _logger.error(f"Patent: {str(patent)} missing 'claims' key.")
        else:
            # claims is in form [{'claim_number': 1, 'claim_text': '...'},]
            claims = patent_from_collection["claims"]
            sorted(claims, key=lambda i: i["claim_number"])
            for claim in claims:
                claim_num_text_od[int(claim["claim_number"])] = claim[
                    "claim_text"
                ]
        patent_od[patent] = claim_num_text_od
    return patent_od


def patent_claims_longhand_form_from_NDA(application_numbers):
    """
    Return OrderedDict of {patent_str:{claim_num (int):[{'parent_clm':
    [independent_claim, ..., grand-parent_claim , parent_claim,],'text':
    claim_text},],},} wherein the value assigned to claim_num contains all
    intepretation of that claim when written in long hand form, without any
    dependencies

    Parameters:
        application_numbers (list): a list of application numbers such as
                                    ['NDA204223',]
    """

    def patent_claims_to_longhand(od):
        """
        Return OrderedDict of {patent_str:{claim_num (int):[{'parent_clm':
        [independent_claim, ..., grand-parent_claim , parent_claim,],'text':
        claim_text},],},}

        Parameters:
            od (OrderedDict): {patent_str:{claim_num:claim_text,},}
        """
        return_od = OrderedDict()
        for patent, claim_od in od.items():
            print(patent)
            # print(str(claim_od)[:500])
            return_od[patent] = dependent_to_independent_claim(claim_od)
        return return_od

    # all_patents = [[patent_str,],]
    all_patents = [
        _ob.get_patents(misc.get_num_in_str(nda)) for nda in application_numbers
    ]
    # print(all_patents)
    # flatten all_patents into [patent_str,]
    all_patents = [j for i in all_patents for j in i]
    # patent_od = OrderedDict of {patent_str:{claim_num:claim_text,},}
    patent_od = get_claims_in_patents_db(all_patents)
    # print(str(patent_od)[:500])
    print("test***")
    # claims_longhand_od = {patent_str:{claim_num (int):[{'parent_clm':
    #           [independent_claim, ..., grand-parent_claim ,
    #           parent_claim,],'text': claim_text},],},}
    claims_longhand_od = patent_claims_to_longhand(patent_od)
    return claims_longhand_od


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


def run_similarity(
    label_collection_name,
    patent_collection_name,
    processed_label_ids_file,
    processed_nda_file,
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
    # loop through all_label_ids, popping off label_ids after diffing sections
    while len(all_label_ids) > 0:

        # pick 1st label_id
        label_id_str = str(all_label_ids[0])

        # get a list of NDA numbers (ex. ['NDA019501',]) associated with _id
        application_numbers = _label_collection.find_one(
            {"_id": ObjectId(label_id_str)},
            {"_id": 0, "application_numbers": 1},
        )["application_numbers"]

        # find all other docs with the same list of NDA numbers
        # len(similar_label_docs) is at least 1
        similar_label_docs = list(
            _label_collection.find({"application_numbers": application_numbers})
        )
        similar_label_docs = sorted(
            similar_label_docs,
            key=lambda i: (i["published_date"]),
            reverse=False,
        )

        patent_od = patent_claims_longhand_form_from_NDA(application_numbers)

        # similar_label_docs = add_previous_and_next_labels(
        #     similar_label_docs
        # )
        # similar_label_docs = remove_newlines(similar_label_docs)
        # similar_label_docs = add_diff_against_previous_label(
        #     similar_label_docs
        # )
        # similar_label_docs = gather_additions(similar_label_docs)

        update_db(_label_collection_name, similar_label_docs, alt_db_name)

        similar_label_docs_ids = [str(x["_id"]) for x in similar_label_docs]

        # remove similar_label_docs_ids from all_label_ids
        all_label_ids = [
            x for x in all_label_ids if x not in similar_label_docs_ids
        ]
        # store processed_label_ids & processed application_numbers to disk
        misc.append_to_file(processed_label_ids_file, similar_label_docs_ids)
        misc.append_to_file(processed_nda_file, str(application_numbers)[1:-1])
