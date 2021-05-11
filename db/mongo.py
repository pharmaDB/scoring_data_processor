from dotenv import dotenv_values
import os
import pymongo
from bson.objectid import ObjectId
import dateutil
import json
import sys

from utils.logging import getLogger

_logger = getLogger(__name__)

_config = dict(
    dotenv_values(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".env")
    )
)


class MongoClient:
    def __init__(
        self,
        label_collection_name,
        patent_collection_name,
        orange_book_collection_name,
        alt_db_name=None,
    ):
        """
        Initializes a MongoDB connection and stores strings of collection names

        Parameters:
            label_collection_name (String): name of the label collection
            patent_collection_name (String): name of the patent collection
            orange_book_collection_name (String): name of orange book collection
            alt_db_name (String): name of database if different from the one in
                                  `.env`. Used mainly for unit-tests.
        """
        self.db = connect_mongo(alt_db_name)
        self.label_collection_name = label_collection_name
        self.patent_collection_name = patent_collection_name
        self.orange_book_collection_name = orange_book_collection_name
        self.label_collection = self.db[self.label_collection_name]
        self.patent_collection = self.db[self.patent_collection_name]
        self.orange_book_collection = self.db[self.orange_book_collection_name]

    def drop_collection(self, collection_name):
        """
        Drop collection from MongoDB

        Parameters:
            collection_name (String):
                name of the collection to reimport
        """
        db = self.db
        collection = db[collection_name]
        collection.drop()

    def reimport_collection(self, collection_name, file_name):
        """
        Reimports collection from file_name into MongoDB

        Parameters:
            collection_name (String):
                name of the collection to reimport
            file_name (path):
                location of the json file for the collection to import
        """
        db = self.db
        collection = db[collection_name]
        collection.drop()
        with open(file_name, "r") as f:
            lines = f.readlines()
            for line in lines:
                doc = json.loads(line)
                doc["_id"] = ObjectId(doc["_id"]["$oid"])
                # additional code to process oid in claims
                if "claims" in doc.keys():
                    for item in doc["claims"]:
                        if "_id" in item.keys():
                            item["_id"] = ObjectId(item["_id"]["$oid"])
                if "created_at" in doc:
                    doc["created_at"] = dateutil.parser.parse(
                        doc["created_at"]["$date"]
                    )
                collection.insert_one(doc)
        _logger.info(f"Reimported '{collection_name}' with '{file_name}'")

    def update_db(self, collection_name, docs):
        """
        Update all docs in docs in the collection

        Parameters:
            collection_name (string):
                MongoDB collection name
            docs (list):
                list of sorted label docs from MongoDB having the same
                application_numbers
            alt_db_name (String):
                this is an optional argument that will set the db_name to a value
                other than the value in the .env file.
        """
        db = self.db
        collection = db[collection_name]
        for doc in docs:
            result = collection.replace_one({"_id": doc["_id"]}, doc)
            if result.matched_count < 1:
                _logger.error(
                    f"Unable to uploaded to collection '{collection_name}': "
                    f"{str(doc)[:250]}" + ("" if len(str(doc)) < 250 else "...")
                )
            else:
                _logger.info(
                    f"Uploaded to collection '{collection_name}': "
                    f"{str(doc)[:250]}" + ("" if len(str(doc)) < 250 else "...")
                )
        return


def connect_mongo(alt_db_name=None):
    """
    This method connects to MongoDB and returns a MongoDB database object
    using the .env file.  alt_db_name can be provided to change change the
    database to a database different from the one in the .env file for testing
    purposes.

    Parameters:
        alt_db_name (String):
            this is an optional argument that will set the db_name to a value
            other than the value in the .env file.
    """
    try:
        host, port, db_name = (
            _config["MONGODB_HOST"],
            int(_config["MONGODB_PORT"]),
            _config["MONGODB_NAME"],
        )
        if alt_db_name:
            db_name = alt_db_name
        mongo = pymongo.MongoClient(host, port=port)
        _logger.info(
            f"Successfully connected to mongodb at {host}:{port} db_name: "
            f"{db_name}"
        )
        return mongo[db_name]
    except Exception as e:
        _logger.error(f"Error occured {e}")
        sys.exit(1)
