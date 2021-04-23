import unittest
import os
from diff.run_diff import run_diff
from similarity import run_similarity as r

from db.mongo import reimport_collection
from utils.logging import getLogger

_logger = getLogger(__name__)


class Test_run_similarity(unittest.TestCase):

    # initial setup of unittest database
    DB_NAME = "unittest"
    LABEL_COLLECTION = "labels"
    PATENT_COLLECTION = "patents"
    PROCESSED_ID_DIFF_FILE = (
        "resources/processed_log_unittest/processed_id_diff.csv"
    )
    PROCESSED_NDA_DIFF_FILE = (
        "resources/processed_log_unittest/processed_nda_diff.csv"
    )
    PROCESSED_ID_SIMILARITY_FILE = (
        "resources/processed_log_unittest/processed_id_similarity.csv"
    )
    PROCESSED_NDA_SIMILARITY_FILE = (
        "resources/processed_log_unittest/processed_nda_similarity.csv"
    )
    reimport_collection(
        LABEL_COLLECTION, "assets/database_before/labels.json", DB_NAME
    )
    reimport_collection(
        PATENT_COLLECTION, "assets/database_before/patents.json", DB_NAME
    )
    if os.path.exists(PROCESSED_ID_DIFF_FILE):
        os.remove(PROCESSED_ID_DIFF_FILE)
    if os.path.exists(PROCESSED_NDA_DIFF_FILE):
        os.remove(PROCESSED_NDA_DIFF_FILE)
    if os.path.exists(PROCESSED_ID_SIMILARITY_FILE):
        os.remove(PROCESSED_ID_SIMILARITY_FILE)
    if os.path.exists(PROCESSED_NDA_SIMILARITY_FILE):
        os.remove(PROCESSED_NDA_SIMILARITY_FILE)
    run_diff(
        LABEL_COLLECTION,
        "resources/processed_log_unittest/processed_id_diff.csv",
        "resources/processed_log_unittest/processed_nda_diff.csv",
        DB_NAME,
    )
    # setup_MongoDB for the run_similarity module to point to the 'unittest' DB
    r.setup_MongoDB(LABEL_COLLECTION, PATENT_COLLECTION, DB_NAME)

    def test_get_claims_in_patents_db(self):
        a = r.get_claims_in_patents_db(["5202128", "5378474"])
        self.assertIn("5202128", a)
        self.assertIn("5378474", a)
        # for patent in a.keys():
        #     for claim in a[patent].keys():
        #         print(claim, a[patent][claim])

    def test_patent_claims_longhand_form_from_NDA(self):
        print(["ND020616"])
        print(r.patent_claims_longhand_form_from_NDA(["NDA020616"]))


if __name__ == "__main__":
    unittest.main()
