import copy
import json
from pathlib import Path
import tempfile
import unittest
from configuration import preset,PRESETS,validate,save,load
from geometry import dimensions

class DimensionSolverTests(unittest.TestCase):
    def setUp(self):self.c=preset(PRESETS[-1])
    def test_old_presets(self):
        for name,expected in zip(PRESETS,([15000,15000],[15000,11000,15000],[11750,11000,11750])):
            c=preset(name)
            for key in ('car_count','bogie_spacings_mm','total_length_mm'):c.pop(key)
            self.assertEqual(validate(c)['bogie_spacings_mm'],expected)
    def test_body_lengths_from_bogies(self):
        self.c.update(lengths_mm=[None]*3,bogie_spacings_mm=[11750,11000,11750],total_length_mm=41000)
        result=validate(self.c)
        self.assertEqual(result['lengths_mm'],[14250,10000,14250])
        self.assertEqual(dimensions(self.c)['length'],41)
    def test_one_body_from_total(self):
        self.c.update(lengths_mm=[None,10000,14250],total_length_mm=42000)
        result=validate(self.c)
        self.assertEqual(result['lengths_mm'],[15250,10000,14250])
        self.assertEqual(result['bogie_spacings_mm'],[12750,11000,11750])
    def test_gap_from_total(self):
        self.c.update(gaps_mm=[None,1000],total_length_mm=41500)
        result=validate(self.c)
        self.assertEqual(result['gaps_mm'],[1500,1000])
        self.assertEqual(result['bogie_spacings_mm'],[12000,11250,11750])
    def test_insets_and_coupler(self):
        self.c.update(outer_insets_mm=[None,3000],coupler_mm=[None,250],
                      bogie_spacings_mm=[12000,None,None],total_length_mm=41000)
        result=validate(self.c)
        self.assertEqual(result['outer_insets_mm'],[2750,3000])
        self.assertEqual(result['coupler_mm'],[250,250])
    def test_unknown_fractions(self):
        self.c.update(joint_fractions=[None,None],bogie_spacings_mm=[11700,11000,11800])
        result=validate(self.c)
        self.assertAlmostEqual(result['joint_fractions'][0],.45)
        self.assertAlmostEqual(result['joint_fractions'][1],.45)
    def test_underconstrained(self):
        self.c.update(lengths_mm=[None,10000,None],total_length_mm=41000)
        with self.assertRaisesRegex(ValueError,'条件不足'):validate(self.c)
    def test_conflicting_total(self):
        self.c['total_length_mm']=40000
        with self.assertRaisesRegex(ValueError,'矛盾'):validate(self.c)
    def test_conflicting_spacing(self):
        self.c['bogie_spacings_mm']=[12000,None,None]
        with self.assertRaisesRegex(ValueError,'矛盾'):validate(self.c)
    def test_unphysical_solution(self):
        self.c.update(lengths_mm=[None,10000,14250],total_length_mm=27000)
        with self.assertRaisesRegex(ValueError,'2,000mm'):validate(self.c)
    def test_inactive_blanks(self):
        c=preset(PRESETS[0]);c['coupler_mm']=[None,None];c['outer_insets_mm']=[None,None]
        self.assertEqual(validate(c)['total_length_mm'],29000)
    def test_roundtrip_preserves_blank_constraints(self):
        self.c.update(lengths_mm=[None,10000,14250],total_length_mm=41000)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'config.json';save(self.c,path);result=load(path)
        self.assertIsNone(result['lengths_mm'][0])
        self.assertIsNone(result['bogie_spacings_mm'][0])
        self.assertEqual(result['total_length_mm'],41000)
    def test_all_dimension_unknowns(self):
        for key in ('lengths_mm','bogie_spacings_mm','gaps_mm','joint_fractions','outer_insets_mm','coupler_mm'):
            self.c[key]=[None]*len(self.c[key])
        with self.assertRaisesRegex(ValueError,'条件不足'):validate(self.c)

if __name__=='__main__':unittest.main()
