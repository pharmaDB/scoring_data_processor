from bson.objectid import ObjectId
import diff_match_patch as dmp_module
import re
from itertools import groupby

from utils import misc
from utils.logging import getLogger

_logger = getLogger(__name__)
_dmp = dmp_module.diff_match_patch()


def add_previous_and_next_labels(docs):
    """
    Assuming that labels docs are sorted, this method identifies all
    previous and next labels and add the following fields to each label doc:
        previous_label_published_date
        previous_label_spl_id
        previous_label_spl_version
        next_label_published_date
        next_label_spl_id
        next_label_spl_version

    Parameters:
        docs (list): list of sorted label docs from mongodb having the same
                     application_numbers
            Example:
            [{'_id': ObjectId('60733ce2faefa1fc4854fe64'),
            'application_numbers': ['NDA204223'], 'set_id':
                '582f42e5-444e-4246-af8c-e7e28097c69a',
                'spl_id':'4347699d-d9de-4f59-a3de-7af661e2e6c9', 'spl_version':
                    '4', 'published_date': '2020-01-29', 'sections': [{'name':
                        '1 INDICATIONS AND USAGE', 'text': "..."},...]},...]
    """
    docs[0]["previous_label_published_date"] = None
    docs[0]["previous_label_spl_id"] = None
    docs[0]["previous_label_spl_version"] = None
    docs[0]["next_label_published_date"] = None
    docs[0]["next_label_spl_id"] = None
    docs[0]["next_label_spl_version"] = None

    if len(docs) > 1:
        docs[0]["next_label_published_date"] = docs[1]["published_date"]
        docs[0]["next_label_spl_id"] = docs[1]["spl_id"]
        docs[0]["next_label_spl_version"] = docs[1]["spl_version"]

        last_num = len(docs) - 1
        for i in range(1, last_num):
            docs[i]["previous_label_published_date"] = docs[i - 1][
                "published_date"
            ]
            docs[i]["previous_label_spl_id"] = docs[i - 1]["spl_id"]
            docs[i]["previous_label_spl_version"] = docs[i - 1]["spl_version"]
            docs[i]["next_label_published_date"] = docs[i + 1]["published_date"]
            docs[i]["next_label_spl_id"] = docs[i + 1]["spl_id"]
            docs[i]["next_label_spl_version"] = docs[i + 1]["spl_version"]

        docs[last_num]["previous_label_published_date"] = docs[last_num - 1][
            "published_date"
        ]
        docs[last_num]["previous_label_spl_id"] = docs[last_num - 1]["spl_id"]
        docs[last_num]["previous_label_spl_version"] = docs[last_num - 1][
            "spl_version"
        ]
        docs[last_num]["next_label_published_date"] = None
        docs[last_num]["next_label_spl_id"] = None
        docs[last_num]["next_label_spl_version"] = None

    return docs


def get_diff(a, b):
    diff = _dmp.diff_main(a, b)
    _dmp.diff_cleanupSemantic(diff)
    diff = [list(x) for x in diff]
    return diff


