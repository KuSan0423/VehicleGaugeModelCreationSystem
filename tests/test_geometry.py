"""固定した既存値・左右鏡像・変則寸法・不正入力を検証する回帰テスト。"""
import math
import unittest
from rail_clearance.configuration import preset,PRESETS
from rail_clearance.geometry import dimensions,formation,point,polygons,separation,coupled,reference,tangent_gap
from rail_clearance.verification import building_margin,PROFILES

class GeometryTests(unittest.TestCase):
    def test_presets(self):
        expected=[([15,15],29),([15,11,15],40),([11.75,11,11.75],41)]
        for name,(spacings,length) in zip(PRESETS,expected):
            d=dimensions(preset(name))
            self.assertEqual([c['spacing'] for c in d['cars']],spacings)
            self.assertEqual(d['length'],length)
    def test_shared_nodes_and_mirror(self):
        c=preset(PRESETS[-1]);c['lengths_mm']=[16500,9200,13000]
        c['gaps_mm']=[1300,900];c['joint_left_mm']=[455,540];c['joint_right_mm']=[845,360]
        d=dimensions(c)
        for r in (0,100,300,2000):
            left,right=formation(d,r,1),formation(d,r,-1)
            for i,car in enumerate(d['cars']):
                self.assertLess(math.dist(point(left['poses'][i],car['a']),left['nodes'][i]),1e-9)
                self.assertLess(math.dist(point(left['poses'][i],car['b']),left['nodes'][i+1]),1e-9)
                self.assertAlmostEqual(left['poses'][i][0],right['poses'][i][0])
                self.assertAlmostEqual(left['poses'][i][1],-right['poses'][i][1])
    def test_known_15m_margins(self):
        d=dimensions(preset(PRESETS[0]));arr=formation(d,100)
        ps=polygons(d,arr,'gauge')
        self.assertAlmostEqual(tangent_gap(ps[0],ps[1],arr['equipment_poses'][0][2]),.77218,places=5)
        self.assertAlmostEqual(separation(ps[0],ps[1]),.770008704904,places=10)
        margin,_=building_margin(PROFILES['gauge'],-7,7,15,100)
        self.assertAlmostEqual(margin,.0669309057149,places=10)
    def test_known_coupled_margins(self):
        d=dimensions(preset(PRESETS[-1]))
        for other,kind,expected in [(d,'body',.235007792387),
                                    (reference(15),'body',.218709741476),
                                    (reference(15),'gauge',-.036239405211)]:
            for sign in (-1,1):
                a,b,ends=coupled(d,other,100,sign)
                self.assertAlmostEqual(math.dist(*ends),.5,places=9)
                p,q=polygons(d,a,kind),polygons(other,b,kind)
                self.assertAlmostEqual(min(separation(x,y) for x in p for y in q),expected,places=9)
    def test_invalid_values(self):
        for key,value in [('gaps_mm',[100,100]),('joint_left_mm',[0,1]),
                          ('lengths_mm',[float('nan'),10000,14000]),('radius_m',80),
                          ('outer_insets_mm',[99999,3000])]:
            c=preset(PRESETS[-1]);c[key]=value
            with self.assertRaises(ValueError):dimensions(c)

if __name__=='__main__':unittest.main()
