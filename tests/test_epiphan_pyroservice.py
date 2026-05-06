"""Tests for EpiphanPyroService.

Exercises the in-process side of the Pyro service (no Pyro daemon). The
service wraps an EpiphanImageProvider, which itself wraps EpiphanFrameGrabber.
"""
import envtest

import numpy as np

from pymicroscope.acquisition.epiphan.epiphanimageprovider import EpiphanImageProvider
from pymicroscope.acquisition.epiphan.pyroservices import EpiphanPyroService


class EpiphanPyroServiceTestCase(envtest.CoreTestCase):

    def setUp(self):
        super().setUp()
        self.provider = EpiphanImageProvider()
        self.provider.setup()
        self.service = EpiphanPyroService(self.provider)

    def tearDown(self):
        super().tearDown()
        try:
            self.service.stop_streaming()
        except Exception:
            pass
        try:
            self.provider.cleanup()
        except Exception:
            pass

    def test010_create(self) -> None:
        self.assertIsNotNone(self.service)

    def test020_initially_not_streaming(self) -> None:
        self.assertFalse(self.service.is_streaming())

    def test030_start_streaming_sets_flag(self) -> None:
        self.service.start_streaming()
        self.assertTrue(self.service.is_streaming())

    def test040_double_start_is_idempotent(self) -> None:
        self.service.start_streaming()
        self.service.start_streaming()  # must not raise
        self.assertTrue(self.service.is_streaming())

    def test050_stop_streaming_clears_flag(self) -> None:
        self.service.start_streaming()
        self.service.stop_streaming()
        self.assertFalse(self.service.is_streaming())

    def test060_double_stop_is_idempotent(self) -> None:
        self.service.stop_streaming()
        self.service.stop_streaming()  # must not raise

    def test070_device_info_keys(self) -> None:
        info = self.service.device_info()
        self.assertIsInstance(info, dict)
        self.assertNotIn("error", info)
        for key in ("serial_number", "product_name", "location"):
            self.assertIn(key, info)

    def test080_grab_array_returns_ndarray_or_none(self) -> None:
        self.service.start_streaming()
        arr = self.service.grab_array()
        self.service.stop_streaming()
        self.assertTrue(arr is None or isinstance(arr, np.ndarray))

    def test090_grab_returns_pyro_tuple_or_none(self) -> None:
        self.service.start_streaming()
        result = self.service.grab()
        self.service.stop_streaming()
        if result is None:
            return  # no source connected
        data, shape, dtype = result
        self.assertIsInstance(data, (bytes, bytearray))
        self.assertIsInstance(shape, list)
        self.assertEqual(dtype, "uint8")

    def test100_latest_frame_after_grab(self) -> None:
        self.service.start_streaming()
        first = self.service.grab()
        latest = self.service.latest_frame()
        self.service.stop_streaming()
        if first is None:
            self.assertIsNone(latest)
        else:
            self.assertIsNotNone(latest)
            self.assertEqual(latest[1], first[1])  # same shape


if __name__ == "__main__":
    envtest.main()
