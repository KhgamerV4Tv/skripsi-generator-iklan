import unittest

from api.copyright_check import classify_visual_matches


class CopyrightCheckTests(unittest.TestCase):
    def test_risk_bands_do_not_claim_legal_safety(self):
        self.assertEqual(classify_visual_matches(0)["code"], "low")
        self.assertEqual(classify_visual_matches(1)["code"], "review")
        self.assertEqual(classify_visual_matches(5)["code"], "high")

    def test_negative_match_count_is_rejected(self):
        with self.assertRaises(ValueError):
            classify_visual_matches(-1)


if __name__ == "__main__":
    unittest.main()
