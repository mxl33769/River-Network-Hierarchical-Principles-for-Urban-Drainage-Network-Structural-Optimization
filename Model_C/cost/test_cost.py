import unittest

from cost import total_budget, unit_cost


class CostTests(unittest.TestCase):
    def test_no_extrapolation(self):
        for mm in (150, 200, 250, 300, 1400, 304.799, 1371.601, 1523.999, 3657.601):
            self.assertEqual(unit_cost(mm), (None, None))

    def test_inclusive_boundaries(self):
        for mm in (304.8, 1371.6):
            self.assertEqual(unit_cost(mm)[0], "Eq. 5")
        for mm in (1524, 3657.6):
            self.assertEqual(unit_cost(mm)[0], "Eq. 6")

    def test_mm_to_inches(self):
        self.assertAlmostEqual(unit_cost(609.6)[1], 11.7 + 0.51 * 24 ** 1.38)

    def test_missing_cost_is_not_zero(self):
        self.assertIsNone(total_budget([{"replacement_cost_usd": 100}, {"replacement_cost_usd": None}]))
        self.assertEqual(total_budget([{"replacement_cost_usd": 100}, {"replacement_cost_usd": 50}]), 150)


if __name__ == "__main__":
    unittest.main()
