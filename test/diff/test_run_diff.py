import unittest
from diff.run_diff import rebuild_string
import copy


class Test_run_diff(unittest.TestCase):

    maxDiff = None

    super_text = [
        [0, "Morphine sulfate"],
        [-1, ","],
        [1, " is"],
        [0, " an opioid agonist"],
        [
            -1,
            ", is a fine white powder.  When exposed to air it gradually loses water of hydration, and darken",
        ],
        [
            1,
            ".  Morphine Sulfate Injection USP is available as a sterile, nonpyrogenic solution of morphine sulfate, free of antioxidants and preservative",
        ],
        [0, "s "],
        [-1, "o"],
        [1, "i"],
        [0, "n pr"],
        [
            -1,
            "olonged exposure to light. It is soluble in water and ethanol at room temperature. It is chemically designated a",
        ],
        [
            1,
            "e-filled syringes for intravenous and intramuscular administration.  Each 1 mL pre-filled syringe contains 2 mg, 4 mg, 5 mg, 8 mg or 10 mg of Morphine Sulfate USP in 1 mL total volume.\nThe chemical name i",
        ],
        [
            0,
            "s 7,8-Didehydro-4,5-epoxy-17-methyl-(5α,6α)-morphinan-3,6diol sulfate (2: 1) (salt), pentahydrate",
        ],
        [-1, ", with t"],
        [1, ".  T"],
        [0, "he "],
        [-1, "f"],
        [1, "m"],
        [0, "ol"],
        [-1, "lowing structural"],
        [1, "ecular weight is 758.83.  Its molecular"],
        [0, " formula"],
        [-1, ":\n"],
        [1, " is "],
        [0, "(C17H19NO3)2 • H2SO4 • 5H2O "],
        [-1, "          Molecular Weight is 758.83"],
        [1, "and it has the following chemical structure."],
        [0, "\nMorphine "],
        [-1, "S"],
        [1, "s"],
        [0, "ulfate "],
        [
            -1,
            "Injection, USP is a sterile, nonpyrogenic solution of Morphine Sulfate Injection, USP, free of antioxidants and preservatives.\nEach 1 mL syringe contains 2 mg, 4 mg, 5 mg, 8 mg or 10 mg of Morphine Sulfate, USP in 1 mL total volume with the following inactive ingredients: f",
        ],
        [
            1,
            "is a fine white powder. When exposed to air it gradually loses water of hydration, and darkens on prolonged exposure to light. It is soluble in water and ethanol at room temperature.\nThe inactive ingredients in Morphine Sulfate Injection, USP include:\nF",
        ],
        [0, "or the 2 "],
        [1, "mg/mL, 4 "],
        [0, "mg/mL and "],
        [-1, "4"],
        [1, "5"],
        [0, " mg/mL"],
        [-1, ","],
        [1, " products:"],
        [
            0,
            " 8.4 mg sodium chloride, 2.3 mg of sodium citrate, 0.74 mg of citric acid, 0.111 mg of edetate disodium, 0.053 mg of calcium chloride and water for injection.",
        ],
        [-1, "  "],
        [1, "\n"],
        [0, "For the"],
        [-1, " 5 mg/mL,"],
        [0, " 8 mg/mL and 10 mg/mL"],
        [-1, ","],
        [1, " products:"],
        [
            0,
            " 7.5 mg sodium chloride, 3.45 mg of sodium citrate, 1.11 mg of citric acid, 0.111 mg of edetate disodium, 0.053 mg of calcium chloride and water for injection.",
        ],
    ]

    def test_rebuild_string(self):
        text = [
            [0, "Morphine "],
            [-1, "s"],
            [1, "S"],
            [0, "ulfate "],
            [-1, "is an opioid ag"],
            [1, "Injecti"],
            [0, "on"],
            [1, " "],
            [0, "is"],
            [-1, "t"],
            [0, " indicated for the management of pain "],
            [-1, "not responsive to non-narcotic analgesics"],
            [
                1,
                "severe enough to require an opioid analgesic and for which alternative treatments are inadequate",
            ],
            [0, "."],
        ]
        orig_text = "Morphine Sulfate Injection is indicated for the management of pain severe enough to require an opioid analgesic and for which alternative treatments are inadequate."
        addition_list = [2, 5, 7, 12]
        rebuilt_str, rebuilt_list = rebuild_string(text, 2)
        self.assertEqual(orig_text, rebuilt_str)
        self.assertEqual(addition_list, rebuilt_list)

    def test_rebuild_string2(self):
        text = [
            [0, "Morphine Sulfate Injection"],
            [-1, ", USP"],
            [0, " is available in the following strengths for intravenous"],
            [1, " (IV)"],
            [0, " and intramuscular"],
            [1, " (IM)"],
            [
                0,
                " administration.\n2 mg/mL in 1 mL prefilled disposable syringe for IV or IM use.\n4 mg/mL in 1 mL prefilled disposable syringe for IV or IM use.\n5 mg/mL in 1 mL prefilled disposable syringe for IV or IM use.\n8 mg/mL in 1 mL prefilled disposable syringe for IV or IM use.\n10 mg/mL in 1 mL prefilled disposable syringe for IV or IM use.",
            ],
        ]
        orig_text = "Morphine Sulfate Injection is available in the following strengths for intravenous (IV) and intramuscular (IM) administration."
        addition_list = [3, 5]
        rebuilt_str, rebuilt_list = rebuild_string(text, 3)
        self.assertEqual(orig_text, rebuilt_str)
        self.assertEqual(addition_list, rebuilt_list)

    def test_rebuild_string3(self):
        orig_text = "Morphine sulfate is an opioid agonist.  Morphine Sulfate Injection USP is available as a sterile, nonpyrogenic solution of morphine sulfate, free of antioxidants and preservatives in pre-filled syringes for intravenous and intramuscular administration."

        addition_list = [2, 5, 8, 11]
        rebuilt_str, rebuilt_list = rebuild_string(self.super_text, 5)
        self.assertEqual(orig_text, rebuilt_str)
        self.assertEqual(addition_list, rebuilt_list)

    def test_rebuild_string4(self):
        orig_text = "Morphine Sulfate Injection USP is available as a sterile, nonpyrogenic solution of morphine sulfate, free of antioxidants and preservatives in pre-filled syringes for intravenous and intramuscular administration.  Each 1 mL pre-filled syringe contains 2 mg, 4 mg, 5 mg, 8 mg or 10 mg of Morphine Sulfate USP in 1 mL total volume.\nThe chemical name is 7,8-Didehydro-4,5-epoxy-17-methyl-(5α,6α)-morphinan-3,6diol sulfate (2: 1) (salt), pentahydrate."

        addition_list = [5, 8, 11, 14]
        rebuilt_str, rebuilt_list = rebuild_string(self.super_text, 11)

        print(rebuilt_str)

        self.assertEqual(orig_text, rebuilt_str)
        self.assertEqual(addition_list, rebuilt_list)


if __name__ == "__main__":
    unittest.main()
