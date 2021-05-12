"""
This file is for the generation of a db2file for data analysis purposes.
Run after 'python main.py -rip -ril -diff'
"""

from bson.objectid import ObjectId
import os
import simplejson
import html
from collections import OrderedDict
from pathlib import Path

from similarity.claim_dependency import dependent_to_independent_claim
from orangebook.merge import OrangeBookMap
from diff.run_diff import group_label_docs_by_set_id, add_patent_map
from utils import misc
from utils.logging import getLogger


_logger = getLogger(__name__)


def output_label_file(db2file_folder, nda_str, set_id_group):
    """
    Outputs all label additions.
    """
    print(f"NDA: {nda_str}")
    for label in set_id_group:
        label["_id"] = str(label["_id"])
        if "diff_against_previous_label" not in label:
            _logger.error(
                f"Label: _id {label['_id']} missing"
                " 'diff_against_previous_label' key.  Please run main.py "
                "--diff before running this script."
            )
            return False
        for diff in label["diff_against_previous_label"]:
            for text in diff["text"]:
                text = text[:3]
        if "additions" not in label:
            _logger.error(
                f"Label: _id {label['_id']} missing 'additions' key.  "
                "Please run main.py --diff before running this script."
            )
            return False
        for key in label["additions"].keys():
            label["additions"][key].pop("scores", None)

        # output NDA/set-id/full_json
        file_name = Path.joinpath(
            db2file_folder,
            nda_str,
            label["set_id"],
            "full_json",
            label["published_date"] + ".json",
        )

        print(file_name)

        if not os.path.exists(os.path.dirname(file_name)):
            os.makedirs(os.path.dirname(file_name))

        with open(file_name, "w") as f:
            f.write(simplejson.dumps(label, indent=4, sort_keys=False))

        # output NDA/set-id/addition_with_context
        file_name = Path.joinpath(
            db2file_folder,
            nda_str,
            label["set_id"],
            "additions_with_context",
            label["published_date"],
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

        file_name = Path.joinpath(
            db2file_folder,
            nda_str,
            label["set_id"],
            "just_additions",
            label["published_date"],
        )

        print(file_name)

        if not os.path.exists(os.path.dirname(file_name)):
            os.makedirs(os.path.dirname(file_name))

        with open(file_name, "wb") as f:
            for addition in additions:
                f.write(addition.encode("unicode_escape"))
                f.write(b"\n")


def output_patent_file(mongo_client, db2file_folder, nda_str, all_patent):
    """
    Outputs all patent files to db2file_folder

    Parameters:
        mongo_client (object): MongoClient object with database and collections
        db2file_folder (Path): folder to store exported files
        nda_str (String): NDA group folder in which to output files
        all_patent (list): All patents related to nda_str
    """
    # output NDA/patent

    all_patent_list = []
    for i in all_patent:
        all_patent_list += i["patents"]

    all_patent_list = list(set(all_patent_list))

    for patent_num in all_patent_list:
        patent_from_collection = mongo_client.patent_collection.find_one(
            {"patent_number": str(patent_num)},
            {"patent_number": 1, "claims": 1},
        )
        if not patent_from_collection:
            continue

        file_name = Path.joinpath(
            db2file_folder,
            nda_str,
            "patents",
            patent_from_collection["patent_number"],
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
                        html.unescape(claim["claim_text"])
                        .replace("\r", "")
                        .encode("unicode_escape")
                    )
                else:
                    f.write(
                        html.unescape(
                            claim["claim_number"] + ". " + claim["claim_text"]
                        )
                        .replace("\r", "")
                        .encode("unicode_escape")
                    )
                f.write(b"\n")

        # output NDA/patent_longhand
        claim_num_text_od = OrderedDict()
        claims = patent_from_collection["claims"]
        sorted(claims, key=lambda i: i["claim_number"])
        for claim in claims:
            claim_num_text_od[int(claim["claim_number"])] = html.unescape(
                claim["claim_text"]
            )
        claims_longhand = dependent_to_independent_claim(
            claim_num_text_od, str(patent_num)
        )

        file_name = Path.joinpath(
            db2file_folder,
            nda_str,
            "patents_longhand",
            patent_from_collection["patent_number"],
        )

        print(file_name)

        if not os.path.exists(os.path.dirname(file_name)):
            os.makedirs(os.path.dirname(file_name))

        with open(file_name, "wb") as f:
            for claim_num, value in claims_longhand.items():
                for interp in value:
                    f.write(
                        (str(claim_num) + ". " + interp["text"])
                        .replace("\r", "")
                        .encode("unicode_escape")
                    )
                    f.write(b"\n")


def get_files_from_db(mongo_client, db2file_folder):

    """
    This method calls other methods in this module to pull data from database
    to db2file_folder.

    Parameters:
        mongo_client (object): MongoClient object with database and collections
        db2file_folder (Path): folder to store exported files
    """
    label_collection = mongo_client.label_collection

    # get list of label_id strings excluding any string in processed_label_id
    all_label_ids = [str(y) for y in label_collection.distinct("_id", {})]

    label_index = 0
    while len(all_label_ids) > 0:
        if label_index >= len(all_label_ids):
            # all labels were traversed, remaining labels have no
            # application_numbers
            break

        # pick label_id
        label_id_str = str(all_label_ids[label_index])

        # get a list of NDA numbers (ex. ['NDA019501',]) associated with _id
        application_numbers = label_collection.find_one(
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
            label_collection.find(
                {"application_numbers": {"$all": application_numbers}}
            )
        )
        # similar_label_docs = add_patent_map(
        #     mongo_client, similar_label_docs, application_numbers
        # )

        groups_by_set_id = group_label_docs_by_set_id(similar_label_docs)

        # initialize OrangeBookMap
        ob = OrangeBookMap(mongo_client)

        for set_id_group in groups_by_set_id:

            output_label_file(
                db2file_folder,
                "-".join(application_numbers),
                set_id_group,
            )
            all_patents = [
                {
                    "application_number": str(nda),
                    "patents": ob.get_patents(misc.get_num_in_str(nda)),
                }
                for nda in application_numbers
            ]
            output_patent_file(
                mongo_client,
                db2file_folder,
                "-".join(application_numbers),
                all_patents,
            )

        similar_label_docs_ids = [str(x["_id"]) for x in similar_label_docs]

        # remove similar_label_docs_ids from all_label_ids
        all_label_ids = [
            x for x in all_label_ids if x not in similar_label_docs_ids
        ]
