import argparse
from dotenv import dotenv_values
import os
from pathlib import Path
import sys

from diff import run_diff
from db.mongo import MongoClient
from utils.logging import getLogger
from utils import fetch
from export import (
    get_files_from_db,
    export_lists,
    export_label_collection_as_csv_zip,
)

_logger = getLogger("main")

_config = dict(
    dotenv_values(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), ".", ".env")
    )
)

# resource folders (contains data files read and written by this package)
RESOURCE_FOLDER = "resources"
ORANGE_BOOK_FOLDER = os.path.join(RESOURCE_FOLDER, "Orange_Book")
PROCESSED_LOGS = os.path.join(RESOURCE_FOLDER, "processed_log")

# csv log files (used by package internally to track completed database tasks)
# for diff module
PROCESSED_ID_DIFF_FILE = os.path.join(PROCESSED_LOGS, "diff_processed_id.csv")
PROCESSED_NDA_DIFF_FILE = os.path.join(PROCESSED_LOGS, "diff_processed_nda.csv")
UNPROCESSED_ID_DIFF_FILE = os.path.join(
    PROCESSED_LOGS, "diff_unprocessed_id.csv"
)

# for similarity module
PROCESSED_ID_SIMILARITY_FILE = os.path.join(
    PROCESSED_LOGS, "similarity_processed_id.csv"
)
PROCESSED_NDA_SIMILARITY_FILE = os.path.join(
    PROCESSED_LOGS, "similarity_processed_NDA.csv"
)
UNPROCESSED_ID_SIMILARITY_FILE = os.path.join(
    PROCESSED_LOGS, "similarity_unprocessed_id.csv"
)
UNPROCESSED_NDA_SIMILARITY_FILE = os.path.join(
    PROCESSED_LOGS, "similarity_unprocessed_NDA.csv"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Running this package without any optional argument will calculate and store diffs between adjacent labels (by date) for each drug as defined by NDA number(s) into the label collection of the MongoDB database.  The name of the MongoDB database is set in the .env file.  The diffs will also be collated to patent claims from the patents collection of the MongoDB database.  "
        f"Labels that are already processed are stored in {PROCESSED_ID_DIFF_FILE} and {PROCESSED_ID_SIMILARITY_FILE}.  These labels will not be re-processed unless optional argument '-r' is set. "
        "Running optional arguments other than '-r' will not additionally run the diffing steps or diffs-to-patent-claims mapping unless those flags are set."
    )

    parser.add_argument(
        "-an",
        "--all_NDA_from_Orange_Book",
        nargs="?",
        type=Path,
        const=Path(__file__).absolute().parent
        / "assets"
        / "db_state"
        / "all_NDA",
        help=(
            "Output list of all NDA from Orange Book to File_Name. If unset"
            ", File_Name is '/assets/db_state/all_NDA'."
        ),
        metavar=("File_Name"),
    )

    parser.add_argument(
        "-ap",
        "--all_patents_from_Orange_Book",
        nargs="?",
        type=Path,
        const=Path(__file__).absolute().parent
        / "assets"
        / "db_state"
        / "all_patents",
        help=(
            "Output list of patents from Orange Book to File_Name. If unset, "
            "File_Name is '/assets/db_state/all_patents'."
        ),
        metavar=("File_Name"),
    )

    parser.add_argument(
        "-apj",
        "--all_patents_from_Orange_Book_json",
        nargs="?",
        type=Path,
        const=Path(__file__).absolute().parent
        / "assets"
        / "db_state"
        / "all_patents.json",
        help=(
            "Output list of patents from Orange Book to File_Name. If unset, "
            "File_Name is '/assets/db_state/all_patents.json'."
        ),
        metavar=("File_Name"),
    )

    parser.add_argument(
        "-mn",
        "--missing_NDA_from_database",
        nargs="?",
        type=Path,
        const=Path(__file__).absolute().parent
        / "assets"
        / "db_state"
        / "missing_NDA",
        help=(
            "Output list of NDA from Orange Book not in MongoDB to "
            "File_Name. If unset, File_Name is '/assets/db_state/missing_NDA'."
        ),
        metavar=("File_Name"),
    )

    parser.add_argument(
        "-mp",
        "--missing_patents_from_database",
        nargs="?",
        type=Path,
        const=Path(__file__).absolute().parent
        / "assets"
        / "db_state"
        / "missing_patents",
        help=(
            "Output list of patents from Orange Book not in MongoDB to "
            "File_Name. If unset, File_Name is '/assets/db_state/missing_patents'."
        ),
        metavar=("File_Name"),
    )

    parser.add_argument(
        "-mpj",
        "--missing_patents_from_database_json",
        nargs="?",
        type=Path,
        const=Path(__file__).absolute().parent
        / "assets"
        / "db_state"
        / "missing_patents.json",
        help=(
            "Output list of patents from Orange Book not in MongoDB to "
            "File_Name. If unset, File_Name is '/assets/db_state/missing_patents.json'."
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
        nargs="?",
        type=Path,
        const=Path(__file__).absolute().parent
        / "assets"
        / "database_latest"
        / "labels.json",
        help=(
            "Reimport label collection from json file. (for development).  "
            "If unset, File_Name is '/assets/database_latest/labels.json'."
        ),
        metavar=("File_Name"),
    )

    parser.add_argument(
        "-rio",
        "--reimport_orange_book",
        nargs="?",
        type=Path,
        const=Path(__file__).absolute().parent
        / "assets"
        / "database_latest"
        / "orangebook.json",
        help=(
            "Reimport orange_book collection from json file. (for development)."
            "If unset, File_Name is '/assets/database_latest/orangebook.json'."
        ),
        metavar=("File_Name"),
    )

    parser.add_argument(
        "-rip",
        "--reimport_patents",
        nargs="?",
        type=Path,
        const=Path(__file__).absolute().parent
        / "assets"
        / "database_latest"
        / "patents.json",
        help=(
            "Reimport patent collection from json file. (for development).  "
            "If unset, File_Name is '/assets/database_latest/patents.json'."
        ),
        metavar=("File_Name"),
    )

    parser.add_argument(
        "-diff",
        "--diff",
        action="store_true",
        help=("Run diffing_algo."),
    )

    parser.add_argument(
        "-bert",
        "--bert",
        action="store_true",
        help=("Run similarity with Bert."),
    )

    parser.add_argument(
        "-db2file",
        "--db2file",
        nargs="?",
        type=Path,
        const=Path(__file__).absolute().parent / "analysis" / "db2file",
        help=(
            "Output list of additions and patent claim sets from the database "
            "to Folder_Name. If unset, Folder_Name is '/analysis/db2file/'."
        ),
        metavar=("Folder_Name"),
    )

    parser.add_argument(
        "-db2csv",
        "--db2csv",
        nargs="?",
        type=Path,
        const=Path(__file__).absolute().parent
        / "assets"
        / "hosted_folder"
        / "db2csv.csv",
        help=(
            "Output the entire database to a csv file File_Name. If unset"
            ", File_Name is '/assets/hosted_folder/db2csv.csv'."
        ),
        metavar=("File_Name"),
    )

    return parser.parse_args()


if __name__ == "__main__":

    args = parse_args()
    _logger.info(f"Running with args: {args}")

    run_diff_and_similarity = False

    # download latest Orange Book File from fda.gov
    if args.update_orange_book:
        url = "https://www.fda.gov/media/76860/download"
        file_path = fetch.download(url, ORANGE_BOOK_FOLDER)
        fetch.extract_and_clean(file_path)

    # export all patents or NDA from the Orange Book
    if args.all_NDA_from_Orange_Book:
        export_lists.export_all_NDA(args.all_NDA_from_Orange_Book)
    if args.all_patents_from_Orange_Book:
        export_lists.export_all_patents(args.all_patents_from_Orange_Book)
    if args.all_patents_from_Orange_Book_json:
        export_lists.export_all_patents(
            args.all_patents_from_Orange_Book_json, True
        )

    label_collection_name = _config["MONGODB_LABEL_COLLECTION_NAME"]
    patent_collection_name = _config["MONGODB_PATENT_COLLECTION_NAME"]
    orange_book_collection_name = _config["MONGODB_ORANGE_BOOK_COLLECTION_NAME"]
    mongo_client = MongoClient(
        label_collection_name,
        patent_collection_name,
        orange_book_collection_name,
    )

    # reimport of label or patent collections; for development
    if args.reimport_labels:
        mongo_client.reimport_collection(
            label_collection_name, args.reimport_labels
        )
    if args.reimport_patents:
        mongo_client.reimport_collection(
            patent_collection_name, args.reimport_patents
        )
    if args.reimport_orange_book:
        mongo_client.reimport_collection(
            orange_book_collection_name, args.reimport_orange_book
        )

    # export list of missing patents or NDA from the database
    if args.missing_NDA_from_database:
        export_lists.export_missing_NDA(
            mongo_client, args.missing_NDA_from_database
        )
    if args.missing_patents_from_database:
        export_lists.export_missing_patents(
            mongo_client, args.missing_patents_from_database
        )
    if args.missing_patents_from_database_json:
        export_lists.export_missing_patents(
            mongo_client, args.missing_patents_from_database_json, True
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
        if os.path.exists(UNPROCESSED_ID_DIFF_FILE):
            os.remove(UNPROCESSED_ID_DIFF_FILE)
        if os.path.exists(UNPROCESSED_ID_SIMILARITY_FILE):
            os.remove(UNPROCESSED_ID_SIMILARITY_FILE)
        if os.path.exists(UNPROCESSED_NDA_SIMILARITY_FILE):
            os.remove(UNPROCESSED_NDA_SIMILARITY_FILE)
        run_diff_and_similarity = True

    if len(sys.argv) == 1 or args.bert:
        # for case when no optional arguments are passed
        run_diff_and_similarity = True

    # if run_diff_and_similarity:
    if run_diff_and_similarity or args.db2csv:
        run_diff.run_diff(
            mongo_client,
            PROCESSED_ID_DIFF_FILE,
            PROCESSED_NDA_DIFF_FILE,
            UNPROCESSED_ID_DIFF_FILE,
        )

        # do not run diff again
        args.diff = False

        from similarity import run_similarity_bert

        run_similarity_bert.run_similarity(
            mongo_client,
            PROCESSED_ID_SIMILARITY_FILE,
            PROCESSED_NDA_SIMILARITY_FILE,
            UNPROCESSED_ID_SIMILARITY_FILE,
            UNPROCESSED_NDA_SIMILARITY_FILE,
        )

    elif args.diff or args.db2file:
        run_diff.run_diff(
            mongo_client,
            PROCESSED_ID_DIFF_FILE,
            PROCESSED_NDA_DIFF_FILE,
            UNPROCESSED_ID_DIFF_FILE,
        )

    if args.db2file:
        get_files_from_db.get_files_from_db(mongo_client, args.db2file)

    if args.db2csv:
        export_label_collection_as_csv_zip.run_export_csv_zip(
            mongo_client, args.db2csv
        )
