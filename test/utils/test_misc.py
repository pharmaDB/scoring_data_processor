import unittest
from utils.misc import reorg_list_dict


class Test_utils_misc(unittest.TestCase):

    maxDiff = None

    def test_reorg_list_dict(self):
        a = [
            {"claim": "1", "text": "a"},
            {"claim": "2", "text": "b"},
            {"claim": "3", "text": "c"},
        ]
        b = {"1": "a", "2": "b", "3": "c"}

        self.assertEqual(reorg_list_dict(a, "claim", "text"), b)


if __name__ == "__main__":
    unittest.main()
