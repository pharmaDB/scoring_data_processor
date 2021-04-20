"""
Module is for merging all old OrangeBook files so that a lookup can be made.
"""

import glob
import pandas as pd

from utils.logging import getLogger

_logger = getLogger(__name__)


class OrangeBookMap:
    _groups_groupby_NDA = None
    _groups_groupby_patent = None

    def __init__(self):
        self._groups_groupby_NDA = self._merge_all_csv().groupby(["nda"])
        self._groups_groupby_patent = self._merge_all_csv().groupby(["patent"])

    def _merge_all_csv(self):
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

    def get_patents(self, nda):
        """Returns a list of patent numbers given an NDA number.

        Parameters:
            nda (int or string): the number portion of an NDA number or string
        """
        return self._groups_groupby_NDA.get_group(int(nda))["patent"].tolist()

    def get_nda(self, patent):
        """Returns a list of NDA numbers given a patent number.

        Parameters:
            patent (int or string): the number portion of patent include 'RE'
                                    if applicable
        """
        return self._groups_groupby_patent.get_group(str(patent))[
            "nda"
        ].tolist()

    def get_all_patents(self):
        """Returns a list of all patent numbers."""
        return list(self._groups_groupby_patent.groups.keys())

    def get_all_nda(self):
        """Returns a list of all NDA numbers."""
        return list(self._groups_groupby_NDA.groups.keys())
