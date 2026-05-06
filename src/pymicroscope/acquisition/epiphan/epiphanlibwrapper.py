"""
This is a standalone file to import and use the Epiphan acquisition card.  It
must not depend on anything outside of its directory.



"""

from ctypes import (
    Structure,
    c_uint16,
    c_uint32,
    byref,
    POINTER,
    CFUNCTYPE,
    c_char_p,
    c_int,
    c_double,
    c_void_p,
)
import ctypes
import os

V2U_TRUE = 1
V2U_FALSE = 0

# Validity flags
V2U_FLAG_VALID_HSHIFT = 0x0001
V2U_FLAG_VALID_PHASE = 0x0002
V2U_FLAG_VALID_OFFSETGAIN = 0x0004
V2U_FLAG_VALID_VSHIFT = 0x0008
V2U_FLAG_VALID_PLLSHIFT = 0x0010
V2U_FLAG_VALID_GRABFLAGS = 0x0020

# Grab flags
V2U_GRAB_BMP_BOTTOM_UP = 0x10000
V2U_GRAB_PREFER_WIDE_MODE = 0x20000

# Ranges
V2U_MIN_PHASE = 0
V2U_MAX_PHASE = 31
V2U_MIN_GAIN = 0
V2U_MAX_GAIN = 255
V2U_MIN_OFFSET = 0
V2U_MAX_OFFSET = 63

# PS/2 Addresses
V2U_PS2ADDR_KEYBOARD = 0x01
V2U_PS2ADDR_MOUSE = 0x02

# String sizes
V2U_SN_BUFSIZ = 32
V2U_CUSTOM_VIDEOMODE_COUNT = 8
V2U_USERDATA_LEN = 8

# Grab frame flags
V2U_GRABFRAME_RESERVED = 0x0F000000
V2U_GRABFRAME_FLAGS_MASK = 0xF0000000
V2U_GRABFRAME_BOTTOM_UP_FLAG = 0x80000000
V2U_GRABFRAME_KEYFRAME_FLAG = 0x40000000
V2U_GRABFRAME_ADDR_IS_PHYS = 0x20000000

# Rotation
V2U_GRABFRAME_ROTATION_MASK = 0x00300000
V2U_GRABFRAME_ROTATION_NONE = 0x00000000
V2U_GRABFRAME_ROTATION_LEFT90 = 0x00100000
V2U_GRABFRAME_ROTATION_RIGHT90 = 0x00200000
V2U_GRABFRAME_ROTATION_180 = 0x00300000

# Scaling
V2U_GRABFRAME_SCALE_MASK = 0x000F0000
V2U_GRABFRAME_SCALE_NEAREST = 0x00010000
V2U_GRABFRAME_SCALE_AVERAGE = 0x00020000
V2U_GRABFRAME_SCALE_FAST_BILINEAR = 0x00030000
V2U_GRABFRAME_SCALE_BILINEAR = 0x00040000
V2U_GRABFRAME_SCALE_BICUBIC = 0x00050000
V2U_GRABFRAME_SCALE_EXPERIMENTAL = 0x00060000
V2U_GRABFRAME_SCALE_POINT = 0x00070000
V2U_GRABFRAME_SCALE_AREA = 0x00080000
V2U_GRABFRAME_SCALE_BICUBLIN = 0x00090000
V2U_GRABFRAME_SCALE_SINC = 0x000A0000
V2U_GRABFRAME_SCALE_LANCZOS = 0x000B0000
V2U_GRABFRAME_SCALE_SPLINE = 0x000C0000
V2U_GRABFRAME_SCALE_HW = 0x000D0000
V2U_GRABFRAME_SCALE_MAX_MODE = V2U_GRABFRAME_SCALE_HW

# Video mode type flags (v2u_defs.h)
VIDEOMODE_TYPE_VALID = 0x01
VIDEOMODE_TYPE_ENABLED = 0x02
VIDEOMODE_TYPE_SUPPORTED = 0x04
VIDEOMODE_TYPE_DUALLINK = 0x08
VIDEOMODE_TYPE_DIGITAL = 0x10
VIDEOMODE_TYPE_INTERLACED = 0x20
VIDEOMODE_TYPE_HSYNCPOSITIVE = 0x40
VIDEOMODE_TYPE_VSYNCPOSITIVE = 0x80

