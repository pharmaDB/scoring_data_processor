"""
Provides for functions to turn a dictionary of claims (ex: {claim_num
(int):claim_text (str),...}) to an ordered dictionary of claims, wherein
claim_text becomes a list of claim_text as though the claim text is written in
'long-hand' form without any references to parent claims.  Removal of claim
reference numbers and specification reference numbers allows each claim to be
treated as a monolithic statement for natural language processing purposes. In
particular, these features are provided by dependent_to_independent_claim().
"""

import re
from collections import OrderedDict


def drop_claim_number(text):
    """
    Returns text without claim number at start of claim. For example, drops
    '\n1. ' from '\n1. A gadget comprising a widget.\n'.

    Parameters:
        text (string): claim text as a string
    """
    if bool(
            re.match(r'.*(\d+)\.([a-zA-Z]+)',
                     text.split(' ', 1)[0].strip('\n'))):
        text = text.split(' ', 1)[0].split('.', 1)[1] + ' ' + text.split(
            ' ', 1)[1]
    if bool(re.match(r'.*(\d+)\.$', text.split(' ', 1)[0].strip('\n'))):
        text = text.split(' ', 1)[1]
    if bool(re.match(r'.*(\d+)$', text.split('. ', 1)[0].strip('\n'))):
        text = text.split('. ', 1)[1]
    return text


def drop_reference_numbers(text):
    """
    Returns text without reference number in parenthesis. For example, drops
    '(1)' from 'a widget (1)'.

    Parameters:
        text (string): claim text as a string
    """
    if bool(re.match(r'.*\([a-zA-Z0-9]+\).*', text.strip('\n'))):
        text = re.sub(r' \([a-zA-Z0-9]+\)', '', text)
        text = re.sub(r'\([a-zA-Z0-9]+\)', '', text)
    return text


def extract_alternative_numbers(text):
    """
    Returns a list of numbers given a string of text.  For example,
    extract_alternative_numbers("1, 2, and 3") returns [1,2,3].
    extract_alternative_numbers["1-2 or 3-5"] returns [1, 2, 3, 4, 5].

    Parameters:
        text (String): text that recite alternate numbers in string
    """
    claim_num = []

    # Add to claim_num all claim all claims in range
    # for case when ranges are written as '1-2'
    # findall_range ex: ['1-2', '3 - 4']
    findall_range = re.findall(r'\d+(?:-| - )\d+', text)
    if bool(findall_range):
        for range_ in findall_range:
            i = range_.split("-")
            claim_num.extend(range(int(i[0].strip()), int(i[1].strip()) + 1))
        text = re.sub(r'\d+(?:-| - )\d+', '', text)

    # for case when ranges are written as '1 to 2'
    # findall_range ex: ['1 to 2', '3 to 4']
    findall_range = re.findall(r'\d+ to \d+', text)
    if bool(findall_range):
        for range_ in findall_range:
            i = range_.split("-")
            claim_num.extend(range(int(i[0]), int(i[1]) + 1))
        text = re.sub(r'\d+ to \d+', '', text)

    # for all other cases of numbers in text; ex. '1, 2'
    findall_range = re.findall(r'\d+', text)
    # convert string to int
    findall_range = [int(i) for i in findall_range]
    claim_num.extend(findall_range)

    return claim_num


def get_parent_claim(text, preceding_claims):
    """
    Returns (a list of all parent not including grandparent or other ancestor
    claims, claim text without recitation of parent claim numbers) for a single
    patent claim.  For example, if claim 3 depends on claim 2 depends on claim
    1, and the text parameter refers to claim 3, get_parent_claim("The gadget
    of claim 2 further comprising") returns ([2,], "The gadget further
    comprising").

    This will even work if a dependent claim refers back to the
    preceding/previous claims not by number, but by prose.  As an example, if
    claim 4 recites "The gadget of any preceding claim further comprising"),
    get_parent_claim() of claim 4 would return ([1,2,3,], "The gadget further
    comprising").

    Parameters:
        text (String): patent claim text
        preceding_claims (List): list of preceding patent claim numbers
    """
    # test if substring with '... claim(s) [number] ...' is recited in text
    matching_search_obj = re.search(
        r' (?:as|according to|of)\W+(?:\w+\W+){,6}(?:claims|claim)(?: or| and| \d+(?:-| - | to )\d+,| \d+(?:-| - | to )\d+| \d+,| \d+)+ inclusive',
        text,
        flags=re.IGNORECASE)

    # re.search() again without the word 'inclusive'
    if not bool(matching_search_obj):
        matching_search_obj = re.search(
            r' (?:as|according to|of)\W+(?:\w+\W+){,6}(?:claims|claim)(?: or| and| \d+(?:-| - | to )\d+,| \d+(?:-| - | to )\d+| \d+,| \d+)+',
            text,
            flags=re.IGNORECASE)

    if bool(matching_search_obj):
        search_span = matching_search_obj.span()
        text_with_match_removed = text[:search_span[0]] + text[search_span[1]:]

        matching_search_str = matching_search_obj.group(0)
        claim_num = extract_alternative_numbers(matching_search_str)

        return claim_num, text_with_match_removed

    # test if 'any one of preceding claims' or variant is recited
    matching_search_obj = re.search(
        r' (?:as|according to|of)\W+(?:\w+\W+){,6}(?:preceding|previous|prior|above|aforementioned|aforesaid|aforestated|former) (?:claims|claim)',
        text,
        flags=re.IGNORECASE)

    # re.search() again for variants of test above for words after claim(s)
    if not bool(matching_search_obj):
        matching_search_obj = re.search(
            r' (?:as|according to|of)\W+(?:\w+\W+){,6}(?:claims|claim) (?:preceding|previously recited|prior|above|aforementioned|aforesaid|aforestated|former)',
            text,
            flags=re.IGNORECASE)

    if bool(matching_search_obj):
        search_span = matching_search_obj.span()
        text_with_match_removed = text[:search_span[0]] + text[search_span[1]:]

        return preceding_claims, text_with_match_removed

    # for case when no match is found
    return [], text