def add_diff_against_previous_label(docs):
    """
    Assuming that labels docs are sorted, this method adds a
    'diff_against_previous_label' field that compares all changes from one
    label to a prior label, in a section by section manner

    For example:

    diff_against_previous_label: [{
                                'name':'1 INDICATIONS AND USAGE',
                                'text':[[0, '...'],[1, '...'],[-1, '...'],...],
                                'parent': null,
                                },...]

    The list within 'text' indicates whether a phrase within a section text has
    been kept (0) added (1), or removed (-1) from the prior version of the
    section text.

    Parameters:
        docs (list): list of sorted label docs from MongoDB having the same
                     application_numbers
    """

    # for first doc in docs, set all sections to 1
    if len(docs) > 0:
        docs[0]["diff_against_previous_label"] = []
        if docs[0]["sections"]:
            for section in docs[0]["sections"]:
                docs[0]["diff_against_previous_label"].append(
                    {
                        "name": section["name"],
                        "text": [[1, str(section["text"])]],
                        "parent": section["parent"],
                    }
                )

    if len(docs) > 1:
        for i in range(1, len(docs)):
            docs[i]["diff_against_previous_label"] = []
            section_names = [x["name"] for x in docs[i]["sections"]]
            # loop through all sections in prior label
            for section_prior in docs[i - 1]["sections"]:
                # if section in prior label is in current label
                if section_prior["name"] in section_names:
                    s_index = misc.find_index(
                        docs[i]["sections"], "name", section_prior["name"]
                    )
                    docs[i]["diff_against_previous_label"].append(
                        {
                            "name": section_prior["name"],
                            "text": get_diff(
                                str(section_prior["text"]),
                                str(docs[i]["sections"][s_index]["text"]),
                            ),
                            "parent": docs[i]["sections"][s_index]["parent"],
                        }
                    )
                # if section in prior label is not in current label
                else:
                    docs[i]["diff_against_previous_label"].append(
                        {
                            "name": section_prior["name"],
                            "text": [[-1, str(section_prior["text"])]],
                            "parent": section_prior["parent"],
                        }
                    )
            section_names_of_diff_against_previous_label = [
                x["name"] for x in docs[i]["diff_against_previous_label"]
            ]
            # loop through all sections in current label not in prior label
            for section in docs[i]["sections"]:
                if (
                    section["name"]
                    not in section_names_of_diff_against_previous_label
                ):
                    # select location to insert if name of section includes
                    # number
                    insert_loc = len(docs[i]["diff_against_previous_label"])
                    # print(docs[i]['_id'], section['name'])
                    if misc.is_number(section["name"].split()[0]):
                        for num in range(
                            len(docs[i]["diff_against_previous_label"])
                        ):
                            first_word = docs[i]["diff_against_previous_label"][
                                num
                            ]["name"].split()[0]
                            if misc.is_number(first_word) and float(
                                first_word
                            ) <= float(section["name"].split()[0]):
                                insert_loc = num + 1

                    docs[i]["diff_against_previous_label"].insert(
                        insert_loc,
                        {
                            "name": section["name"],
                            "text": [[1, str(section["text"])]],
                            "parent": section["parent"],
                        },
                    )
    return docs


def find_end(str, query, reverse=False):
    """
    Similar to find/rfind for end of sentence punctuation, but considers edge
    case of '.'
    """
    if query == ".":
        loc_list = [m.start() for m in re.finditer(r"\.", str)]
        if reverse:
            loc_list.reverse()
        for loc in loc_list:
            # test left hand side of '.' if '.' is preceded by lowercase letter
            # upper case letter may be an initial
            test_str = str[:loc]
            if len(test_str) > 0 and test_str[-1].islower():
                return loc
            # test right side to see if not followed by number, or followed by
            # upper letter
            test_str = str[loc:]
            if len(test_str) > 1 and not test_str[0].isnumeric():
                test_str = test_str[1:].lstrip()
                if len(test_str) > 0 and test_str[0].isupper():
                    return loc
        return -1
    elif reverse:
        return str.rfind(query)
    else:
        return str.find(query)


