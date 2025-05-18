import os
import ctypes
import time

from pymicroscope.utils.pyroprocess import PyroProcess

from pymicroscope.acquisition.imageprovider import (
    ImageProvider,
)
from pymicroscope.acquisition.libepiphan.v2u_defs import *

V2U_TRUE = 1


class EpiphanImageProvider(ImageProvider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lib = None
        self.fg = None

    def setup_library(self):
        basedir = os.path.dirname(__file__)
        libpath = os.path.join(basedir, "libepiphan/libfrmgrab.dylib")
        self.lib = ctypes.CDLL(libpath)

        FrmGrabLocalPtr = ctypes.c_void_p

        self.lib.FrmGrabLocal_OpenAll.argtypes = [
            ctypes.POINTER(FrmGrabLocalPtr),
            ctypes.c_int,
        ]
        self.lib.FrmGrabLocal_OpenAll.restype = ctypes.c_int

        self.lib.FrmGrabLocal_Open.restype = FrmGrabLocalPtr

        self.lib.FrmGrab_Start.argtypes = [FrmGrabLocalPtr]
        self.lib.FrmGrab_Start.restype = ctypes.c_uint32

        self.lib.FrmGrab_Stop.argtypes = [FrmGrabLocalPtr]
        self.lib.FrmGrab_Stop.restype = None

        self.lib.FrmGrab_Close.argtypes = [FrmGrabLocalPtr]
        self.lib.FrmGrab_Close.restype = None

        self.lib.FrmGrab_Init()

    def setup(self):
        self.fg = self.lib.FrmGrabLocal_Open("local".encode("utf-8"))

    def capture_image(self) -> np.ndarray:
        pass

    def start(self):
        if self.lib.FrmGrab_Start(self.fg) == V2U_TRUE:
            print("Started")
        else:
            print("Error starting")

    def stop(self):
        self.lib.FrmGrab_Stop(self.fg)
        print("Stopped")

    def cleanup_library(self):
        if self.fg is not None:
            self.lib.FrmGrab_Close(self.fg)

        self.lib.FrmGrab_Deinit()

    def list_grabbers(self):
        FrmGrabLocalPtr = ctypes.c_void_p
        MAX_GRABS = 4

        # Allocate array of FrmGrabLocal* (c_void_p) initialized to NULL
        grabbers = (FrmGrabLocalPtr * MAX_GRABS)()

        # Call the function
        count = self.lib.FrmGrabLocal_OpenAll(grabbers, MAX_GRABS)
        print(f"Found {count} grabber(s).")
        for g in grabbers:
            print(g)


if __name__ == "__main__":
    print("Now")
    prov = EpiphanImageProvider(pyro_name="ca.dccmlab.imageprovider.epiphan")
    prov.setup()
    prov.start()

    #    time.sleep(1)

    prov.stop()
    prov.cleanup()
