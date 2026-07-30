import unittest

from utils.evaluation import classify_quality_score, parse_quality_score


class EvaluationTests(unittest.TestCase):
    def test_parse_quality_score(self):
        self.assertEqual(parse_quality_score("SKOR KELAYAKAN: 84\nANALISIS PAKAR: ..."), 84)

    def test_invalid_or_missing_score(self):
        self.assertIsNone(parse_quality_score("SKOR KELAYAKAN: 101"))
        self.assertIsNone(parse_quality_score("Tidak ada skor"))

    def test_thesis_thresholds(self):
        self.assertEqual(classify_quality_score(85)["code"], "pass")
        self.assertEqual(classify_quality_score(70)["code"], "minor")
        self.assertEqual(classify_quality_score(69)["code"], "revise")


if __name__ == "__main__":
    unittest.main()
