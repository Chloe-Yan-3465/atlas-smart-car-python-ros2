import unittest

from smartcar_core.chassis.protocol import CHECK_VALUE, decode_packet, encode_packet


class ProtocolTests(unittest.TestCase):
    def test_round_trip(self):
        packet = encode_packet((-80, -80, 80, 80), (110, 90))
        self.assertEqual(len(packet), 14)
        self.assertEqual(decode_packet(packet), (-80, -80, 80, 80, 110, 90))
        self.assertEqual(int.from_bytes(packet[-2:], "little", signed=True), CHECK_VALUE)

    def test_rejects_bad_ranges_and_packets(self):
        with self.assertRaises(ValueError): encode_packet((301, 0, 0, 0))
        with self.assertRaises(ValueError): decode_packet(b"short")


if __name__ == "__main__": unittest.main()

