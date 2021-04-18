import argparse
import os
import json
from bson.objectid import ObjectId

# from similarity import run_nlp_scispacy
from diff import run_diff
from db.mongo import connect_mongo

from utils.logging import getLogger
from utils import fetch

_logger = getLogger("main")


RESOURCE_FOLDER = "resources"
MODEL_FOLDER = os.path.join(RESOURCE_FOLDER, "models")
ORANGE_BOOK_FOLDER = os.path.join(RESOURCE_FOLDER, "Orange_Book")
PROCESSED_LOGS = os.path.join(RESOURCE_FOLDER, "processed_log")
PROCESSED_ID_DIFF_FILE = os.path.join(PROCESSED_LOGS, "processed_id_diff.csv")
PROCESSED_NDA_DIFF_FILE = os.path.join(PROCESSED_LOGS, "processed_nda_diff.csv")
PROCESSED_ID_SIMILARITY_FILE = os.path.join(
    PROCESSED_LOGS, "processed_id_similarity.csv"
)
PROCESSED_NDA_SIMILARITY_FILE = os.path.join(
    PROCESSED_LOGS, "processed_NDA_similarity.csv"
)
LABEL_COLLECTION = "labels"
PATENT_COLLECTION = "patents"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Process the arguments to the application."
    )

    parser.add_argument(
        "-ob",
        "--update_orange_book",
        action="store_true",
        help=(
            "Download the latest monthly update to the Orange Book from "
            "https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files "
            "into '{ORANGE_BOOK_FOLDER}'."
        ),
    )

    parser.add_argument(
        "-r",
        "--rerun",
        action="store_true",
        help=(
            "Delete all process csv's of MongoDB ObjectId and NDAs from folder"
            " '{RESOURCE_FOLDER}', then rerun all diffs and similarity."
        ),
    )

    parser.add_argument(
        "-ril",
        "--reimport_labels",
        action="store_true",
        help=("Reimport labels collection from assets/database_before/"),
    )

    parser.add_argument(
        "-rip",
        "--reimport_patents",
        action="store_true",
        help=("Reimport labels collection from assets/database_before/"),
    )

    return parser.parse_args()


def reimport_collection(collection_name, file_name):
    db = connect_mongo()
    collection = db[collection_name]
    collection.drop()
    with open(file_name, "r") as f:
        lines = f.readlines()
        for line in lines:
            doc = json.loads(line)
            doc["_id"] = ObjectId(doc["_id"]["$oid"])
            collection.insert_one(doc)


if __name__ == "__main__":

    args = parse_args()
    _logger.info(f"Running with args: {args}")

    run_diff_and_similarity = False

    # download latest Orange Book File from fda.gov
    if args.update_orange_book:
        url = "https://www.fda.gov/media/76860/download"
        file_path = fetch.download(url, ORANGE_BOOK_FOLDER)
        fetch.extract_and_clean(file_path)
    else:
        run_diff_and_similarity = True

    if args.reimport_labels:
        reimport_collection(
            LABEL_COLLECTION, "assets/database_before/labels.json"
        )

    if args.reimport_patents:
        reimport_collection(
            PATENT_COLLECTION, "assets/database_before/patents.json"
        )

    # rerun all
    if args.rerun:
        if os.path.exists(PROCESSED_ID_DIFF_FILE):
            os.remove(PROCESSED_ID_DIFF_FILE)
        if os.path.exists(PROCESSED_NDA_DIFF_FILE):
            os.remove(PROCESSED_NDA_DIFF_FILE)
        if os.path.exists(PROCESSED_ID_SIMILARITY_FILE):
            os.remove(PROCESSED_ID_SIMILARITY_FILE)
        if os.path.exists(PROCESSED_NDA_SIMILARITY_FILE):
            os.remove(PROCESSED_NDA_SIMILARITY_FILE)
        run_diff_and_similarity = True

    if run_diff_and_similarity:
        # download scispaCy model
        url = "https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.4.0/en_core_sci_lg-0.4.0.tar.gz"
        if not os.path.exists(
            os.path.join(MODEL_FOLDER, "en_core_sci_lg-0.4.0")
        ):
            file_path = fetch.download(url, MODEL_FOLDER)
            # fetch.extract_and_clean(file_path)

        run_diff.run_diff(
            LABEL_COLLECTION, PROCESSED_ID_DIFF_FILE, PROCESSED_NDA_DIFF_FILE
        )

        # run_nlp_scispacy.process_similarity(LABEL_COLLECTION, PATENT_COLLECTION, PROCESSED_ID_SIMILARITY_FILE, PROCESSED_NDA_SIMILARITY_FILE)