# Pixel formats
V2U_GRABFRAME_FORMAT_MASK = 0x0000FFFF
V2U_GRABFRAME_FORMAT_RGB_MASK = 0x0000001F
V2U_GRABFRAME_FORMAT_RGB4 = 0x00000004
V2U_GRABFRAME_FORMAT_RGB8 = 0x00000008
V2U_GRABFRAME_FORMAT_RGB16 = 0x00000010
V2U_GRABFRAME_FORMAT_RGB24 = 0x00000018
V2U_GRABFRAME_FORMAT_YUY2 = 0x00000100
V2U_GRABFRAME_FORMAT_YV12 = 0x00000200
V2U_GRABFRAME_FORMAT_2VUY = 0x00000300
V2U_GRABFRAME_FORMAT_BGR16 = 0x00000400
V2U_GRABFRAME_FORMAT_Y8 = 0x00000500
V2U_GRABFRAME_FORMAT_CRGB24 = 0x00000600
V2U_GRABFRAME_FORMAT_CYUY2 = 0x00000700
V2U_GRABFRAME_FORMAT_BGR24 = 0x00000800
V2U_GRABFRAME_FORMAT_CBGR24 = 0x00000900
V2U_GRABFRAME_FORMAT_I420 = 0x00000A00
V2U_GRABFRAME_FORMAT_ARGB32 = 0x00000B00
V2U_GRABFRAME_FORMAT_NV12 = 0x00000C00
V2U_GRABFRAME_FORMAT_C2VUY = 0x00000D00


from ctypes import (
    Structure,
    Union,
    c_int8,
    c_uint8,
    c_int16,
    c_uint16,
    c_int32,
    c_uint32,
    c_int64,
    c_uint64,
    c_char,
    POINTER,
)

FrmGrabLocalPtr = ctypes.c_void_p
FrmGrabAuthProc = ctypes.CFUNCTYPE(
    ctypes.c_int,  # return type: V2U_BOOL
    ctypes.c_char_p,  # user
    ctypes.c_char_p,  # pass
    ctypes.c_void_p,  # param
)

# Define function pointer types
FrmGrabMemAlloc = CFUNCTYPE(c_void_p, c_void_p, c_uint32)
FrmGrabMemFree = CFUNCTYPE(None, c_void_p, c_void_p)


# Define the structure
class FrmGrabMemCB(Structure):
    _fields_ = [
        ("alloc", FrmGrabMemAlloc),
        ("free", FrmGrabMemFree),
    ]


class FrmGrabNetStat(Structure):
    _fields_ = [
        ("bytesSent", c_uint64),
        ("bytesReceived", c_uint64),
    ]


class V2USize(Structure):
    _pack_ = 1
    _fields_ = [("width", c_int32), ("height", c_int32)]


class V2URect(Structure):
    _pack_ = 1
    _fields_ = [("x", c_int32), ("y", c_int32), ("width", c_int32), ("height", c_int32)]


class V2UStrUcs2(Structure):
    _pack_ = 1
    _fields_ = [
        ("buffer", POINTER(c_uint16)),  # UCS-2 (UTF-16)
        ("len", c_uint32),
        ("maxlen", c_uint32),
    ]


class V2U_VideoMode(Structure):
    _pack_ = 1
    _fields_ = [("width", c_int32), ("height", c_int32), ("vfreq", c_int32)]


class V2U_GrabFrame2(Structure):
    _pack_ = 1
    _fields_ = [
        ("pixbuf", c_void_p),
        ("pixbuflen", c_uint32),
        ("palette", c_uint32),
        ("crop", V2URect),
        ("mode", V2U_VideoMode),
        ("imagelen", c_uint32),
        ("retcode", c_int32),
    ]


