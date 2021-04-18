"""
This module provides methods to download and extract large files.
"""

import requests
import tarfile
import zipfile
import os
from urllib.parse import urlparse
import sys
import re

from utils.logging import getLogger

_logger = getLogger(__name__)


def download(url, folder_location):
    """
    Downloads URL to folder_location
    """
    response = requests.get(url, stream=True, allow_redirects=True)

    if "Content-Disposition" in response.headers.keys():
        file_name = response.headers["Content-Disposition"].split("filename=")[1]
    else:
        file_name = os.path.basename(urlparse(url).path)

    file_path = os.path.join(folder_location, file_name)
    if not os.path.exists(folder_location):
        os.makedirs(folder_location)

    # referenced https://stackoverflow.com/questions/15644964/python-progress-bar-and-downloads to create a download bar
    with open(file_path, "wb") as f:
        _logger.info("Downloading %s" % file_name)

        total_length = response.headers.get("content-length")
        if total_length is None:
            # no content length header
            f.write(response.content)
        else:
            dl = 0
            total_length = int(total_length)
            for data in response.iter_content(chunk_size=4096):
                dl += len(data)
                f.write(data)
                done = int(50 * dl / total_length)
                sys.stdout.write("\r[%s%s]" % ("=" * done, " " * (50 - done)))
                sys.stdout.flush()
    print("")
    return file_path


def extract_and_clean(file_name):
    """
    Extracts and deletes compressed file
    """
    # Extraction
    _logger.info("Extracting %s" % file_name)
    dir_name = os.path.dirname(os.path.abspath(file_name))
    base_name = os.path.basename(os.path.abspath(file_name))
    if file_name.endswith("tar.gz"):
        tar = tarfile.open(file_name, "r:gz")
        tar.extractall(path=dir_name)
        tar.close()
    elif file_name.endswith("tar"):
        tar = tarfile.open(file_name, "r:")
        tar.extractall(path=dir_name)
        tar.close()
    elif file_name.endswith("zip"):
        with zipfile.ZipFile(file_name, "r") as f:
            extract_dir = os.path.join(dir_name, base_name[:-4])
            f.extractall(extract_dir)

    # Cleanup
    _logger.info("Deleting %s" % file_name)
    if os.path.exists(file_name):
        os.remove(file_name)
