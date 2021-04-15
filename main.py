import argparse
import os

from similarity import run_nlp_scispacy

from utils.logging import getLogger
from utils import fetch

_logger = getLogger("main")

MODEL_FOLDER = "resources/models"
ORANGE_BOOK_FOLDER = "resources/Orange_Book"

def parse_args():
    parser = argparse.ArgumentParser(
        description="Process the arguments to the application."
    )

    parser.add_argument(
        '-ob',
        '--update_orange_book',
        action='store_true',
        help=(
            "Download the latest monthly update to the Orange Book from "
            "https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files "
            "into '{ORANGE_BOOK_FOLDER}'."
        ),
    )

    parser.add_argument(
        '-ob',
        '--update_orange_book',
        action='store_true',
        help=(
            "Download the latest monthly update to the Orange Book from "
            "https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files"
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":

    args = parse_args()
    _logger.info(f"Running with args: {args}")

    # download latest Orange Book File from fda.gov
    if args.update_orange_book:
        url = "https://www.fda.gov/media/76860/download"
        file_path = fetch.download(url, ORANGE_BOOK_FOLDER)
        fetch.extract_and_clean(file_path)

    # download scispaCy model
    url = "https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.4.0/en_core_sci_lg-0.4.0.tar.gz"
    if not os.path.exists(os.path.join(MODEL_FOLDER, "en_core_sci_lg-0.4.0")):
        file_path = fetch.download(url, MODEL_FOLDER)
        fetch.extract_and_clean(file_path)

    run_nlp_scispacy.process_similarity()

    # Fetch set_ids
    # all_set_ids = []
    # if args.set_ids_from_file:
    #     # Read set ids from the resource file
    #     all_set_ids = get_set_ids_from_file(args.set_ids_from_file)
    # elif args.start_page and args.num_pages:
    #     # Get SPL index data
    #     all_spls, end_page = process_paginated_index(
    #         start_page=args.start_page, num_pages=args.num_pages
    #     )
    #     # Get unique setids, for the subsequent steps
    #     all_set_ids = list(set(map(lambda x: x["setid"], all_spls)))
    #     # Write data obtained into a json file
    #     if args.write_index_data:
    #         with open(
    #             os.path.join(
    #                 TEMP_DATA_FOLDER,
    #                 f"spl_index_pages_{args.start_page}_to_{end_page}.json",
    #             ),
    #             "w+",
    #         ) as f:
    #             f.write(json.dumps(all_spls))

    # # Get SetID history, for all unique setids retrieved
    # all_setid_history = process_spl_history(all_set_ids)

    # # Write data obtained into a json file
    # if args.write_history_data:
    #     with open(
    #         os.path.join(
    #             TEMP_DATA_FOLDER,
    #             f"spl_history_pages.json",
    #         ),
    #         "w+",
    #     ) as f:
    #         f.write(json.dumps(all_setid_history))

    # # Get label text for each SPL version and write to MongoDB if any
    # # version contains an association with and NDA number.
    # process_historical_labels(
    #     all_setid_history, os.path.join(TEMP_DATA_FOLDER, "label_data")
    # )
