import unittest

from smartcar_core.chassis import decode_packet
from smartcar_core.chassis.serial_controller import SerialController
from smartcar_core.types import ActionCommand


class FakeSerial:
    def __init__(self, *_args, **_kwargs): self.writes = []; self.closed = False
    def reset_input_buffer(self): pass
    def write(self, value): self.writes.append(value)
    def flush(self): pass
    def readline(self): return b"SUCC\n"
    def close(self): self.closed = True


class BrokenSerial(FakeSerial):
    def reset_input_buffer(self): raise OSError("disconnected")


class SerialTests(unittest.TestCase):
    def test_command_and_shutdown_stop(self):
        fake = FakeSerial()
        controller = SerialController("loop", serial_factory=lambda *_a, **_k: fake)
        status = controller.execute(ActionCommand("follow_lane", 80, 0.0))
        self.assertTrue(status.connected)
        self.assertEqual(decode_packet(fake.writes[0])[:4], (-80, -80, 80, 80))
        controller.close()
        self.assertEqual(decode_packet(fake.writes[-1])[:4], (0, 0, 0, 0))

    def test_reconnects_once(self):
        instances = [BrokenSerial(), FakeSerial()]
        controller = SerialController("loop", serial_factory=lambda *_a, **_k: instances.pop(0))
        self.assertTrue(controller.execute(ActionCommand("forward", 20)).connected)
        controller.close()


if __name__ == "__main__": unittest.main()

