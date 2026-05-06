import envtest  # setup environment for testing

import numpy as np

from pymicroscope.acquisition.epiphan.epiphanimageprovider import EpiphanImageProvider
from pymicroscope.acquisition.epiphan.epiphanlibwrapper import EpiphanLibraryWrapper


class EpiphanImageProviderTestCase(envtest.CoreTestCase):
    """Tests for EpiphanImageProvider against a real Epiphan card."""

    @classmethod
    def setUpClass(cls):
        EpiphanLibraryWrapper.setup_library()

    def setUp(self):
        super().setUp()
        self.prov = EpiphanImageProvider()

    def tearDown(self):
        super().tearDown()
        try:
            self.prov.stop()
        except Exception:
            pass
        try:
            self.prov.cleanup()
        except Exception:
            pass

    # ---- import / instantiation ----

    def test010_can_import(self) -> None:
        from pymicroscope.acquisition.epiphan.epiphanimageprovider import (
            EpiphanImageProvider as Cls,
        )
        self.assertIs(Cls, EpiphanImageProvider)

    def test020_instantiation_does_not_open_device(self) -> None:
        self.assertIsNotNone(self.prov.fg)
        self.assertIsNone(self.prov.fg.device)

    def test030_default_configuration(self) -> None:
        self.assertEqual(self.prov.channels, 3)
        self.assertGreater(self.prov.width, 0)
        self.assertGreater(self.prov.height, 0)
        self.assertGreater(self.prov.frame_rate, 0)

    # ---- setup / cleanup lifecycle ----

    def test040_setup_opens_device(self) -> None:
        self.prov.setup()
        self.assertIsNotNone(self.prov.fg.device)

    def test050_cleanup_after_setup_closes_device(self) -> None:
        self.prov.setup()
        self.prov.cleanup()
        self.assertFalse(hasattr(self.prov, "fg"))

    def test060_re_setup_after_cleanup(self) -> None:
        self.prov.setup()
        self.prov.cleanup()
        self.prov.fg = type(EpiphanImageProvider().fg)()  # rebuild grabber
        self.prov.setup()
        self.assertIsNotNone(self.prov.fg.device)

    # ---- streaming ----

    def test070_start_stop_streaming(self) -> None:
        self.prov.setup()
        self.prov.start()
        self.prov.stop()  # must not raise

    # ---- capture ----

    def _has_active_source(self) -> bool:
        mode = self.prov.fg.detect_video_mode()
        return mode is not None and mode.width > 0 and mode.height > 0

    def test080_capture_image_returns_ndarray_or_none(self) -> None:
        self.prov.setup()
        self.prov.start()
        img = self.prov.capture_image()
        self.prov.stop()
        # Accept either np.ndarray (with source) or None (no source)
        self.assertTrue(img is None or isinstance(img, np.ndarray))

    def test090_capture_image_shape_when_source_present(self) -> None:
        self.prov.setup()
        if not self._has_active_source():
            self.skipTest("No video source connected")
        self.prov.start()
        img = self.prov.capture_image()
        self.prov.stop()
        self.assertIsInstance(img, np.ndarray)
        self.assertEqual(img.dtype, np.uint8)
        self.assertEqual(img.ndim, 3)
        self.assertEqual(img.shape[2], 3)

    def test100_capture_image_without_setup_returns_none(self) -> None:
        """Without an open device, capture_image must not crash."""
        img = self.prov.capture_image()
        self.assertIsNone(img)

    # ---- configuration ----

    def test110_set_get_configuration(self) -> None:
        self.prov.set_configuration({"frame_rate": 15})
        self.assertEqual(self.prov.frame_rate, 15)
        cfg = self.prov.get_configuration()
        self.assertEqual(cfg["frame_rate"], 15)


if __name__ == "__main__":
    envtest.main()
