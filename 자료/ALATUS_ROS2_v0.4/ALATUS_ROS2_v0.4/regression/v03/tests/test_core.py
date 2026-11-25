import math
import unittest
from alatus_runtime.core import fresh, observation_ok, Tracker, Mission, proposal, gate

class CoreTests(unittest.TestCase):
    def test_freshness(self):
        for now, stamp, expected in [(1,1,True),(1.5,1,True),(1.501,1,False),(0.9,1,False),(2,float('nan'),False)]:
            self.assertEqual(fresh(now,stamp),expected)

    def test_observation_domain(self):
        for confidence,x,y in [(0.69,0.5,0.5),(1.1,0.5,0.5),(0.9,-0.1,0.5),(0.9,0.5,math.nan)]:
            self.assertFalse(observation_ok(True,confidence,x,y))
        self.assertFalse(observation_ok(False,1,0.5,0.5))

    def test_tracker_confirmation_and_duplicate(self):
        t=Tracker()
        self.assertFalse(t.update(1,1,True,0.9,0.5,0.5,1))
        self.assertFalse(t.update(1.1,1.1,True,0.9,0.5,0.5,1))
        self.assertTrue(t.update(1.2,1.2,True,0.9,0.5,0.5,1))
        self.assertFalse(t.update(1.2,1.2,True,0.9,0.5,0.5,1))

    def test_tracker_identity_gap_and_stale(self):
        t=Tracker()
        for s in [1,1.1,1.2]: t.update(s,s,True,0.9,0.5,0.5,1)
        self.assertFalse(t.update(1.3,1.3,True,0.9,0.5,0.5,2))
        self.assertFalse(t.update(3,3,True,0.9,0.5,0.5,2))
        self.assertFalse(t.update(4,3.1,True,0.9,0.5,0.5,2))

    def test_mission_abort_latch(self):
        m=Mission(); self.assertEqual(m.step(True,True),'IDLE')
        m.request(True); self.assertEqual(m.step(False,True),'SEARCH')
        self.assertEqual(m.step(True,True),'TRACK_SHADOW')
        self.assertEqual(m.step(False,True),'ABORT')
        self.assertFalse(m.request(True)); self.assertEqual(m.step(True,True),'ABORT')
        m.request(False); m.request(True); self.assertEqual(m.step(True,False),'ABORT')

    def test_proposal_bounds(self):
        for x in [0,0.25,0.5,0.75,1]:
            valid,ex,ey,c=proposal(x,0.5,True)
            self.assertTrue(valid); self.assertLessEqual(abs(c),0.2)
            self.assertAlmostEqual(ex,x-0.5)
        self.assertEqual(proposal(math.nan,0.5,True),(False,0,0,0))
        self.assertFalse(proposal(0.5,0.5,False)[0])

    def test_gate_never_enables(self):
        import itertools
        for flags in itertools.product([False,True], repeat=4):
            for c in [0,0.2,1,math.nan,math.inf]:
                inputs,control=gate(*flags,c)
                self.assertFalse(control)
                if inputs: self.assertTrue(all(flags) and abs(c)<=0.200001)

if __name__ == '__main__': unittest.main()
