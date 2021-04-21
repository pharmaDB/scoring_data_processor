import os
import re
from utils.logging import getLogger

_logger = getLogger(__name__)


def get_lines_in_file(file_name):
    """Returns a list of a lines in a file"""
    if os.path.exists(file_name):
        f = open(file_name, "r")
        completed_label_id = [line.strip() for line in f if line.strip()]
        f.close()
        return completed_label_id
    else:
        return []


def append_to_file(file_name, data):
    """Append string or list of string to end of file"""
    if isinstance(data, str):
        lines = [data]
    else:
        lines = data

    if not os.path.exists(os.path.dirname(file_name)):
        os.makedirs(os.path.dirname(file_name))

    with open(file_name, "a") as f:
        for line in lines:
            f.write(str(line))
            f.write("\n")

    _logger.info(
        f"Append to file: {file_name}, data: {str(lines)[:250]}"
        + ("" if len(str(lines)) < 250 else "...")
    )


def store_to_file(file_name, data):
    """Store string or list of string to new file"""
    if os.path.exists(file_name):
        answer = ""
        while answer.lower() not in ["y", "n", "yes", "no"]:
            answer = input(
                f"File {file_name} already exists! Overwrite [y/n]: "
            )
        if answer.lower() in ["y", "yes"]:
            os.remove(file_name)
        else:
            _logger.error(f"Unable to overwrite and create file: {file_name}")
            return
    append_to_file(file_name, data)


def get_num_in_str(text):
    """Return number in word of letters and digits (ex: 'NDA019501')"""
    return int(re.match(r"([a-z]+)([0-9]+)", text, re.I).groups()[1])


def is_number(string):
    """
    Test if string is a float.
    """
    try:
        float(string)
        return True
    except ValueError:
        return False


def find_index(lst, key, value):
    """
    Given a list of dictionaries, [{key:value,},] return index of list with key
    and value.

    Parameters:
        lst (list): list to be searched for index
        key (immutable key): key to match
        value: value to match
    """
    for i, dic in enumerate(lst):
        if dic[key] == value:
            return i
    return -1


def reorg_list_dict(lst, key1, key2):
    """
    Given a list of dictionaries, [{key1:value1, key2:value2,},{key3:value3,
    key4:value4,},] return a dictionary of {value1: value2, value3:value4,}

    Parameters:
        lst (list): list to be searched for index
        key1 (immutable object): value of key1 to be turned into new key
        key2 (mutable object): value of key2 to be turned into value of value
                                of key1
    """
    rdict = {}
    for x in lst:
        rdict[x[key1]] = x[key2]
    return rdict
