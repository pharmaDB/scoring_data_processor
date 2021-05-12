"""
This file creates a .csv copy of all data in the labels collection and uploads
"""
from bson.objectid import ObjectId
import os
from bson.binary import Binary
from datetime import date
import zipfile

from diff.run_diff import group_label_docs_by_set_id
from utils import misc
from utils.logging import getLogger

_logger = getLogger(__name__)


def compress_file(file_name):
    new_zip_file = os.path.abspath(file_name) + ".zip"
    _logger.info("Compressing %s" % file_name)
    zip_file = zipfile.ZipFile(new_zip_file, "w", zipfile.ZIP_DEFLATED)
    zip_file.write(file_name, os.path.basename(file_name))
    zip_file.close()


def delete_file(file_name):
    # Cleanup
    _logger.info("Deleting %s" % file_name)
    file_name = os.path.abspath(file_name)
    if os.path.exists(file_name):
        os.remove(file_name)


def upload_file_to_db(mongo_client, collection_name, file_name):
    collection = mongo_client.db[collection_name]

    with open(file_name, "rb") as f:
        encoded = Binary(f.read())

    today = date.today()
    # ex: Sep-16-2019
    date_str = today.strftime("%b-%d-%Y")

    collection.insert(
        {
            "filename": file_name,
            "file": encoded,
            "description": "Last Edit " + date_str,
        }
    )


def append_to_csv(file_name, nda_str, set_id_group):
    """
    Output all doc in set_id to a csv file.

    Parameters:
        file_name (Path): filename to store exported csv
        nda_str (String): ex "12345-23456"
        set_id_group (String): ex: "7b5489a1-e30f-450f-bd2b-00d05fd52915"
    """
    _logger.info(f"NDA: {nda_str}")
    multi_line = []
    for label in set_id_group:
        label["_id"] = str(label["_id"])
        if "diff_against_previous_label" not in label:
            _logger.error(
                f"Label: _id {label['_id']} missing"
                " 'diff_against_previous_label' key.  Please run main.py "
                "--diff before running this script."
            )
            return None
        if "additions" not in label:
            _logger.error(
                f"Label: _id {label['_id']} missing 'additions' key.  "
                "Please run main.py --diff before running this script."
            )
            return None
        # output: NDA,set-id,full_json,published_date
        output_string = (
            nda_str
            + ","
            + label["set_id"]
            + ","
            + (
                label["previous_label_published_date"]
                if label["previous_label_published_date"]
                else ""
            )
            + ","
            + label["published_date"]
        )
        _logger.info(
            f"\n\tset_id: {label['set_id']}\tspl_id: {label['spl_version']}\t"
            f"{label['published_date']}"
        )
        for diff in label["diff_against_previous_label"]:
            if diff["text"]:
                output_string_1 = (
                    output_string + ',"' + fix_text(diff["name"]) + '"'
                )
                for text in diff["text"]:
                    if len(text) > 3:
                        # add additions
                        output_string_2 = (
                            output_string_1 + ',"' + fix_text(text[1]) + '"'
                        )
                        # add expanded_content
                        output_string_3 = (
                            output_string_2
                            + ',"'
                            + fix_text(text[3]["expanded_content"])
                            + '"'
                        )
                        for score in text[3]["scores"]:
                            output_string_4 = (
                                output_string_3
                                + ","
                                + str(score["patent_number"])
                            )
                            output_string_4 = (
                                output_string_4
                                + ","
                                + str(score["claim_number"])
                            )
                            output_string_4 = (
                                output_string_4
                                + ","
                                + ";".join(
                                    [
                                        str(x)
                                        for x in score["parent_claim_numbers"]
                                    ]
                                )
                            )
                            output_string_4 = (
                                output_string_4 + "," + str(score["score"])
                            )
                            multi_line += [output_string_4]

    return multi_line


def fix_text(txt):
    """
    Fixes text so it is csv friendly
    """
    return " ".join(txt.replace('"', "'").split())


def loop_through_set_id(mongo_client, file_name):
    """
    This method will gather all label additions in the labels collection in
    MongoDB into a csv file, with one row per score.

    Parameters:
        mongo_client (object): MongoClient object with database and collections
        file_name (Path): filename to store exported csv
    """
    label_collection = mongo_client.label_collection

    # get list of label_id strings excluding any string in processed_label_id
    all_label_ids = [str(y) for y in label_collection.distinct("_id", {})]

    csv_heading = (
        "NDA,set_id,previous_published_date,published_date,section_name,"
        "addition,expanded_content,patent_number,claim_number,parent_claim,"
        "score"
    )

    final_csv = [csv_heading]
    delete_file(file_name)
    misc.append_to_file(file_name, final_csv)

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

        groups_by_set_id = group_label_docs_by_set_id(similar_label_docs)

        for set_id_group in groups_by_set_id:

            multi_line = append_to_csv(
                file_name,
                ";".join(application_numbers),
                set_id_group,
            )
            if multi_line:
                misc.append_to_file(file_name, multi_line)

        similar_label_docs_ids = [str(x["_id"]) for x in similar_label_docs]

        # remove similar_label_docs_ids from all_label_ids
        all_label_ids = [
            x for x in all_label_ids if x not in similar_label_docs_ids
        ]


def run_export_csv_zip(mongo_client, file_name):
    """
    This method runs all other methods in this module

    Parameters:
        mongo_client (object): MongoClient object with database and collections
        file_name (Path): filename to store exported csv
    """
    # delete csv_file
    delete_file(file_name)
    # delete zip file
    delete_file(os.path.abspath(file_name) + ".zip")
    loop_through_set_id(mongo_client, file_name)
    compress_file(file_name)
    # delete csv file
    delete_file(file_name)
