import os
import ctypes

from pymicroscope.utils.pyroprocess import PyroProcess

from pymicroscope.acquisition.imageprovider import (
    ImageProvider,
    ImageProviderClient,
    DebugImageProvider,
    show_provider,
)


class EpiphanImageProvider(ImageProvider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        basedir = os.path.dirname(__file__)
        libpath = os.path.join(basedir, "libepiphan/libfrmgrab.dylib")
        self.lib = ctypes.CDLL(libpath)