class V2U_GrabParameters(Structure):
    _pack_ = 1
    _fields_ = [
        ("flags", c_uint32),
        ("hshift", c_int32),
        ("phase", c_uint8),
        ("gain_r", c_uint8),
        ("gain_g", c_uint8),
        ("gain_b", c_uint8),
        ("offset_r", c_uint8),
        ("offset_g", c_uint8),
        ("offset_b", c_uint8),
        ("reserved", c_uint8),
        ("vshift", c_int32),
        ("pllshift", c_int32),
        ("grab_flags", c_uint32),
        ("grab_flags_mask", c_uint32),
    ]


class V2U_SendPS2(Structure):
    _pack_ = 1
    _fields_ = [("addr", c_int16), ("len", c_int16), ("buf", c_uint8 * 64)]


class V2U_GetSN(Structure):
    _pack_ = 1
    _fields_ = [("sn", c_char * 32)]


class V2UVideoModeDescr(Structure):
    _pack_ = 1
    _fields_ = [
        ("VerFrequency", c_uint32),
        ("HorAddrTime", c_uint16),
        ("HorFrontPorch", c_uint16),
        ("HorSyncTime", c_uint16),
        ("HorBackPorch", c_uint16),
        ("VerAddrTime", c_uint16),
        ("VerFrontPorch", c_uint16),
        ("VerSyncTime", c_uint16),
        ("VerBackPorch", c_uint16),
        ("Type", c_uint32),
    ]


class V2UVGAMode(Structure):
    _pack_ = 1
    _fields_ = [("idx", c_int32), ("vesa_mode", V2UVideoModeDescr)]


class V2UVersion(Structure):
    _pack_ = 1
    _fields_ = [
        ("major", c_int32),
        ("minor", c_int32),
        ("micro", c_int32),
        ("nano", c_int32),
    ]


class V2UAdjRange(Structure):
    _pack_ = 1
    _fields_ = [
        ("flags", c_uint32),
        ("valid_flags", c_uint32),
        ("hshift_min", c_int16),
        ("hshift_max", c_int16),
        ("phase_min", c_int16),
        ("phase_max", c_int16),
        ("offset_min", c_int16),
        ("offset_max", c_int16),
        ("gain_min", c_int16),
        ("gain_max", c_int16),
        ("vshift_min", c_int16),
        ("vshift_max", c_int16),
        ("pll_min", c_int16),
        ("pll_max", c_int16),
    ]


