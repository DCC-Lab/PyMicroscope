from pymicroscope.acquisition.epiphan.epiphanlibwrapper import (
    EpiphanLibraryWrapper,
    EpiphanFrameGrabber,
)
# EpiphanImageProvider depends on mytk which is optional ; import lazily.
try:
    from pymicroscope.acquisition.epiphan.epiphanimageprovider import EpiphanImageProvider
except ImportError:
    EpiphanImageProvider = None
