# Epiphan VGA acquisition card

This document explains the details of how to get the libraries of v2u (VGA2USB?) from Epiphan to be accessible under Python.
A single document `epiphanlibwrapper.py` contains everything and is completely standalone and independent.

## Architecture

The libraries are Intel only. Trying to use them on arm64 will simply return nothing (no symbols are defined).

## Preparation: combine libraries into libfrmgrab.dylib

Static libraries (ending with .a) are not directly usable from Python via `ctypes`.
The many libraries `libfrmgrab.a libz.a libjpeg.a libpng.a libslava.a` must be packaged
into a single dylib. The committed `libfrmgrab.dylib` is built for
`-mmacosx-version-min=10.9` so it works on the legacy DCC video acquisition Mac
(`dcc-video-2p.local`, OS X 10.9.5). On a more recent machine, you can either
keep using the committed binary or rebuild it locally.

To rebuild:

```
cd src/pymicroscope/acquisition/epiphan
./build_dylib.sh
```

The script accepts environment variables:

```
MACOS_MIN=11.0 ARCH=x86_64 ./build_dylib.sh
```

If you ever see `dlopen ... no suitable image found ... cannot load 'libfrmgrab.dylib' (load command 0x80000034 is unknown)`,
the dylib was compiled for a newer macOS than the one you are running. Rebuild
with `MACOS_MIN` set to your target OS.

The underlying command (kept here for reference) is:

```
clang -dynamiclib -arch x86_64 \
    -mmacosx-version-min=10.9 \
    -install_name @rpath/libfrmgrab.dylib \
    -Wl,-force_load,libfrmgrab.a \
    libslava.a libjpeg.a libpng.a libz.a \
    -framework CoreFoundation -framework IOKit -framework CoreServices \
    -lexpat -lc++ \
    -o libfrmgrab.dylib
```

## EpiphanLibraryWrapper

Using `ctypes` we can load a library with `lib = ctypes.CDLL(libpath)`, then all symbols are usable via attributes.
A namespace-class is used to keep track of the library, and declare the various function types and arguments.
Important: when accessing the functions directly in `lib`, the C-type arguments must be used. For instance
a string must be c-encoded, and the location follows a URL-like format documented in `frmgrab.h`
(`local:[SERIAL]`, `net:[ADDRESS[:PORT]]`, `sn:SERIAL`, `id:INDEX`):

```
EpiphanLibraryWrapper.lib.FrmGrab_Init()
EpiphanLibraryWrapper.lib.FrmGrab_Open("local:".encode('utf-8'))
...
```

## EpiphanFrameGrabber

The goal of `EpiphanFrameGrabber` is to allow testing of the library independently of the rest of the structure of the program.
It is a thin object-oriented wrapper around `FrmGrabLocal_Open` and the `FrmGrab_*` API. It supports use as a context manager:

```python
with EpiphanFrameGrabber() as fg:
    print(fg.get_serial_number(), fg.get_product_name())
    frame = fg.grab_frame()
    if frame:
        print(frame.width, frame.height, len(frame.data))
```

`grab_frame()` returns a `CapturedFrame` whose `data` is a Python `bytes` copy of the pixel buffer (the underlying C buffer is released before the call returns).

Tests live in `tests/test_wrapper_epiphan.py` (library/CDLL smoke tests) and `tests/test_epiphan_framegrabber.py` (full `EpiphanFrameGrabber` coverage).
