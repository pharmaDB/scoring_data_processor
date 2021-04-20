import argparse
import os
import json
from bson.objectid import ObjectId
from pathlib import Path
import sys

# from similarity import run_nlp_scispacy
from diff import run_diff
from db.mongo import connect_mongo

from orangebook.merge import OrangeBookMap
from utils.logging import getLogger
from utils import fetch
from utils import misc

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
        description="Running this package without any optional argument will calculated and store diffs between adjacent labels (by date) for each drug as defined by NDA number(s) into the label collection of the MongoDB database.  The name of the MongoDB database is set in the .env file.  The diffs will also be collated to patent claims from the patents collection of the MongoDB database.  "
        f"Labels that are already processed are stored in {PROCESSED_ID_DIFF_FILE} and {PROCESSED_ID_SIMILARITY_FILE}.  These labels will not be re-processed unless optional argument '-r' is set. "
        "Running optional arguments other than '-r' will not additionally run the diffing steps or diffs-to-patent-claims mapping."
    )

    parser.add_argument(
        "-al",
        "--all_labels_from_Orange_Book",
        nargs="?",
        type=Path,
        const=Path(__file__).absolute().parent / "assets" / "all_labels",
        help=(
            "Output list of all labels from Orange Book to File_Name. If unset"
            ", File_Name is '/assets/all_labels'."
        ),
        metavar=("File_Name"),
    )

    parser.add_argument(
        "-ap",
        "--all_patents_from_Orange_Book",
        nargs="?",
        type=Path,
        const=Path(__file__).absolute().parent / "assets" / "all_patents",
        help=(
            "Output list of patents from Orange Book to File_Name. If unset, "
            "File_Name is '/assets/all_patents'."
        ),
        metavar=("File_Name"),
    )

    parser.add_argument(
        "-ml",
        "--missing_labels_from_database",
        nargs="?",
        type=Path,
        const=Path(__file__).absolute().parent / "assets" / "missing_labels",
        help=(
            "Output list of labels from Orange Book not in MongoDB to "
            "File_Name. If unset, File_Name is '/assets/missing_labels'."
        ),
        metavar=("File_Name"),
    )

    parser.add_argument(
        "-mp",
        "--missing_patents_from_database",
        nargs="?",
        type=Path,
        const=Path(__file__).absolute().parent / "assets" / "missing_patents",
        help=(
            "Output list of patents from Orange Book not in MongoDB to "
            "File_Name. If unset, File_Name is '/assets/missing_patents'."
        ),
        metavar=("File_Name"),
    )

    parser.add_argument(
        "-ob",
        "--update_orange_book",
        action="store_true",
        help=(
            "Download the latest monthly update to the Orange Book from "
            "https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files "
            f"into '{ORANGE_BOOK_FOLDER}'."
        ),
    )

    parser.add_argument(
        "-r",
        "--rerun",
        action="store_true",
        help=(
            "Delete all process csv's of MongoDB ObjectId and NDAs from folder"
            f" '{PROCESSED_LOGS}', then rerun all diffs and similarity."
        ),
    )

    parser.add_argument(
        "-ril",
        "--reimport_labels",
        action="store_true",
        help=(
            "Reimport label collection from assets/database_before/ "
            "(for development)"
        ),
    )

    parser.add_argument(
        "-rip",
        "--reimport_patents",
        action="store_true",
        help=(
            "Reimport patent collection from assets/database_before/ "
            "(for development"
        ),
    )

    return parser.parse_args()


def reimport_collection(collection_name, file_name):
    """Reimports collection into MongoDB"""
    db = connect_mongo()
    collection = db[collection_name]
    collection.drop()
    with open(file_name, "r") as f:
        lines = f.readlines()
        for line in lines:
            doc = json.loads(line)
            doc["_id"] = ObjectId(doc["_id"]["$oid"])
            collection.insert_one(doc)


def export_all_labels(file_name):
    """Exports list of all labels from the Orange Book to a file"""
    ob = OrangeBookMap()
    all_labels_in_Orange_Book = ob.get_all_nda()
    misc.store_to_file(file_name, all_labels_in_Orange_Book)


def export_all_patents(file_name):
    """Exports list of all patents from the Orange Book to a file"""
    ob = OrangeBookMap()
    all_patents_in_Orange_Book = ob.get_all_patents()
    misc.store_to_file(file_name, all_patents_in_Orange_Book)


def export_missing_labels(file_name):
    """Exports list of missing labels from the database to a file"""
    db = connect_mongo()
    label_collection = db[LABEL_COLLECTION]
    ob = OrangeBookMap()
    all_labels_in_Orange_Book = ob.get_all_nda()
    all_labels_in_MongoDB = label_collection.distinct("application_numbers")
    labels_in_OB_not_in_Mongo = [
        x for x in all_labels_in_Orange_Book if x not in all_labels_in_MongoDB
    ]
    misc.store_to_file(file_name, labels_in_OB_not_in_Mongo)


def export_missing_patents(file_name):
    """Exports list of missing patents from the database to a file"""
    db = connect_mongo()
    patent_collection = db[PATENT_COLLECTION]
    ob = OrangeBookMap()
    all_patents_in_Orange_Book = ob.get_all_patents()
    all_patents_in_MongoDB = patent_collection.distinct("patent_no")
    patents_in_OB_not_in_Mongo = [
        x for x in all_patents_in_Orange_Book if x not in all_patents_in_MongoDB
    ]
    misc.store_to_file(file_name, patents_in_OB_not_in_Mongo)


if __name__ == "__main__":

    args = parse_args()
    _logger.info(f"Running with args: {args}")

    run_diff_and_similarity = False

    # export all patents or labels from the Orange Book
    if args.all_labels_from_Orange_Book:
        export_all_labels(args.all_labels_from_Orange_Book)
    if args.all_patents_from_Orange_Book:
        export_all_patents(args.all_patents_from_Orange_Book)

    # export list of missing patents or labels from the database
    if args.missing_labels_from_database:
        export_missing_labels(args.missing_labels_from_database)
    if args.missing_patents_from_database:
        export_missing_patents(args.missing_patents_from_database)

    # download latest Orange Book File from fda.gov
    if args.update_orange_book:
        url = "https://www.fda.gov/media/76860/download"
        file_path = fetch.download(url, ORANGE_BOOK_FOLDER)
        fetch.extract_and_clean(file_path)

    # reimport of label or patent collections; for development
    if args.reimport_labels:
        reimport_collection(
            LABEL_COLLECTION, "assets/database_before/labels.json"
        )
    if args.reimport_patents:
        reimport_collection(
            PATENT_COLLECTION, "assets/database_before/patents.json"
        )

    # rerun all diff and similarity
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

    if len(sys.argv) == 1:
        # for case when no optional arguments are passed
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
