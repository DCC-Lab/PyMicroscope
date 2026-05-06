from pymicroscope.acquisition.epiphan.epiphanlibwrapper import (
    EpiphanLibraryWrapper,
    EpiphanFrameGrabber,
)

from pymicroscope.acquisition.epiphan.polygoncontroller import PolygonController
from pymicroscope.acquisition.epiphan.pyroservices import (
    EpiphanPyroService,
    VMSPyroService,
    PolygonPyroService,
)

# EpiphanImageProvider depends on mytk which isn't required by the new
# acquisition daemon. Import it lazily so the daemon runs even if mytk
# isn't installed.

try:
    from pymicroscope.acquisition.epiphan.epiphanimageprovider import EpiphanImageProvider
except ImportError:
    EpiphanImageProvider = None
