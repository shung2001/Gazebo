"""Deterministic multi-component scenarios; no substitute for ROS transport tests."""
import unittest
from alatus_runtime.core import Tracker, Mission, proposal, gate, fresh

class PipelineTests(unittest.TestCase):
    def test_acquire_dropout_recover(self):
        tracker, mission = Tracker(), Mission()
        mission.request(True)
        for stamp in [1.0, 1.1, 1.2]:
            tracked = tracker.update(stamp, stamp, True, 0.9, 0.7, 0.5, 1)
            state = mission.step(tracked, True)
        self.assertEqual(state, 'TRACK_SHADOW')
        valid, _, _, correction = proposal(0.7, 0.5, state == 'TRACK_SHADOW')
        self.assertEqual(gate(valid, True, True, True, correction), (True, False))
        tracked = tracker.update(1.3, 1.3, False, 0.9, 0.7, 0.5, 1)
        self.assertEqual(mission.step(tracked, True), 'ABORT')
        for stamp in [1.4, 1.5, 1.6]:
            tracked = tracker.update(stamp, stamp, True, 0.9, 0.7, 0.5, 1)
        self.assertEqual(mission.step(tracked, True), 'ABORT')
        mission.request(False)
        mission.request(True)
        self.assertEqual(mission.step(tracked, True), 'TRACK_SHADOW')

    def test_silent_status_loss_and_clock_rewind(self):
        mission = Mission()
        mission.request(True)
        self.assertEqual(mission.step(True, fresh(1.0, 1.0)), 'TRACK_SHADOW')
        self.assertEqual(mission.step(True, fresh(1.6, 1.0)), 'ABORT')
        self.assertFalse(fresh(0.1, 1.0))
        self.assertEqual(gate(True, True, False, True, 0.1), (False, False))
