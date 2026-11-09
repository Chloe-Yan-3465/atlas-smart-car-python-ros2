import unittest

from smartcar_core.decision import DecisionEngine
from smartcar_core.types import Detection, LaneResult


CFG = {"decision": {"detection_confidence": 0.35, "action_cooldown_s": 2.0, "lane_timeout_s": 0.3, "normal_rpm": 80, "crawl_rpm": 35, "turn_rpm": 70, "action_durations_s": {"turn_left": 0.5, "turn_right": 0.5, "turnaround": 1.0, "park": 1.2}}}


def det(name, confidence=0.9):
    classes = ("left", "right", "turnaround", "park", "person", "obstacle", "crosswalk")
    return Detection(classes.index(name), name, confidence, 1, 1, 20, 20)


class DecisionTests(unittest.TestCase):
    def setUp(self): self.engine = DecisionEngine(CFG)

    def test_emergency_has_highest_priority(self):
        lane = LaneResult(True, timestamp=10.0)
        action = self.engine.decide(lane, [det("left"), det("person")], 10.0)
        self.assertEqual(action.name, "stop"); self.assertTrue(action.emergency)

    def test_landmark_then_cooldown(self):
        lane = LaneResult(True, timestamp=10.0)
        self.assertEqual(self.engine.decide(lane, [det("left")], 10.0).name, "turn_left")
        self.assertEqual(self.engine.decide(lane, [det("left")], 10.1).name, "turn_left")
        self.assertEqual(self.engine.decide(LaneResult(True, timestamp=10.6), [det("left")], 10.6).name, "follow_lane")

    def test_crosswalk_crawls(self):
        action = self.engine.decide(LaneResult(True, timestamp=10.0), [det("crosswalk")], 10.0)
        self.assertEqual((action.name, action.speed_rpm), ("follow_lane", 35.0))

    def test_missing_or_stale_lane_stops(self):
        self.assertEqual(self.engine.decide(None, [], 10.0).name, "stop")
        action = self.engine.decide(LaneResult(True, timestamp=9.0), [], 10.0)
        self.assertTrue(action.emergency)


if __name__ == "__main__": unittest.main()

