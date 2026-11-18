"""Budget accounting, source invariants and new diameter constraints."""
from pathlib import Path
import json
import math
import unittest
import numpy as np
from costs import CostDesign, rate, replacement
from swmm_io import Inp, parse_model

ROOT = Path(__file__).resolve().parent


class CostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.design = CostDesign((ROOT/'A.inp').read_text(), (ROOT/'C.inp').read_text(), json.loads((ROOT/'run.json').read_text()))

    def test_inches_and_full_new_component(self):
        self.assertAlmostEqual(rate(1.0), 11.7 + .51 * 12 ** 1.38)
        p = {'diameter': .5, 'length': 100., 'xs': ['p','CIRCULAR','.5','0','0','0','2']}
        self.assertEqual(replacement(p, .5), 0)
        self.assertAlmostEqual(replacement(p, 1.), 200 * (11.7 + .51*12**1.38))
        with self.assertRaises(ValueError):
            replacement(p, .4)

    def test_reference_budget(self):
        self.assertAlmostEqual(self.design.reference_cost, 228499.909526234, places=5)
        self.assertLess(abs(self.design.reference_cost-self.design.budget), .01)

    def test_zero_design_and_no_hydrologic_change(self):
        d = self.design
        x = np.zeros(len(d.ids), dtype=int)
        self.assertEqual(d.cost(x), 0)
        self.assertEqual(d.added_volume(x), 0)
        self.assertEqual(d.render(x), d.text)

    def test_repair_and_export_both_enforce_budget(self):
        np.random.seed(29)
        d = self.design
        for _ in range(20):
            x = d.repair(np.random.uniform(-2, 20, len(d.ids)))
            self.assertLessEqual(d.cost(x), d.budget+1e-8)
            self.assertLessEqual(np.count_nonzero(x), d.max_count)
            self.assertTrue(d.verify(d.render(x))['only_diameters_changed'])
        with self.assertRaises(ValueError):
            d.render(d.upper)

    def test_catalogue_clearance_and_extrapolation(self):
        d = self.design
        for options, audit in zip(d.choices, d.audit):
            self.assertLessEqual(max(options)*304.8, 2000+1e-6)
            self.assertLessEqual(max(options), audit['MaximumDiameterWithoutRimChange_ft']+1e-8)
            self.assertGreaterEqual(min(options), audit['OriginalDiameter_ft']-1e-8)
        self.assertGreater(rate(200/304.8), 0)


if __name__ == '__main__':
    unittest.main()
