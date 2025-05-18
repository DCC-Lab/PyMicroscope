import os
import ctypes
import time
from ctypes import byref, POINTER, cast

import numpy as np

from pymicroscope.utils.pyroprocess import PyroProcess

from pymicroscope.acquisition.imageprovider import (
    ImageProvider,
)
from pymicroscope.acquisition.epiphan import EpiphanFrameGrabber


class EpiphanImageProvider(ImageProvider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fg: EpiphanFrameGrabber = EpiphanFrameGrabber()

    def setup(self):
        self.fg.initialize_device()

    def cleanup(self):
        self.fg.shutdown_device()
        del self.fg

    def start(self):
        self.fg.start_streaming()

    def stop(self):
        self.fg.stop_streaming()

    def capture_image(self) -> np.ndarray:
        return self.fg.grab_frame()


if __name__ == "__main__":
    prov = EpiphanImageProvider(pyro_name="ca.dccmlab.imageprovider.epiphan")
    prov.setup()
    prov.start()

    #    time.sleep(1)

    prov.stop()
    prov.cleanup()
