# v2u_defs_constants.py

from ctypes import Structure, c_uint16, c_uint32


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