class EpiphanLibraryWrapper:
    lib = None
    is_functional = False

    @classmethod
    def list_grabbers(cls):
        MAX_GRABS = 4

        # Allocate array of FrmGrabLocal* (c_void_p) initialized to NULL
        grabbers = (FrmGrabLocalPtr * MAX_GRABS)()

        # Call the function
        count = cls.lib.FrmGrabLocal_OpenAll(grabbers, MAX_GRABS)
        print(f"Found {count} grabber(s).")
        for g in grabbers:
            print(g)

    @classmethod
    def setup_library(cls, libpath=None):
        if cls.lib is not None:
            return

        if libpath is None:
            basedir = os.path.dirname(__file__)
            libpath = os.path.join(basedir, "libfrmgrab.dylib")

        cls.lib = ctypes.CDLL(libpath)

        try:
            FrmGrabberPtr = ctypes.c_void_p

            # Init/Deinit
            cls.lib.FrmGrab_Init.argtypes = []
            cls.lib.FrmGrab_Init.restype = None

            cls.lib.FrmGrab_Deinit.argtypes = []
            cls.lib.FrmGrab_Deinit.restype = None

            cls.lib.FrmGrabNet_Init.argtypes = []
            cls.lib.FrmGrabNet_Init.restype = None

            cls.lib.FrmGrabNet_Deinit.argtypes = []
            cls.lib.FrmGrabNet_Deinit.restype = None

            # Local grabber access
            cls.lib.FrmGrabLocal_Open.argtypes = []
            cls.lib.FrmGrabLocal_Open.restype = FrmGrabberPtr

            cls.lib.FrmGrabLocal_OpenSN.argtypes = [c_char_p]
            cls.lib.FrmGrabLocal_OpenSN.restype = FrmGrabberPtr

            cls.lib.FrmGrabLocal_Count.argtypes = []
            cls.lib.FrmGrabLocal_Count.restype = ctypes.c_int

            cls.lib.FrmGrabLocal_OpenAll.argtypes = [POINTER(FrmGrabberPtr), c_int]
            cls.lib.FrmGrabLocal_OpenAll.restype = c_int

            # Network
            cls.lib.FrmGrabNet_Open.argtypes = []
            cls.lib.FrmGrabNet_Open.restype = FrmGrabberPtr

            cls.lib.FrmGrabNet_OpenSN.argtypes = [c_char_p]
            cls.lib.FrmGrabNet_OpenSN.restype = FrmGrabberPtr

            cls.lib.FrmGrabNet_OpenLocation.argtypes = [c_char_p]
            cls.lib.FrmGrabNet_OpenLocation.restype = FrmGrabberPtr

            cls.lib.FrmGrabNet_OpenAddress.argtypes = [c_uint32, c_uint16]
            cls.lib.FrmGrabNet_OpenAddress.restype = FrmGrabberPtr

            cls.lib.FrmGrabNet_OpenAddress2.argtypes = [
                c_uint32,
                c_uint16,
                FrmGrabAuthProc,
                c_void_p,
                POINTER(c_int),
            ]
            cls.lib.FrmGrabNet_OpenAddress2.restype = FrmGrabberPtr

            cls.lib.FrmGrabNet_IsProtected.argtypes = [FrmGrabberPtr]
            cls.lib.FrmGrabNet_IsProtected.restype = c_int

            cls.lib.FrmGrabNet_Auth.argtypes = [
                FrmGrabberPtr,
                FrmGrabAuthProc,
                c_void_p,
            ]
            cls.lib.FrmGrabNet_Auth.restype = c_int

            cls.lib.FrmGrabNet_Auth2.argtypes = [FrmGrabberPtr, c_char_p, c_char_p]
            cls.lib.FrmGrabNet_Auth2.restype = c_int

            cls.lib.FrmGrabNet_GetStat.argtypes = [
                FrmGrabberPtr,
                POINTER(FrmGrabNetStat),
            ]
            cls.lib.FrmGrabNet_GetStat.restype = c_int

            cls.lib.FrmGrabNet_GetRemoteAddr.argtypes = [
                FrmGrabberPtr,
                c_void_p,
            ]  # struct sockaddr_in
            cls.lib.FrmGrabNet_GetRemoteAddr.restype = c_int

            cls.lib.FrmGrabNet_IsAlive.argtypes = [FrmGrabberPtr]
            cls.lib.FrmGrabNet_IsAlive.restype = c_int

            cls.lib.FrmGrabNet_SetAutoReconnect.argtypes = [FrmGrabberPtr, c_int]
            cls.lib.FrmGrabNet_SetAutoReconnect.restype = c_int

            # Generic Open/Dup/Close
            cls.lib.FrmGrab_Open.argtypes = [c_char_p]
            cls.lib.FrmGrab_Open.restype = FrmGrabberPtr

            cls.lib.FrmGrab_Dup.argtypes = [FrmGrabberPtr]
            cls.lib.FrmGrab_Dup.restype = FrmGrabberPtr

            cls.lib.FrmGrab_Close.argtypes = [FrmGrabberPtr]
            cls.lib.FrmGrab_Close.restype = None

            cls.lib.FrmGrab_GetSN.argtypes = [FrmGrabberPtr]
            cls.lib.FrmGrab_GetSN.restype = c_char_p

            cls.lib.FrmGrab_GetProductId.argtypes = [FrmGrabberPtr]
            cls.lib.FrmGrab_GetProductId.restype = c_int

            cls.lib.FrmGrab_GetProductName.argtypes = [FrmGrabberPtr]
            cls.lib.FrmGrab_GetProductName.restype = c_char_p

            cls.lib.FrmGrab_GetLocation.argtypes = [FrmGrabberPtr]
            cls.lib.FrmGrab_GetLocation.restype = c_char_p

            cls.lib.FrmGrab_GetCaps.argtypes = [FrmGrabberPtr]
            cls.lib.FrmGrab_GetCaps.restype = c_uint32

            # Video mode / params / properties
            cls.lib.FrmGrab_GetVideoMode.argtypes = [FrmGrabberPtr, c_void_p]
            cls.lib.FrmGrab_GetVideoMode.restype = None

            cls.lib.FrmGrab_DetectVideoMode.argtypes = [FrmGrabberPtr, c_void_p]
            cls.lib.FrmGrab_DetectVideoMode.restype = c_int

            cls.lib.FrmGrab_GetGrabParams.argtypes = [FrmGrabberPtr, c_void_p]
            cls.lib.FrmGrab_GetGrabParams.restype = c_int

            cls.lib.FrmGrab_GetGrabParams2.argtypes = [
                FrmGrabberPtr,
                c_void_p,
                c_void_p,
            ]
            cls.lib.FrmGrab_GetGrabParams2.restype = c_int

            cls.lib.FrmGrab_SetGrabParams.argtypes = [FrmGrabberPtr, c_void_p]
            cls.lib.FrmGrab_SetGrabParams.restype = c_int

            cls.lib.FrmGrab_GetProperty.argtypes = [FrmGrabberPtr, c_void_p]
            cls.lib.FrmGrab_GetProperty.restype = c_int

            cls.lib.FrmGrab_SetProperty.argtypes = [FrmGrabberPtr, c_void_p]
            cls.lib.FrmGrab_SetProperty.restype = c_int

            # VGA Modes
            cls.lib.FrmGrab_GetVGAModes.argtypes = [FrmGrabberPtr]
            cls.lib.FrmGrab_GetVGAModes.restype = (
                c_void_p  # Use actual struct if defined
            )

            cls.lib.FrmGrab_SetVGAModes.argtypes = [FrmGrabberPtr, c_void_p]
            cls.lib.FrmGrab_SetVGAModes.restype = c_int

            # PS2
            cls.lib.FrmGrab_SendPS2.argtypes = [FrmGrabberPtr, c_void_p]
            cls.lib.FrmGrab_SendPS2.restype = c_int

            # Streaming
            cls.lib.FrmGrab_SetMaxFps.argtypes = [FrmGrabberPtr, c_double]
            cls.lib.FrmGrab_SetMaxFps.restype = c_int

            cls.lib.FrmGrab_Start.argtypes = [FrmGrabberPtr]
            cls.lib.FrmGrab_Start.restype = c_int

            cls.lib.FrmGrab_Stop.argtypes = [FrmGrabberPtr]
            cls.lib.FrmGrab_Stop.restype = None

            # Frame
            cls.lib.FrmGrab_Frame.argtypes = [FrmGrabberPtr, c_uint32, c_void_p]
            cls.lib.FrmGrab_Frame.restype = POINTER(V2U_GrabFrame2)

            cls.lib.FrmGrab_Release.argtypes = [FrmGrabberPtr, POINTER(V2U_GrabFrame2)]
            cls.lib.FrmGrab_Release.restype = None

            # Memory cleanup
            cls.lib.FrmGrab_Free.argtypes = [c_void_p]
            cls.lib.FrmGrab_Free.restype = None

            cls.lib.FrmGrab_SetAlloc.argtypes = [
                FrmGrabberPtr,
                POINTER(FrmGrabMemCB),
                c_void_p,
            ]
            cls.lib.FrmGrab_SetAlloc.restype = None

            cls.lib.FrmGrab_Init()
            cls.is_functional = True  # IF we made it, then it works

        except AttributeError as err:
            raise RuntimeError(
                "Epiphan library is not accessible, possibly wrong architecture"
            ) from err

    @classmethod
    def cleanup_library(cls):
        if cls.is_functional:
            cls.lib.FrmGrab_Deinit()


