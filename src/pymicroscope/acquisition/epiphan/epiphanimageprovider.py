import os
import ctypes
import time
from ctypes import byref, POINTER, cast

from pymicroscope.utils.pyroprocess import PyroProcess

from pymicroscope.acquisition.imageprovider import (
    ImageProvider,
)
from pymicroscope.acquisition.libepiphan.epiphanlibwrapper import *


class EpiphanImageProvider(ImageProvider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fg = None

    def setup(self):
        self.fg = EpiphanFrameGrabber()

    def cleanup(self):
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
