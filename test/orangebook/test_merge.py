import unittest
from orangebook.merge import OrangeBookMap
from db.mongo import MongoClient
import datetime
from utils.logging import getLogger

_logger = getLogger(__name__)


class Test_merge_with_orangebook_collection(unittest.TestCase):

    maxDiff = None

    # initial setup of unittest database
    mongo_client = MongoClient(
        "labels", "patents", "orangebook", alt_db_name="unittest"
    )
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

    ob = OrangeBookMap(mongo_client)

    def test_get_all_patents(self):
        self.assertTrue(self.ob.get_all_patents())

    def test_get_all_nda(self):
        self.assertTrue(self.ob.get_all_nda())

    def test_get_nda(self):
        self.assertTrue(self.ob.get_nda("9283178"))

    def test_get_patents(self):
        self.assertTrue(self.ob.get_patents("22315"))

    def test_get_all_nda_past_date(self):
        date_time_obj = datetime.datetime.strptime("2021-01-01", "%Y-%m-%d")
        # print(str(self.ob.get_all_nda_past_date(date_time_obj))[:50])
        self.assertTrue(self.ob.get_all_nda_past_date(date_time_obj))


class Test_merge_without_orangebook_collection(unittest.TestCase):

    maxDiff = None

    # initial setup of unittest database
    mongo_client = MongoClient(
        "labels", "patents", "orangebook", alt_db_name="unittest"
    )
    mongo_client.reimport_collection(
        mongo_client.label_collection_name,
        "resources/database_testing/labels.json",
    )
    mongo_client.reimport_collection(
        mongo_client.patent_collection_name,
        "resources/database_testing/patents.json",
    )
    mongo_client.drop_collection(mongo_client.orange_book_collection_name)

    ob = OrangeBookMap(mongo_client)

    def test_get_all_patents(self):
        self.assertTrue(self.ob.get_all_patents())

    def test_get_all_nda(self):
        self.assertTrue(self.ob.get_all_nda())

    def test_get_nda(self):
        self.assertTrue(self.ob.get_nda("9283178"))

    def test_get_patents(self):
        self.assertTrue(self.ob.get_patents("22315"))

    def test_get_all_nda_past_date(self):
        OrangeBookMap._orange_book_sort_by_date_df = None
        date_time_obj = datetime.datetime.strptime("2021-01-01", "%Y-%m-%d")
        # print(str(self.ob.get_all_nda_past_date(date_time_obj))[:50])
        self.assertFalse(self.ob.get_all_nda_past_date(date_time_obj))


if __name__ == "__main__":
    unittest.main()
