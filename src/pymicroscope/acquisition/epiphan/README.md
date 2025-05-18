# Epiphan VGA acquisition card

This document explains the details of how to get the libraries of v2u (VGA2USB?) from Epiphan to be accessible under Python.
A single document `epiphanlibwrapper.py` contains everything and is completely standalone and independent.

## Architecture

The libraries are Intel only.  Trying to use them on arm64 will simply return nothing (no symbols are defined)


## Preparation: combine libraries into libfrmgrab.dylib

Static libraries (ending with .a) are not supported in Python.  The many libraries libfrmgrab.a libz.a libjpeg.a libpng.a libslava.a must be
packages into a single dylib (dynamic library) with the following command on an Intel macOS:

```
g++ -dynamiclib -o libfrmgrab.dylib -Wl,-all_load libfrmgrab.a libz.a libjpeg.a libpng.a libslava.a -framework CoreFoundation -framework IOKit -framework 
CoreServices -lexpat
```

## EpiphanLibraryWrapper

Using `ctypes` we can load a library with `lib = ctypes.CDLL(libpath)`, then all symbols are usable via attributes.
A namespace-class is used to keep track of the library, and declare the various function types and arguments).
Important: when accessing the functions directly in `lib`, the c-type arguments must be used.  For instance
a string must be c-encoded:

```
EpiphanLibraryWrapper.lib.FrmGrab_Init()
EpiphanLibraryWrapper.lib.FrmGrab_Open("local".encode('utf-8'))
...
```
## EpiphanFrameGrabber

Finally, the goal of `EpiphanFrameGrabber` is to allow testing of the library independently of the rest of the structure of the program.
All necessary functions should be there.
