"""
This file creates a .csv copy of all data in the labels collection and uploads
"""
import zipfile
import os
from bson.binary import Binary
from datetime import date

from utils.logging import getLogger

_logger = getLogger(__name__)


def compress_file(file_name):
    file_name = os.path.abspath(file_name)
    full_zip_file_path = os.path.abspath(file_name) + ".zip"
    _logger.info("Compressing %s" % file_name)
    zip_file = zipfile.ZipFile(full_zip_file_path, "w")
    zip_file.write(file_name, compress_type=zipfile.ZIP_DEFALTED)
    zip_file.close()

    # Cleanup
    _logger.info("Deleting %s" % file_name)
    if os.path.exists(file_name):
        os.remove(file_name)


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