class CapturedFrame:
    def __init__(self, data: bytes, width: int, height: int,
                 palette: int, vfreq: int, retcode: int):
        self.data = data
        self.width = width
        self.height = height
        self.palette = palette
        self.vfreq = vfreq
        self.retcode = retcode

    def __repr__(self):
        return (f"CapturedFrame({self.width}x{self.height}, "
                f"palette=0x{self.palette:x}, {len(self.data)} bytes)")

    def to_numpy(self):
        """Return the pixel buffer as a numpy uint8 array.

        RGB24 -> shape (H, W, 3) ; Y8 -> shape (H, W) ; other formats
        return a flat 1D array (caller knows the layout). Returns None if
        the frame has no usable pixel data.
        """
        import numpy as np
        if not self.data or self.width <= 0 or self.height <= 0:
            return None
        arr = np.frombuffer(self.data, dtype=np.uint8)
        fmt = self.palette & V2U_GRABFRAME_FORMAT_MASK
        if fmt == V2U_GRABFRAME_FORMAT_RGB24:
            n = self.height * self.width * 3
            if arr.size < n:
                return None
            return arr[:n].reshape(self.height, self.width, 3).copy()
        if fmt == V2U_GRABFRAME_FORMAT_Y8:
            n = self.height * self.width
            if arr.size < n:
                return None
            return arr[:n].reshape(self.height, self.width).copy()
        return arr.copy()


