import unittest
from diff.run_diff import run_diff
from similarity import run_similarity_bert as r

from db.mongo import MongoClient
from utils.logging import getLogger

_logger = getLogger(__name__)


class Test_run_similarity(unittest.TestCase):

    # initial setup of unittest database
    mongo_client = MongoClient(
        "labels", "patents", "orangebook", alt_db_name="unittest"
    )
    mongo_client.label_collection_name
    mongo_client.reimport_collection(
        mongo_client.label_collection_name,
        "resources/database_testing/labels.json",
    )
    mongo_client.reimport_collection(
        mongo_client.patent_collection_name,
        "resources/database_testing/patents.json",
    )
    mongo_client.reimport_collection(
        mongo_client.orange_book_collection_name,
        "resources/database_testing/orangebook.json",
    )
    run_diff(mongo_client, None, None, None)

    def test_get_claims_in_patents_db(self):
        a = r.get_claims_in_patents_db(
            self.mongo_client, ["5202128", "5378474"]
        )
        self.assertIn("5202128", a)
        self.assertIn("5378474", a)

    def test_patent_claims_from_NDA(self):
        patent_list = r.patent_claims_from_NDA(self.mongo_client, ["NDA020616"])
        self.assertEqual(len(patent_list), 47)
        self.assertEqual(len(patent_list[0]), 4)
        self.assertEqual(patent_list[0][1], 1)

    def test_database(self):
        r.run_similarity(self.mongo_client, None, None, None, None)
        label_collection = self.mongo_client.label_collection
        label = label_collection.find_one(
            {
                "set_id": "b5cee013-000f-4e35-a284-1f58add31b4d",
                "spl_version": "16",
            },
        )
        self.assertIn("additions", label)
        self.assertIn("scores", label["additions"]["0"])
        self.assertIn("score", label["additions"]["0"]["scores"][0])
        self.assertIn("patent_number", label["additions"]["0"]["scores"][0])
        self.assertIn("nda_to_patent", label)
        self.assertIn("patents", label["nda_to_patent"][0])


if __name__ == "__main__":
    unittest.main()
