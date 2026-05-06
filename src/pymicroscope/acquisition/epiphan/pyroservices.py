"""Pyro5-exposed wrappers for the Epiphan acquisition stack.

Three services are registered on the local daemon:

    ca.dccmlab.imageprovider.epiphan  -> EpiphanPyroService
    ca.dccmlab.hardware.vms           -> VMSPyroService
    ca.dccmlab.hardware.polygon       -> PolygonPyroService

Numpy frames are returned as ``(bytes, shape, dtype_str)`` so that Pyro5's
serpent serializer can ferry them across the wire without extra deps.
"""
from __future__ import annotations

import threading

import numpy as np
from Pyro5.api import expose

from pymicroscope.acquisition.epiphan.epiphanlibwrapper import (
    EpiphanFrameGrabber,
    V2U_GRABFRAME_FORMAT_RGB24,
)


def _grab_rgb_array(grabber: EpiphanFrameGrabber) -> np.ndarray | None:
    """Single-frame grab decoded into a numpy uint8 array of shape (H, W, 3)."""
    if grabber.device is None:
        return None
    frame = grabber.grab_frame(format=V2U_GRABFRAME_FORMAT_RGB24)
    return frame.to_numpy() if frame is not None else None


# ---- Pyro service wrappers -------------------------------------------------

@expose
class EpiphanPyroService:
    """Single-process image source. Owns the only ``EpiphanFrameGrabber`` -
    the device cannot be opened twice, so all consumers (local GUI + remote
    Pyro proxies) call through this object.
    """

    def __init__(self, grabber: EpiphanFrameGrabber):
        self._grabber = grabber
        self._lock = threading.Lock()
        self._streaming = False
        self._latest: np.ndarray | None = None

    def start_streaming(self):
        with self._lock:
            if not self._streaming:
                self._grabber.start_streaming()
                self._streaming = True

    def stop_streaming(self):
        with self._lock:
            if self._streaming:
                self._grabber.stop_streaming()
                self._streaming = False

    def is_streaming(self) -> bool:
        return self._streaming

    def grab(self):
        """Grab one frame and return ``(bytes, shape, dtype)`` for Pyro."""
        with self._lock:
            arr = _grab_rgb_array(self._grabber)
        if arr is None:
            return None
        self._latest = arr
        return arr.tobytes(), list(arr.shape), str(arr.dtype)

    def latest_frame(self):
        """Return the most recently grabbed frame without re-grabbing."""
        arr = self._latest
        if arr is None:
            return None
        return arr.tobytes(), list(arr.shape), str(arr.dtype)

    def grab_array(self) -> np.ndarray | None:
        """In-process callers (the local Tk GUI) bypass Pyro serialisation."""
        with self._lock:
            arr = _grab_rgb_array(self._grabber)
        if arr is not None:
            self._latest = arr
        return arr

    def device_info(self) -> dict:
        try:
            return {
                "serial_number": self._grabber.get_serial_number(),
                "product_name": self._grabber.get_product_name(),
                "location": self._grabber.get_location(),
            }
        except Exception as err:
            return {"error": str(err)}


@expose
class VMSPyroService:
    """Pyro facade over ``VMSController``. Exposes only the methods the GUI
    needs; raw ``send_command`` is intentionally not exposed."""

    def __init__(self, controller):
        self._c = controller

    def is_accessible(self) -> bool:
        return bool(getattr(self._c, "is_accessible", False))

    def build_info(self) -> str:
        try:
            return self._c.build_info()
        except Exception as err:
            return f"VMS: <unreadable: {err}>"

    @property
    def lines_per_frame(self) -> int:
        return self._c.lines_per_frame

    def set_lines_per_frame(self, value: int):
        self._c.lines_per_frame = value

    @property
    def lines_for_vsync(self) -> int:
        return self._c.lines_for_vsync

    def set_lines_for_vsync(self, value: int):
        self._c.lines_for_vsync = value

    @property
    def dac_start(self) -> int:
        return self._c.dac_start

    def set_dac_start(self, value: int):
        self._c.dac_start = value

    @property
    def dac_increment(self) -> int:
        return self._c.dac_increment

    def set_dac_increment(self, value: int):
        self._c.dac_increment = value

    def apply_settings(self, settings: dict):
        self._c.apply_settings(settings)


@expose
class PolygonPyroService:
    """Pyro facade over ``PolygonController``."""

    def __init__(self, controller):
        self._c = controller

    def is_accessible(self) -> bool:
        return bool(getattr(self._c, "is_accessible", False))

    def build_info(self) -> str:
        return self._c.build_info()

    @property
    def tmr1_reload(self) -> int:
        return self._c.tmr1_reload

    def set_tmr1_reload(self, value: int):
        self._c.tmr1_reload = value

    @property
    def polygon_rev_per_min(self) -> int:
        return self._c.polygon_rev_per_min

    def set_rpm(self, target_rpm: int):
        self._c.set_rpm(target_rpm)

    def enable_clock(self):
        self._c.enable_clock()

    def disable_clock(self):
        self._c.disable_clock()

    @property
    def clock_enabled(self) -> bool:
        return self._c.clock_enabled

    @staticmethod
    def rpm_for_tmr1(tmr1: int) -> int:
        from pymicroscope.acquisition.epiphan.polygoncontroller import PolygonController
        return PolygonController.rpm_for_tmr1(tmr1)

    @staticmethod
    def tmr1_for_rpm(rpm: int) -> int:
        from pymicroscope.acquisition.epiphan.polygoncontroller import PolygonController
        return PolygonController.tmr1_for_rpm(rpm)
