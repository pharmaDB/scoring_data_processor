import unittest
from similarity.no_dependent_claim import (
    drop_claim_number,
    drop_reference_numbers,
    get_parent_claim,
    dependent_to_independent_claim,
)
import copy


class Test_no_dependent_claim(unittest.TestCase):

    maxDiff = None

    claims_pre_treat = {
        1: "\n1. A gadget comprising a widget(1).\n",
        2: "2.A gadget comprising a gizmo(b).\n",
        3: "Claim 3. The gadget of claim 1 further comprising a gizmo (200).\n",
        4: "4. The gadget of claim 2 further comprising a widget (1).\n",
        5: "The gadget of claim 3 further comprising a doodad.\n",
    }

    claims_no_number = {
        1: "A gadget comprising a widget(1).\n",
        2: "A gadget comprising a gizmo(b).\n",
        3: "The gadget of claim 1 further comprising a gizmo (200).\n",
        4: "The gadget of claim 2 further comprising a widget (1).\n",
        5: "The gadget of claim 3 further comprising a doodad.\n",
    }

    claims_no_reference = {
        1: "\n1. A gadget comprising a widget.\n",
        2: "2.A gadget comprising a gizmo.\n",
        3: "Claim 3. The gadget of claim 1 further comprising a gizmo.\n",
        4: "4. The gadget of claim 2 further comprising a widget.\n",
        5: "The gadget of claim 3 further comprising a doodad.\n",
    }

    claims_clean = {
        1: "A gadget comprising a widget.\n",
        2: "A gadget comprising a gizmo.\n",
        3: "The gadget of claim 1 further comprising a gizmo.\n",
        4: "The gadget of claim 2 further comprising a widget.\n",
        5: "The gadget of claim 3 further comprising a doodad.\n",
    }

    claims_get_parent_claims_and_text = {
        1: ([], "A gadget comprising a widget.\n"),
        2: ([], "A gadget comprising a gizmo.\n"),
        3: ([1], "The gadget further comprising a gizmo.\n"),
        4: ([2], "The gadget further comprising a widget.\n"),
        5: ([3], "The gadget further comprising a doodad.\n"),
    }

    claims_clean_no_dependent = {
        1: [{"parent_clm": [], "text": "A gadget comprising a widget.\n"}],
        2: [{"parent_clm": [], "text": "A gadget comprising a gizmo.\n"}],
        3: [
            {
                "parent_clm": [1],
                "text": "A gadget comprising a widget.\n The gadget further comprising a gizmo.\n",
            }
        ],
        4: [
            {
                "parent_clm": [2],
                "text": "A gadget comprising a gizmo.\n The gadget further comprising a widget.\n",
            }
        ],
        5: [
            {
                "parent_clm": [1, 3],
                "text": "A gadget comprising a widget.\n The gadget further comprising a gizmo.\n The gadget further comprising a doodad.\n",
            }
        ],
    }

    # these are example dependent claims from MPEP 608.01(n)
    sample_claim_preambles_of_alternatives = {
        6: "A gadget according to claim 1, further comprising\n",
        7: "A gadget according to claims 3 or 4, further comprising\n",
        8: "A gadget as in any one of the preceding claims, in which\n",
        9: "A gadget as in any one of claims 1, 2, and 3, in which\n",
        10: "A gadget as in either claim 1 or claim 2, further comprising\n",
        11: "A gadget as in claims 1, 2, or 3, further comprising\n",
        12: "A gadget as in one of claims 1-3, in which\n",
        13: "A gadget as in any preceding claim, in which\n",
        14: "A gadget as in any of claims 1-2 or 3-4, in which\n",
        15: "A gadget as in any one of claims 1, 2, or 3 - 4 inclusive, in which\n",
        16: "A gadget as in any one of claim 200, in which\n",
    }

    claim_preambles_of_alternatives_no_dependents = {
        6: [
            {
                "parent_clm": [1],
                "text": "A gadget comprising a widget.\n A gadget further comprising\n",
            }
        ],
        7: [
            {
                "parent_clm": [1, 3],
                "text": "A gadget comprising a widget.\n"
                " The gadget further comprising a gizmo.\n"
                " A gadget further comprising\n",
            },
            {
                "parent_clm": [2, 4],
                "text": "A gadget comprising a gizmo.\n"
                " The gadget further comprising a widget.\n"
                " A gadget further comprising\n",
            },
        ],
        8: [
            {
                "parent_clm": [1],
                "text": "A gadget comprising a widget.\n A gadget, in which\n",
            },
            {
                "parent_clm": [2],
                "text": "A gadget comprising a gizmo.\n A gadget, in which\n",
            },
            {
                "parent_clm": [1, 3],
                "text": "A gadget comprising a widget.\n"
                " The gadget further comprising a gizmo.\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [2, 4],
                "text": "A gadget comprising a gizmo.\n"
                " The gadget further comprising a widget.\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [1, 3, 5],
                "text": "A gadget comprising a widget.\n"
                " The gadget further comprising a gizmo.\n"
                " The gadget further comprising a doodad.\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [1, 6],
                "text": "A gadget comprising a widget.\n"
                " A gadget further comprising\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [1, 3, 7],
                "text": "A gadget comprising a widget.\n"
                " The gadget further comprising a gizmo.\n"
                " A gadget further comprising\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [2, 4, 7],
                "text": "A gadget comprising a gizmo.\n"
                " The gadget further comprising a widget.\n"
                " A gadget further comprising\n"
                " A gadget, in which\n",
            },
        ],
        9: [
            {
                "parent_clm": [1],
                "text": "A gadget comprising a widget.\n A gadget in which\n",
            },
            {
                "parent_clm": [2],
                "text": "A gadget comprising a gizmo.\n A gadget in which\n",
            },
            {
                "parent_clm": [1, 3],
                "text": "A gadget comprising a widget.\n"
                " The gadget further comprising a gizmo.\n"
                " A gadget in which\n",
            },
        ],
        10: [
            {
                "parent_clm": [1],
                "text": "A gadget comprising a widget.\n A gadget further comprising\n",
            },
            {
                "parent_clm": [2],
                "text": "A gadget comprising a gizmo.\n A gadget further comprising\n",
            },
        ],
        11: [
            {
                "parent_clm": [1],
                "text": "A gadget comprising a widget.\n A gadget further comprising\n",
            },
            {
                "parent_clm": [2],
                "text": "A gadget comprising a gizmo.\n A gadget further comprising\n",
            },
            {
                "parent_clm": [1, 3],
                "text": "A gadget comprising a widget.\n"
                " The gadget further comprising a gizmo.\n"
                " A gadget further comprising\n",
            },
        ],
        12: [
            {
                "parent_clm": [1],
                "text": "A gadget comprising a widget.\n A gadget in which\n",
            },
            {
                "parent_clm": [2],
                "text": "A gadget comprising a gizmo.\n A gadget in which\n",
            },
            {
                "parent_clm": [1, 3],
                "text": "A gadget comprising a widget.\n"
                " The gadget further comprising a gizmo.\n"
                " A gadget in which\n",
            },
        ],
        13: [
            {
                "parent_clm": [1],
                "text": "A gadget comprising a widget.\n A gadget, in which\n",
            },
            {
                "parent_clm": [2],
                "text": "A gadget comprising a gizmo.\n A gadget, in which\n",
            },
            {
                "parent_clm": [1, 3],
                "text": "A gadget comprising a widget.\n"
                " The gadget further comprising a gizmo.\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [2, 4],
                "text": "A gadget comprising a gizmo.\n"
                " The gadget further comprising a widget.\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [1, 3, 5],
                "text": "A gadget comprising a widget.\n"
                " The gadget further comprising a gizmo.\n"
                " The gadget further comprising a doodad.\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [1, 6],
                "text": "A gadget comprising a widget.\n"
                " A gadget further comprising\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [1, 3, 7],
                "text": "A gadget comprising a widget.\n"
                " The gadget further comprising a gizmo.\n"
                " A gadget further comprising\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [2, 4, 7],
                "text": "A gadget comprising a gizmo.\n"
                " The gadget further comprising a widget.\n"
                " A gadget further comprising\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [1, 8],
                "text": "A gadget comprising a widget.\n"
                " A gadget, in which\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [2, 8],
                "text": "A gadget comprising a gizmo.\n"
                " A gadget, in which\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [1, 3, 8],
                "text": "A gadget comprising a widget.\n"
                " The gadget further comprising a gizmo.\n"
                " A gadget, in which\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [2, 4, 8],
                "text": "A gadget comprising a gizmo.\n"
                " The gadget further comprising a widget.\n"
                " A gadget, in which\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [1, 3, 5, 8],
                "text": "A gadget comprising a widget.\n"
                " The gadget further comprising a gizmo.\n"
                " The gadget further comprising a doodad.\n"
                " A gadget, in which\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [1, 6, 8],
                "text": "A gadget comprising a widget.\n"
                " A gadget further comprising\n"
                " A gadget, in which\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [1, 3, 7, 8],
                "text": "A gadget comprising a widget.\n"
                " The gadget further comprising a gizmo.\n"
                " A gadget further comprising\n"
                " A gadget, in which\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [2, 4, 7, 8],
                "text": "A gadget comprising a gizmo.\n"
                " The gadget further comprising a widget.\n"
                " A gadget further comprising\n"
                " A gadget, in which\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [1, 9],
                "text": "A gadget comprising a widget.\n"
                " A gadget in which\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [2, 9],
                "text": "A gadget comprising a gizmo.\n"
                " A gadget in which\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [1, 3, 9],
                "text": "A gadget comprising a widget.\n"
                " The gadget further comprising a gizmo.\n"
                " A gadget in which\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [1, 10],
                "text": "A gadget comprising a widget.\n"
                " A gadget further comprising\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [2, 10],
                "text": "A gadget comprising a gizmo.\n"
                " A gadget further comprising\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [1, 11],
                "text": "A gadget comprising a widget.\n"
                " A gadget further comprising\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [2, 11],
                "text": "A gadget comprising a gizmo.\n"
                " A gadget further comprising\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [1, 3, 11],
                "text": "A gadget comprising a widget.\n"
                " The gadget further comprising a gizmo.\n"
                " A gadget further comprising\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [1, 12],
                "text": "A gadget comprising a widget.\n"
                " A gadget in which\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [2, 12],
                "text": "A gadget comprising a gizmo.\n"
                " A gadget in which\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [1, 3, 12],
                "text": "A gadget comprising a widget.\n"
                " The gadget further comprising a gizmo.\n"
                " A gadget in which\n"
                " A gadget, in which\n",
            },
        ],
        14: [
            {
                "parent_clm": [1],
                "text": "A gadget comprising a widget.\n A gadget in which\n",
            },
            {
                "parent_clm": [2],
                "text": "A gadget comprising a gizmo.\n A gadget in which\n",
            },
            {
                "parent_clm": [1, 3],
                "text": "A gadget comprising a widget.\n"
                " The gadget further comprising a gizmo.\n"
                " A gadget in which\n",
            },
            {
                "parent_clm": [2, 4],
                "text": "A gadget comprising a gizmo.\n"
                " The gadget further comprising a widget.\n"
                " A gadget in which\n",
            },
        ],
        15: [
            {
                "parent_clm": [1, 3],
                "text": "A gadget comprising a widget.\n"
                " The gadget further comprising a gizmo.\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [2, 4],
                "text": "A gadget comprising a gizmo.\n"
                " The gadget further comprising a widget.\n"
                " A gadget, in which\n",
            },
            {
                "parent_clm": [1],
                "text": "A gadget comprising a widget.\n A gadget, in which\n",
            },
            {
                "parent_clm": [2],
                "text": "A gadget comprising a gizmo.\n A gadget, in which\n",
            },
        ],
        16: [{"parent_clm": [200], "text": "A gadget in which\n"}],
    }

    def test_drop_claim_number(self):
        """Ensure that drop_claim_number works on each example in
        self.claims_pre_treat
        """
        for i in range(1, len(self.claims_clean) + 1):
            self.assertEqual(
                drop_claim_number(self.claims_pre_treat[i]),
                self.claims_no_number[i],
            )

    def test_drop_reference_numbers(self):
        """Ensure that drop_reference_numbers works on each example in
        self.claims_pre_treat
        """
        for i in range(1, len(self.claims_clean) + 1):
            self.assertEqual(
                drop_reference_numbers(self.claims_pre_treat[i]),
                self.claims_no_reference[i],
            )

    def test_drop_claim_number_and_drop_reference_numbers(self):
        """Ensure that drop_reference_numbers works on each example in
        self.claims_pre_treat
        """
        for i in range(1, len(self.claims_clean) + 1):
            self.assertEqual(
                drop_claim_number(
                    drop_reference_numbers(self.claims_pre_treat[i])
                ),
                self.claims_clean[i],
            )

    def test_get_parent_claim(self):
        """Ensure that get_parent_claim works for claims_clean to
        claims_get_parent_claims_and_text
        """
        all_claim_nums = list(self.claims_clean.keys())

        for i in range(1, len(self.claims_clean) + 1):
            self.assertEqual(
                get_parent_claim(
                    self.claims_clean[i],
                    all_claim_nums[: all_claim_nums.index(i)],
                ),
                self.claims_get_parent_claims_and_text[i],
            )

    def test_dependent_to_independent_claim(self):
        """Ensure that dependent_to_independent_claim works for claims_clean
        to claims_clean_no_dependent
        """
        independent_claims = dependent_to_independent_claim(self.claims_clean)
        for i in range(1, len(self.claims_clean) + 1):
            self.assertEqual(
                independent_claims[i], self.claims_clean_no_dependent[i]
            )

    def test_dependent_to_independent_claim_alternatives(self):
        """Ensure that dependent_to_independent_claim work for
        sample_claim_preambles_of_alternatives to
        claim_preambles_of_alternatives_no_dependents
        """
        claims_combined = copy.deepcopy(self.claims_clean)
        claims_combined.update(self.sample_claim_preambles_of_alternatives)

        claims_no_dependent_combined = copy.deepcopy(
            self.claims_clean_no_dependent
        )

        claims_no_dependent_combined.update(
            self.claim_preambles_of_alternatives_no_dependents
        )

        independent_claims = dependent_to_independent_claim(claims_combined)

        for i in range(1, len(claims_combined) + 1):
            self.assertEqual(
                independent_claims[i], claims_no_dependent_combined[i]
            )


if __name__ == "__main__":
    unittest.main()
