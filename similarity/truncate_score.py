from utils.logging import getLogger

_logger = getLogger(__name__)


def round_score(doc, digits=9):
    """
    truncate the score to 9 digits

    Parameters:
        doc (MongoDB document)
    """
    for addition_key, addition_value in doc["additions"].items():
        for score_num in range(len(doc["additions"][addition_key]["scores"])):
            if (
                "score"
                in doc["additions"][addition_key]["scores"][score_num].keys()
            ):
                doc["additions"][addition_key]["scores"][score_num][
                    "score"
                ] = round(
                    doc["additions"][addition_key]["scores"][score_num][
                        "score"
                    ],
                    digits,
                )

    for diff_num in range(len(doc["diff_against_previous_label"])):
        for text_num in range(
            len(doc["diff_against_previous_label"][diff_num]["text"])
        ):
            if (
                len(
                    doc["diff_against_previous_label"][diff_num]["text"][
                        text_num
                    ]
                )
                > 3
            ):
                for score_num in range(
                    len(
                        doc["diff_against_previous_label"][diff_num]["text"][
                            text_num
                        ][3]["scores"]
                    )
                ):
                    doc["diff_against_previous_label"][diff_num]["text"][
                        text_num
                    ][3]["scores"][score_num]["score"] = round(
                        doc["diff_against_previous_label"][diff_num]["text"][
                            text_num
                        ][3]["scores"][score_num]["score"],
                        digits,
                    )
    return doc


def run_truncation(
    mongo_client,
):
    """
    This method calls other methods in this module.

    Parameters:
        mongo_client (object): MongoClient object with database and collections
    """
    label_collection = mongo_client.label_collection
    label_collection_name = mongo_client.label_collection_name

    # get all docs in label_collection
    docs = label_collection.find({})

    # loop through all_label_ids
    for doc in docs:
        doc = round_score(doc)

        # update MongoDB
        mongo_client.update_db(label_collection_name, [doc])
