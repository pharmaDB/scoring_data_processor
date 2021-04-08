'''
This file will grab the corresponding model from
'''

import requests
import tarfile
import os
from urllib.parse import urlparse
import sys

from utils.logging import getLogger

_logger = getLogger(__name__)


def download(url, folder_location):
    '''
    Downloads URL to folder_location
    '''
    file_name = os.path.basename(urlparse(url).path)
    file_path = os.path.join(folder_location, file_name)
    if not os.path.exists(folder_location):
        os.makedirs(folder_location)

    # referenced https://stackoverflow.com/questions/15644964/python-progress-bar-and-downloads
    with open(file_path, 'wb') as f:
        _logger.info("Downloading %s" % file_name)

        response = requests.get(url, stream=True, allow_redirects=True)
        total_length = response.headers.get('content-length')
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
                sys.stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50 - done)))
                sys.stdout.flush()
    print("")
    return file_path


def extract_and_clean(file_name):
    '''
    Extracts and deletes compressed file
    '''
    # Extraction
    _logger.info("Extracting %s" % file_name)
    if file_name.endswith("tar.gz"):
        tar = tarfile.open(file_name, "r:gz")
        tar.extractall(path=os.path.dirname(os.path.abspath(file_name)))
        tar.close()
    elif file_name.endswith("tar"):
        tar = tarfile.open(file_name, "r:")
        tar.extractall(path=os.path.dirname(os.path.abspath(file_name)))
        tar.close()

    # Cleanup
    _logger.info("Deleting %s" % file_name)
    if os.path.exists(file_name):
        os.remove(file_name)