def dependent_to_independent_claim(od):
    """
    Returns an OrderedDict of {claim_num (int):[{'parent_clm':
    [independent_claim, ..., grand-parent_claim , parent_claim,],'text':
    claim_text},],}
    for a patent, wherein all dependent claims are turned independent.

    For example, if the patent claims are:
        {
            1: "A gadget comprising X.\n",
            2: "A gadget comprising Y.\n",
            3: "The gadget of any prior claim comprising Z.\n",
        }

    This function returns:
        {
            1: [
                {
                    'parent_clm': [],
                    "text": "A gadget comprising X.\n"
                },
            ],
            2: [
                {
                    'parent_clm': [],
                    "text": "A gadget comprising Y.\n"
                },
            ],
            3: [
                {
                    'parent_clm': [1],
                    "text":
                    "A gadget comprising X.\n The gadget comprising Z.\n"
                },
                {
                    'parent_clm': [2],
                    "text":
                    "A gadget comprising Y.\n The gadget comprising Z.\n"
                },
            ]
        }

    Parameters:
        od (OrderedDict): An OrderedDict of {claim_num (int): claim_text (str),..}
    """

    print(str(od)[:500])

    if not od:
        return OrderedDict()

    # claim_parent_text_od is OrderedDict of
    # {claim_num:([parent_claim_num,..],"text_without_parent_claim"),..}
    claim_parent_text_od = OrderedDict()

    all_claim_nums = list(od.keys())

    print(all_claim_nums)

    for key, claim_text in od.items():
        # drop first word if claim text begins with number, for example: '\n1.'
        claim_text = drop_claim_number(claim_text)

        # remove reference characters in parenthesis, for example: '(1)'
        claim_text = drop_reference_numbers(claim_text)

        # split claim_text into a list of parent claims and remainder claim text
        claim_parent_text_od[key] = get_parent_claim(
            claim_text, all_claim_nums[:all_claim_nums.index(key)])

    # claim_parent_text_list is a list of
    # [(claim_num,([parent_claim_num,..],"text_without_parent_claim")),..]
    claim_parent_text_list = list(claim_parent_text_od.items())

    print(str(claim_parent_text_list[1]))
    print(str(claim_parent_text_list[2]))
    print(str(claim_parent_text_list[3]))
    print(str(claim_parent_text_list[4]))

    # no_dependent_od is returned and consists of:
    # {claim_num: [{'parent_clm': [], "text": claim_text },   ],
    no_dependent_od = OrderedDict()

    i = 0
    # run_loop stops while loop below after i travels the length of
    # claim_parent_text_list, and does not add an element to no_dependent_od
    # for case when there is a dependency issue in patent
    run_loop = True

    # while claim_parent_text_list is not empty
    while claim_parent_text_list:
        claim_num = claim_parent_text_list[i][0]
        # parent_claim_num_list = [parent_claim_num,] of immediate parent claim
        parent_claim_num_list = claim_parent_text_list[i][1][0]
        text_without_parent_claim = claim_parent_text_list[i][1][1]
        if not parent_claim_num_list:
            # list of parent_claim_num is empty; don't increment i
            no_dependent_od[claim_num] = [
                OrderedDict([('parent_clm', []),
                             ('text', text_without_parent_claim)])
            ]
            claim_parent_text_list.pop(i)
            run_loop = True
        else:
            # ensure that all claims in parent_claim_num_list elements are in no_dependent_od
            parent_claim_not_ready_list = [
                True if j not in no_dependent_od else False
                for j in parent_claim_num_list
            ]
            if not any(parent_claim_not_ready_list):

                # add all claim alternatives to a list
                alternative_list = []
                for parent_claim in parent_claim_num_list:
                    # no_dependent_od consists of:
                    # {claim_num: [{'parent_clm': [], "text": claim_text },],
                    for item in no_dependent_od[parent_claim]:
                        item_parent_clm_list = item['parent_clm']
                        item_text = item['text']
                        new_od = OrderedDict([
                            ('parent_clm',
                             item_parent_clm_list + [parent_claim]),
                            ('text',
                             item_text + ' ' + text_without_parent_claim)
                        ])
                        alternative_list.append(new_od)

                no_dependent_od[claim_num] = alternative_list
                claim_parent_text_list.pop(i)
                run_loop = True

        if i > len(claim_parent_text_list) - 1:
            # ensure that i always points to a claim_parent_text_list element
            i = 0
            if not run_loop:
                break
            run_loop = False

    print("***")
    return no_dependent_od