def rebuild_string(diff_text, num):
    """
    Give a diff_map_patch list rebuild a string around index num.  Strings are
    delimited by test_chars.  This function returns the rebuilt string and a
    list of indexes of additions that constitute the rebuild string.

    For example:
    rebuild_string([[0, 'Morphine '],[-1,'s'],[1,'S'],[0,'ulfate '],[-1, 'is an
        opioid']],2)
    returns:
    (Morphine Sulfate", [2])


    Parameters:
        diff_text (list of list): See example above
        num (int): index in diff_match_patch list; 0 would represent [0,
                   'Morphine '] in example above
    """
    # test_chars = [".", "?", "!", "\n", "\r"]
    test_chars = [".", "?", "!"]
    addition_list = [num]
    rebuilt_text = diff_text[num][1]

    # rebuilt left end
    i = num - 1
    while i >= 0:
        if diff_text[i][0] == -1:
            i -= 1
            continue
        txt = diff_text[i][1]

        # if txt is a complete sentence do not add to rebuilt string.
        if (
            txt.rstrip().endswith(".")
            and (
                (len(rebuilt_text) > 0 and not rebuilt_text[0].isnumeric())
                or (
                    len(rebuilt_text.lstrip()) > 0
                    and rebuilt_text.lstrip()[0].isupper()
                )
            )
        ) or any([txt.rstrip().endswith(x) for x in ["?", "!"]]):
            break

        # test if any test_chars is in txt and truncate at rightmost test_char
        loc_test_chars_list = [find_end(txt, e, True) for e in test_chars]
        if max(loc_test_chars_list) > -1:
            # test_char is rightmost index of any test_chars in txt
            test_char = test_chars[
                loc_test_chars_list.index(max(loc_test_chars_list))
            ]
            leftside_txt = txt[
                (max(loc_test_chars_list) + len(test_char)) :
            ].lstrip()
            rebuilt_text = leftside_txt + rebuilt_text
            if diff_text[i][0] == 1 and leftside_txt:
                addition_list.append(i)
            break
        # for case when there is no test_chars in txt, append txt to left side
        leftside_txt = txt
        if diff_text[i][0] == 1 and leftside_txt:
            addition_list.append(i)
        rebuilt_text = leftside_txt + rebuilt_text
        i -= 1

    # rebuild right end
    i = num + 1
    while i < len(diff_text):
        if diff_text[i][0] == -1:
            i += 1
            continue
        txt = diff_text[i][1]

        # if rebuilt_text ends with [".", "?", "!"] do not add to right end
        if (
            rebuilt_text.rstrip().endswith(".")
            and (
                (len(txt) > 0 and not txt[0].isnumeric())
                or (len(txt.lstrip()) > 0 and txt.lstrip()[0].isupper())
            )
        ) or any([rebuilt_text.rstrip().endswith(x) for x in ["?", "!"]]):
            break

        # test if any test_chars is in txt and truncate at leftmost test_char
        loc_test_chars_list = [find_end(txt, e) for e in test_chars]
        if max(loc_test_chars_list) > -1:
            min_loc = min([x for x in loc_test_chars_list if x > -1])
            # test_char is leftmost index of any test_chars in txt
            test_char = test_chars[loc_test_chars_list.index(min_loc)]
            rightside_txt = txt[: (min_loc + len(test_char))]
            rebuilt_text = rebuilt_text + rightside_txt
            if diff_text[i][0] == 1 and rightside_txt:
                addition_list.append(i)
            break
        # for case when there is not test_chars in txt, append entire txt
        rightside_txt = txt
        if diff_text[i][0] == 1 and rightside_txt:
            addition_list.append(i)
        rebuilt_text = rebuilt_text + rightside_txt
        i += 1

    addition_list = sorted(addition_list)
    return rebuilt_text, addition_list


def gather_additions(docs):
    """
    If, for each doc in docs, 'diff_against_previous_label':[{'text':[1,
    string],}] has a value of 1, the string is an addition.  This function
    gathers all additions in a label under key 'additions' and append a number
    X at within 'text', such as {'text':[1, string_A, X],}, to reference the
    addition entry.

    Example of 'additions'

    'additions':[0:{'expanded_context'::...,
                     "scores":[
                                {"patent_number":"12345678",
                                 "claim_number":5,
                                 "parent_claim_numbers":[1,2],
                                 "score":0.5172
                                },
                              ]
                   },
                ]

    Parameters:
        docs (list): list of sorted label docs from MongoDB having the same
                     application_numbers
    """
    for doc in docs:
        doc["additions"] = {}
        additions_num = 0
        for diff in doc["diff_against_previous_label"]:
            for j in range(len(diff["text"])):
                # if the diff is an addition, and the diff is not just spaces
                # or items that is removed by strip(), or the changes are not
                # just capitalization, or the changes are not just a stray
                # punctuation, then diffs are significant and the text should
                # be rebuilt around diff
                if (
                    diff["text"][j][0] == 1
                    and str(diff["text"][j][1]).strip()
                    and (
                        j == 0
                        or (
                            j > 0
                            and str(diff["text"][j][1]).lower()
                            != str(diff["text"][j - 1][1]).lower()
                        )
                    )
                    and any(
                        [i.isalnum() for i in str(diff["text"][j][1].strip())]
                    )
                ):
                    rebuilt_string, rebuilt_index = rebuild_string(
                        diff["text"], j
                    )
                    # if rebuilt_string is same a prior rebuilt_string
                    if (
                        additions_num > 0
                        and str(additions_num - 1) in doc["additions"].keys()
                        and doc["additions"][str(additions_num - 1)][
                            "expanded_content"
                        ]
                        == rebuilt_string
                    ):
                        diff["text"][j].append(str(additions_num - 1))
                    else:
                        # the scores are mock data at the moment
                        doc["additions"][str(additions_num)] = {
                            "expanded_content": rebuilt_string,
                            "scores": [],
                        }
                        diff["text"][j].append(str(additions_num))
                        additions_num += 1
    return docs


