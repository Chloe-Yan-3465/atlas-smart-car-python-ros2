import unittest

import numpy as np

from smartcar_core.perception.lane import lane_from_mask, lane_mask
from smartcar_core.perception.yolo import decode_yolo, letterbox, scale_boxes


class PerceptionTests(unittest.TestCase):
    def test_lane_center_and_direction(self):
        mask = np.zeros((100, 200), np.uint8); mask[60:, 145:155] = 1
        result = lane_from_mask(mask, min_pixels=20)
        self.assertTrue(result.valid); self.assertGreater(result.steering, 0.3)

    def test_lane_logits(self):
        logits = np.zeros((1, 2, 10, 10), np.float32); logits[:, 1, :, 7:] = 1
        self.assertEqual(int(lane_mask(logits).sum()), 30)

    def test_letterbox_round_trip(self):
        image = np.zeros((360, 1280, 3), np.uint8)
        padded, ratio, pad = letterbox(image, 640)
        self.assertEqual(padded.shape, (640, 640, 3))
        original = np.array([[100, 50, 300, 200, 0.9, 0]], np.float32)
        encoded = original.copy(); encoded[:, [0, 2]] = encoded[:, [0, 2]] * ratio + pad[0]; encoded[:, [1, 3]] = encoded[:, [1, 3]] * ratio + pad[1]
        np.testing.assert_allclose(scale_boxes(encoded, ratio, pad, image.shape[:2])[:, :4], original[:, :4], atol=1e-4)

    def test_six_column_om_output(self):
        rows = np.array([[[1, 2, 3, 4, 0.9, 2], [1, 2, 3, 4, 0.1, 1]]], np.float32)
        self.assertEqual(decode_yolo(rows, 0.35, 0.45).shape, (1, 6))


if __name__ == "__main__": unittest.main()

