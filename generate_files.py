"""
This file is the generation of a db2file for data analysis purposes.
Run after 'python main.py -rip -ril -diff'
"""

from bson.objectid import ObjectId
from itertools import groupby
import os
import simplejson
import html

from db.mongo import connect_mongo
from orangebook.merge import OrangeBookMap
from utils import misc

# Store name string and MongoDB collection object
_label_collection_name = None
_label_collection = None
_patent_collection_name = None
_patent_collection = None

# initialize OrangeBookMap
_ob = OrangeBookMap()


def group_label_docs_by_set_id(docs):
    """
    This function groups the docs by 'set_id" and returns a list of list,
    wherein the inner list share the same set_id.

    Return example:
        [[{set_id:X,},{set_id:X,}],[{set_id:Y,},{set_id:Y,}],]

    Parameters:
        docs (list): list of label docs from MongoDB having the same
                     application_numbers
    """

    def key_func(k):
        return k["set_id"]

    docs = sorted(
        docs,
        key=key_func,
        reverse=False,
    )
    return_list = [list(value) for key, value in groupby(docs, key=key_func)]
    return return_list


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


def output_file(nda_str, set_id_group, all_patent):
    print(f"NDA: {nda_str}")
    for label in set_id_group:
        label["_id"] = str(label["_id"])
        for diff in label["diff_against_previous_label"]:
            for text in diff["text"]:
                text = text[:3]
        for key in label["additions"].keys():
            label["additions"][key].pop("scores", None)

        # output NDA/set-id/full_json
        file_name = (
            "db2file/"
            + nda_str
            + "/"
            + label["set_id"]
            + "/full_json/"
            + label["published_date"]
            + ".json"
        )

        print(file_name)

        if not os.path.exists(os.path.dirname(file_name)):
            os.makedirs(os.path.dirname(file_name))

        with open(file_name, "w") as f:
            f.write(simplejson.dumps(label, indent=4, sort_keys=False))

        # output NDA/set-id/addition_with_context
        file_name = (
            "db2file/"
            + nda_str
            + "/"
            + label["set_id"]
            + "/additions_with_context/"
            + label["published_date"]
        )

        print(file_name)

        if not os.path.exists(os.path.dirname(file_name)):
            os.makedirs(os.path.dirname(file_name))

        additions = []
        for key, value in label["additions"].items():
            additions.append(str(value["expanded_content"]))

        with open(file_name, "wb") as f:
            for addition in additions:
                f.write(addition.encode("unicode_escape"))
                f.write(b"\n")

        # output NDA/set-id/just_addition
        additions = []
        for diff in label["diff_against_previous_label"]:
            for text in diff["text"]:
                if text[0] == 1 and len(text) > 2:
                    additions.append(str(text[1]))

        file_name = (
            "db2file/"
            + nda_str
            + "/"
            + label["set_id"]
            + "/just_additions/"
            + label["published_date"]
        )

        print(file_name)

        if not os.path.exists(os.path.dirname(file_name)):
            os.makedirs(os.path.dirname(file_name))

        with open(file_name, "wb") as f:
            for addition in additions:
                f.write(addition.encode("unicode_escape"))
                f.write(b"\n")

    # output NDA/patent

    all_patent_list = []
    for i in all_patent:
        all_patent_list += i["patents"]

    all_patent_list = list(set(all_patent_list))

    for patent_num in all_patent_list:
        patent_from_collection = _patent_collection.find_one(
            {"patent_number": str(patent_num)},
            {"patent_number": 1, "claims": 1},
        )
        if not patent_from_collection:
            continue

        file_name = (
            "db2file/"
            + nda_str
            + "/patents/"
            + patent_from_collection["patent_number"]
        )

        print(file_name)

        if not os.path.exists(os.path.dirname(file_name)):
            os.makedirs(os.path.dirname(file_name))

        with open(file_name, "wb") as f:
            for claim in patent_from_collection["claims"]:
                if (
                    claim["claim_text"].lstrip("0123456789. ")
                    != claim["claim_text"]
                ):
                    f.write(
                        html.unescape(claim["claim_text"]).encode(
                            "unicode_escape"
                        )
                    )
                else:
                    f.write(
                        html.unescape(
                            claim["claim_number"] + ". " + claim["claim_text"]
                        ).encode("unicode_escape")
                    )
                f.write(b"\n")


def get_files_from_db():
    setup_MongoDB(
        "labels",
        "patents",
    )
    # get list of label_id strings excluding any string in processed_label_id
    all_label_ids = [str(y) for y in _label_collection.distinct("_id", {})]

    label_index = 0

    while len(all_label_ids) > 0:
        if label_index >= len(all_label_ids):
            # all labels were traversed, remaining labels have no
            # application_numbers; store unprocessed label_ids to disk
            misc.append_to_file("log_db2file/unprocessed_ids", all_label_ids)
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

        groups_by_set_id = group_label_docs_by_set_id(similar_label_docs)

        for set_id_group in groups_by_set_id:
            # # sort by published_date
            # set_id_group = sorted(
            #     set_id_group,
            #     key=lambda i: (i["published_date"]),
            #     reverse=False,
            # )
            all_patents = [
                {
                    "application_number": str(nda),
                    "patents": _ob.get_patents(misc.get_num_in_str(nda)),
                }
                for nda in application_numbers
            ]
            output_file(
                "-".join(application_numbers), set_id_group, all_patents
            )
            # set_id_group = add_previous_and_next_labels(set_id_group)
            # set_id_group = add_diff_against_previous_label(set_id_group)
            # set_id_group = gather_additions(set_id_group)

        # # ungroup similar_label_docs by set id
        # similar_label_docs = [
        #     item for sublist in groups_by_set_id for item in sublist
        # ]

        similar_label_docs_ids = [str(x["_id"]) for x in similar_label_docs]

        # remove similar_label_docs_ids from all_label_ids
        all_label_ids = [
            x for x in all_label_ids if x not in similar_label_docs_ids
        ]


if __name__ == "__main__":
    get_files_from_db()
