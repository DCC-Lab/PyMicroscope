import envtest  # setup environment for testing
from pymicroscope.acquisition.epiphan.epiphanlibwrapper import (
    EpiphanFrameGrabber,
    EpiphanLibraryWrapper,
    CapturedFrame,
    V2U_VideoMode,
    V2U_GrabParameters,
    V2URect,
    V2U_GRABFRAME_FORMAT_RGB24,
    V2U_GRABFRAME_FORMAT_Y8,
    V2U_TRUE,
)


class EpiphanFrameGrabberTestCase(envtest.CoreTestCase):
    """Exercise the EpiphanFrameGrabber class against a real PCIe card."""

    @classmethod
    def setUpClass(cls):
        EpiphanLibraryWrapper.setup_library()

    def setUp(self):
        super().setUp()
        self.fg = EpiphanFrameGrabber()
        self.fg.initialize_device()

    def tearDown(self):
        super().tearDown()
        try:
            self.fg.close()
        except Exception:
            pass

    def test010_create_without_initialize(self) -> None:
        fg = EpiphanFrameGrabber()
        self.assertIsNone(fg.device)

    def test020_initialize_device_opens_card(self) -> None:
        self.assertIsNotNone(self.fg.device)
        self.assertNotEqual(self.fg.device, 0)

    def test030_close_resets_device_to_none(self) -> None:
        self.fg.close()
        self.assertIsNone(self.fg.device)

    def test040_close_is_idempotent(self) -> None:
        self.fg.close()
        self.fg.close()  # must not raise

    def test050_re_initialize_after_close(self) -> None:
        self.fg.close()
        self.fg.initialize_device()
        self.assertIsNotNone(self.fg.device)

    def test060_get_serial_number_returns_string(self) -> None:
        sn = self.fg.get_serial_number()
        self.assertIsInstance(sn, str)
        self.assertGreater(len(sn), 0)

    def test070_get_product_name_returns_string(self) -> None:
        name = self.fg.get_product_name()
        self.assertIsInstance(name, str)
        self.assertGreater(len(name), 0)

    def test080_get_location_returns_string(self) -> None:
        loc = self.fg.get_location()
        self.assertIsInstance(loc, str)
        self.assertGreater(len(loc), 0)

    def test090_get_video_mode_returns_struct(self) -> None:
        mode = self.fg.get_video_mode()
        self.assertIsInstance(mode, V2U_VideoMode)
        self.assertGreaterEqual(mode.width, 0)
        self.assertGreaterEqual(mode.height, 0)

    def test100_detect_video_mode_returns_struct_or_none(self) -> None:
        mode = self.fg.detect_video_mode()
        # No source connected is acceptable; result must still be the right type
        self.assertTrue(mode is None or isinstance(mode, V2U_VideoMode))

    def test110_get_capture_params_returns_struct(self) -> None:
        params = self.fg.get_capture_params()
        self.assertIsInstance(params, V2U_GrabParameters)

    def test120_set_capture_params_round_trip(self) -> None:
        params = self.fg.get_capture_params()
        original_phase = params.phase
        self.fg.set_capture_params(params)  # must not raise
        again = self.fg.get_capture_params()
        self.assertEqual(again.phase, original_phase)

    def test130_start_stop_streaming(self) -> None:
        self.fg.start_streaming()
        self.fg.stop_streaming()  # must not raise

    def test140_grab_frame_with_no_source(self) -> None:
        """Without an active source, FrmGrab_Frame returns NULL : grab_frame returns None."""
        result = self.fg.grab_frame(format=V2U_GRABFRAME_FORMAT_RGB24)
        self.assertTrue(result is None or isinstance(result, CapturedFrame))

    def _has_active_source(self) -> bool:
        mode = self.fg.detect_video_mode()
        return mode is not None and mode.width > 0 and mode.height > 0

    def test150_grab_frame_returns_captured_frame_when_source_present(self) -> None:
        """When a source is connected, grab_frame must return a populated CapturedFrame."""
        if not self._has_active_source():
            self.skipTest("No video source connected")
        result = self.fg.grab_frame(format=V2U_GRABFRAME_FORMAT_RGB24)
        self.assertIsInstance(result, CapturedFrame)
        self.assertGreater(result.width, 0)
        self.assertGreater(result.height, 0)
        self.assertGreater(len(result.data), 0)

    def test160_grab_frame_y8_format(self) -> None:
        if not self._has_active_source():
            self.skipTest("No video source connected")
        result = self.fg.grab_frame(format=V2U_GRABFRAME_FORMAT_Y8)
        self.assertIsInstance(result, CapturedFrame)
        self.assertGreaterEqual(len(result.data), result.width * result.height)

    def test155_to_numpy_rgb24(self) -> None:
        if not self._has_active_source():
            self.skipTest("No video source connected")
        import numpy as np
        frame = self.fg.grab_frame(format=V2U_GRABFRAME_FORMAT_RGB24)
        arr = frame.to_numpy()
        self.assertIsInstance(arr, np.ndarray)
        self.assertEqual(arr.dtype, np.uint8)
        self.assertEqual(arr.ndim, 3)
        self.assertEqual(arr.shape[2], 3)
        self.assertEqual(arr.shape[0], frame.height)
        self.assertEqual(arr.shape[1], frame.width)

    def test165_to_numpy_y8(self) -> None:
        if not self._has_active_source():
            self.skipTest("No video source connected")
        import numpy as np
        frame = self.fg.grab_frame(format=V2U_GRABFRAME_FORMAT_Y8)
        arr = frame.to_numpy()
        self.assertIsInstance(arr, np.ndarray)
        self.assertEqual(arr.dtype, np.uint8)
        self.assertEqual(arr.ndim, 2)
        self.assertEqual(arr.shape, (frame.height, frame.width))

    def test170_grab_frame_with_crop(self) -> None:
        if not self._has_active_source():
            self.skipTest("No video source connected")
        crop = V2URect(x=0, y=0, width=100, height=100)
        result = self.fg.grab_frame(format=V2U_GRABFRAME_FORMAT_RGB24, crop=crop)
        if result is None:
            self.skipTest("Grabber refused crop on this source")
        self.assertIsInstance(result, CapturedFrame)
        self.assertEqual(result.width, 100)
        self.assertEqual(result.height, 100)

    def test180_context_manager_initializes_and_closes(self) -> None:
        fg = EpiphanFrameGrabber()
        with fg:
            self.assertIsNotNone(fg.device)
        self.assertIsNone(fg.device)


if __name__ == "__main__":
    envtest.main()