class EpiphanFrameGrabber:
    def __init__(self):
        EpiphanLibraryWrapper.setup_library()
        self.device: FrmGrabLocalPtr = None

    def initialize_device(self):
        self.device = EpiphanLibraryWrapper.lib.FrmGrabLocal_Open()
        if not self.device:
            raise RuntimeError("No frame grabber found")

    def get_serial_number(self) -> str:
        sn = EpiphanLibraryWrapper.lib.FrmGrab_GetSN(self.device)
        return sn.decode() if sn else None

    def get_product_name(self) -> str:
        name = EpiphanLibraryWrapper.lib.FrmGrab_GetProductName(self.device)
        return name.decode() if name else None

    def get_location(self) -> str:
        loc = EpiphanLibraryWrapper.lib.FrmGrab_GetLocation(self.device)
        return loc.decode() if loc else None

    def get_video_mode(self) -> V2U_VideoMode:
        mode = V2U_VideoMode()
        EpiphanLibraryWrapper.lib.FrmGrab_GetVideoMode(self.device, byref(mode))
        return mode

    def detect_video_mode(self) -> V2U_VideoMode | None:
        mode = V2U_VideoMode()
        ok = EpiphanLibraryWrapper.lib.FrmGrab_DetectVideoMode(self.device, byref(mode))
        return mode if ok == V2U_TRUE else None

    def get_capture_params(self) -> V2U_GrabParameters:
        params = V2U_GrabParameters()
        ok = EpiphanLibraryWrapper.lib.FrmGrab_GetGrabParams(self.device, byref(params))
        if ok != V2U_TRUE:
            raise RuntimeError("Failed to get grab parameters")
        return params

    def set_capture_params(self, params: V2U_GrabParameters):
        ok = EpiphanLibraryWrapper.lib.FrmGrab_SetGrabParams(self.device, byref(params))
        if ok != V2U_TRUE:
            raise RuntimeError("Failed to set grab parameters")

    def start_streaming(self):
        if EpiphanLibraryWrapper.lib.FrmGrab_Start(self.device) != V2U_TRUE:
            raise RuntimeError("Failed to start streaming")

    def stop_streaming(self):
        EpiphanLibraryWrapper.lib.FrmGrab_Stop(self.device)

    def close(self):
        if self.device:
            EpiphanLibraryWrapper.lib.FrmGrab_Close(self.device)
            self.device = None

    def grab_frame(
        self, format=V2U_GRABFRAME_FORMAT_RGB24, crop: V2URect | None = None
    ) -> CapturedFrame | None:
        crop_ptr = byref(crop) if crop else None
        frame_ptr = EpiphanLibraryWrapper.lib.FrmGrab_Frame(
            self.device, format, crop_ptr
        )
        if not frame_ptr:
            return None
        try:
            f = frame_ptr.contents
            length = int(f.imagelen)
            if length and f.pixbuf:
                data = ctypes.string_at(f.pixbuf, length)
            else:
                data = b""
            return CapturedFrame(
                data=data,
                width=int(f.crop.width),
                height=int(f.crop.height),
                palette=int(f.palette),
                vfreq=int(f.mode.vfreq),
                retcode=int(f.retcode),
            )
        finally:
            EpiphanLibraryWrapper.lib.FrmGrab_Release(self.device, frame_ptr)

    def __enter__(self):
        if self.device is None:
            self.initialize_device()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
