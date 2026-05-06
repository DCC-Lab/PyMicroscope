"""Unit tests for PolygonController serial framing.

These run on any platform: the test substitutes a fake serial port so no
hardware is required.
"""
import struct
from unittest.mock import MagicMock

import envtest  # noqa: F401  -- adds src/ to sys.path

from pymicroscope.acquisition.epiphan.polygoncontroller import (
    PolygonController,
    TMR1_MIN,
    TMR1_MAX,
)


class FakeSerial:
    """Minimal stand-in for ``serial.Serial`` that records writes and yields
    pre-programmed reads."""

    def __init__(self, scripted_responses=None):
        self.writes = []
        self._reads = list(scripted_responses or [])
        self.flushed = 0

    def write(self, data):
        self.writes.append(bytes(data))
        return len(data)

    def flush(self):
        self.flushed += 1

    def read(self, n):
        if not self._reads:
            return b""
        chunk = self._reads.pop(0)
        return chunk[:n]

    def close(self):
        pass


class PolygonControllerTestCase(envtest.CoreTestCase):
    def setUp(self):
        super().setUp()
        self.ctl = PolygonController(serial_path="/dev/null-fake")

    def _attach_fake(self, responses=None):
        fake = FakeSerial(scripted_responses=responses)
        self.ctl.port = fake
        self.ctl.is_accessible = True
        return fake

    def test_write_tmr1_reload_frames_correctly(self):
        fake = self._attach_fake()
        self.ctl.tmr1_reload = 60327
        # Opcode 0x7D + big-endian 16-bit value
        expected = struct.pack(">bH", 0x7D, 60327)
        self.assertEqual(fake.writes[-1], expected)

    def test_tmr1_reload_rejects_out_of_range(self):
        self._attach_fake()
        with self.assertRaises(ValueError):
            self.ctl.tmr1_reload = TMR1_MIN - 1
        with self.assertRaises(ValueError):
            self.ctl.tmr1_reload = TMR1_MAX + 1

    def test_read_tmr1_reload_unpacks_response(self):
        fake = self._attach_fake(responses=[struct.pack(">H", 60327)])
        value = self.ctl.tmr1_reload
        self.assertEqual(value, 60327)
        self.assertEqual(fake.writes[-1], struct.pack(">b", 0x75))

    def test_enable_and_disable_clock_send_correct_opcodes(self):
        fake = self._attach_fake()
        self.ctl.enable_clock()
        self.assertEqual(fake.writes[-1], struct.pack(">b", 0x70))
        self.assertTrue(self.ctl.clock_enabled)
        self.ctl.disable_clock()
        self.assertEqual(fake.writes[-1], struct.pack(">b", 0x71))
        self.assertFalse(self.ctl.clock_enabled)

    def test_rpm_round_trip(self):
        # Spot-check: 28800 RPM corresponds to TMR1 ≈ 60327 (matches MATLAB preset)
        tmr1 = PolygonController.tmr1_for_rpm(28800)
        self.assertAlmostEqual(tmr1, 60327, delta=1)
        self.assertAlmostEqual(
            PolygonController.rpm_for_tmr1(tmr1), 28800, delta=10
        )


if __name__ == "__main__":
    envtest.main()
