"""
Module is for merging all old OrangeBook files so that a lookup can be made.
"""

import glob
import pandas as pd

from utils.logging import getLogger

_logger = getLogger(__name__)


def _merge_all_csv():
    """
    Returns data-frame with columns: 'nda' (int64) and 'patent' (object)
    """
    filelist = sorted(
        glob.glob("resources/Orange_Book/*/patent.txt"), reverse=True
    )

    # combine all extracted EOBZIP into one giant df
    df_obzip = pd.concat(
        (
            pd.read_csv(csv_file, sep="~").rename(columns=str.lower)
            for csv_file in filelist
        ),
        ignore_index=True,
        join="outer",
        sort=True,
    )

    df_obzip_sm = df_obzip[["appl_no", "patent_no"]].copy()
    df_obzip_sm.columns = ["nda", "patent"]

    # remove '*PED' from the ends of some patent
    # patents cannot be converted to integer since they include 'RE44186'
    df_obzip_sm["patent"] = df_obzip_sm["patent"].map(
        lambda x: x.rstrip("*PED")
    )

    df_1985_2016 = pd.read_csv(
        "resources/Orange_Book/nber_1985_2016/FDA_drug_patents.csv", sep=","
    ).rename(columns=str.lower)

    df_1985_2016_sm = df_1985_2016[
        ["application_number", "patent_number"]
    ].copy()
    df_1985_2016_sm.columns = ["nda", "patent"]

    df_joined = (
        pd.concat([df_obzip_sm, df_1985_2016_sm])
        .drop_duplicates()
        .reset_index(drop=True)
    )

    return df_joined


def _get_all_associations_from_mongo(mongo_client):
    """Queries the OrangeBook collection in MongoDB, returning a
    dataframe with columns (nda, patent)
    Args:
        mongo_client (MongoClient): The mongo DB client initialized with the
                                    expected credentials
    Returns:
        pandas.DataFrame: Dataframe with columns "nda" and "patent" from the
                          OrangeBook data in the MongoDB
    """
    # Get all documents from MongoDB
    docs = mongo_client.orange_book_collection.find()
    if not docs.count():
        # Compile the OrangeBook locally, if no data found in MongoDB
        return _merge_all_csv()
    ndas, patents = [], []
    for doc in docs:
        ndas.append(int(doc["nda"]))
        patents.append(str(doc["patent_num"]))
    df = pd.DataFrame(data={"nda": ndas, "patent": patents})
    return df


class OrangeBookMap:

    _groups_groupby_NDA = None
    _groups_groupby_patent = None

    def __init__(self, mongo_client):
        # Initialize class attributes
        if (
            OrangeBookMap._groups_groupby_NDA is None
            or OrangeBookMap._groups_groupby_patent is None
        ):
            orange_book_data = _get_all_associations_from_mongo(mongo_client)
            OrangeBookMap._groups_groupby_NDA = orange_book_data.groupby(
                ["nda"]
            )
            OrangeBookMap._groups_groupby_patent = orange_book_data.groupby(
                ["patent"]
            )

    def get_patents(self, nda):
        """Returns a list of patent numbers given an NDA number.

        Parameters:
            nda (int or string): the number portion of an NDA number or string
        """
        try:
            return self._groups_groupby_NDA.get_group(int(nda))["patent"].tolist()
        except KeyError:
            return []

    def get_nda(self, patent):
        """Returns a list of NDA numbers given a patent number.

        Parameters:
            patent (int or string): the number portion of patent include 'RE'
                                    if applicable
        """
        try:
            return self._groups_groupby_patent.get_group(str(patent))[
                "nda"
            ].tolist()
        except KeyError:
            return []

    def get_all_patents(self):
        """Returns a list of all patent numbers."""
        return list(self._groups_groupby_patent.groups.keys())

    def get_all_nda(self):
        """Returns a list of all NDA numbers."""
        return list(self._groups_groupby_NDA.groups.keys())