def group_label_docs_by_set_id(docs):
    """
    This function groups the docs by 'set_id" and returns a list of list,
    wherein the inner list share the same set_id.

    Return example:
        [[{set_id:X,},{set_id:X,}],[{set_id:Y,},{set_id:Y,}],]

    Parameters:
        docs (list): list of label docs from MongoDB having the same
                     application_numbers
    """

    def key_func(k):
        return k["set_id"]

    docs = sorted(
        docs,
        key=key_func,
        reverse=False,
    )
    return_list = [list(value) for key, value in groupby(docs, key=key_func)]
    return return_list


def run_diff(
    mongo_client,
    processed_label_ids_file,
    processed_nda_file,
    unprocessed_label_ids_file,
):
    """
    This method calls other methods in this module and tracks completed
    label IDs and completed NDA numbers.

    Parameters:
        mongo_client (object): MongoClient object with database and collections
        processed_label_ids_file (Path): location to store processed ids
        processed_nda_file (Path): location to store processed NDAs
        unprocessed_label_ids_file (Path): location to store unprocessed ids
    """
    label_collection = mongo_client.label_collection

    # open processed_label_id_file and return a list of processed _id string
    if processed_label_ids_file:
        processed_label_ids = misc.get_lines_in_file(processed_label_ids_file)
    else:
        processed_label_ids = []

    # get list of label_id strings excluding any string in processed_label_id
    all_label_ids = [
        x
        for x in [str(y) for y in label_collection.distinct("_id", {})]
        if x not in processed_label_ids
    ]

    label_index = 0

    # loop through all_label_ids, popping off label_ids after diffing sections
    while len(all_label_ids) > 0:
        if label_index >= len(all_label_ids):
            # all labels were traversed, remaining labels have no
            # application_numbers; store unprocessed label_ids to disk
            if unprocessed_label_ids_file:
                misc.append_to_file(unprocessed_label_ids_file, all_label_ids)
            break

        # pick label_id
        label_id_str = str(all_label_ids[label_index])

        # get a list of NDA numbers (ex. ['NDA019501',]) associated with _id
        application_numbers = label_collection.find_one(
            {"_id": ObjectId(label_id_str)},
            {"_id": 0, "application_numbers": 1},
        )["application_numbers"]

        if not application_numbers:
            # if label doesn't have application number skip for now
            label_index += 1
            continue

        # find all other docs with the same list of NDA numbers
        # len(similar_label_docs) is at least 1
        similar_label_docs = list(
            label_collection.find({"application_numbers": application_numbers})
        )

        groups_by_set_id = group_label_docs_by_set_id(similar_label_docs)
        for set_id_group in groups_by_set_id:
            # sort by published_date
            set_id_group = sorted(
                set_id_group,
                key=lambda i: (i["published_date"]),
                reverse=False,
            )
            set_id_group = add_previous_and_next_labels(set_id_group)
            set_id_group = add_diff_against_previous_label(set_id_group)
            set_id_group = gather_additions(set_id_group)
        # ungroup similar_label_docs by set id
        similar_label_docs = [
            item for sublist in groups_by_set_id for item in sublist
        ]

        mongo_client.update_db(
            mongo_client.label_collection_name, similar_label_docs
        )

        similar_label_docs_ids = [str(x["_id"]) for x in similar_label_docs]

        # remove similar_label_docs_ids from all_label_ids
        all_label_ids = [
            x for x in all_label_ids if x not in similar_label_docs_ids
        ]
        # store processed_label_ids and processed application_numbers to disk
        if processed_label_ids_file:
            misc.append_to_file(
                processed_label_ids_file, similar_label_docs_ids
            )
        if processed_nda_file:
            misc.append_to_file(
                processed_nda_file, str(application_numbers)[1:-1]
            )
