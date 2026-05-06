# Changelog - Epiphan acquisition node

Newest first. Entries are dated. Bump entries as you go; do not rewrite
history.

## 2026-04-30 (later)

### Changed
- VMS and polygon `_auto_discover` no longer require `usbserial`/`USA` in
  the device path. They now probe every `/dev/cu.*` (skipping Bluetooth
  and debug consoles). Reason: on the old Mac the polygon adapter has a
  device name that didn't match the substring filter, so polygon never
  came up despite the cable being plugged in.

### Known broken
- `libfrmgrab.dylib` shipped in `src/pymicroscope/acquisition/epiphan/`
  fails to load on OS X 10.9.5 (`load command 0x80000034 is unknown` =
  `LC_BUILD_VERSION`, added in 10.13). Need an older Epiphan SDK build.
  Tracked in TODO.md → "Blockers found".

## 2026-04-30

### Added
- `acquisitiondaemon.py`: single-process entry point. Starts a Pyro5
  nameserver if absent, opens hardware (best-effort), runs the Pyro
  daemon in a background thread, opens the Tk GUI on the main thread.
- `HardwareManager` class with `reconnect()` so subsystems can be brought
  online after the GUI is already up. Pyro names are registered lazily,
  one per subsystem.
- `polygoncontroller.py` (`PolygonController`, CPN 607): opcodes
  `ENABLE_POLYGON_CLOCK=0x70`, `DISABLE_POLYGON_CLOCK=0x71`,
  `WRITE_TMR1_RELOAD=0x7D`, `READ_TMR1_RELOAD=0x75`. Validates TMR1 in
  `[40535, 60327]`. Auto-discovers serial port by probing `READ_CPN`.
- `pyroservices.py`: `EpiphanPyroService`, `VMSPyroService`,
  `PolygonPyroService`. Includes a ctypes mirror of `V2U_GrabFrame2` that
  decodes the DVI buffer into a `(H, W, 3) uint8` numpy array before the
  driver releases it.
- `diagnosticgui.py`: Tk window with status bar, free-form numeric
  controls, preset dropdown loaded from the legacy iPhotonRT plist
  (`ScanningAcquisitionParameters.plist`) with a PDF-transcription
  fallback, atomic Apply button (polygon-aware ordering), and a
  `ttk.Notebook` with Combined / R / G / B preview tabs.
- `tests/test_polygon_controller.py`: 5 mocked-serial tests covering
  framing, range checks, and RPM <-> TMR1 round-trip.
- Lazy import for `EpiphanImageProvider` in
  `acquisition/epiphan/__init__.py` so the daemon runs without `mytk`.

### Changed
- `vmscontroller.py`: `parameters_are_valid` now uses inclusive bounds
  (`<=`). Added `apply_settings(dict)` that validates and writes line
  counts + DAC values in a defined order. Auto-discovers serial port by
  probing `READ_CPN`. Verifies CPN == 522 on connect. Removed the
  misleading TMR1 / polygon-frequency properties — those live on the
  polygon circuit.

### Fixed
- GUI no longer crashes with `'NoneType' has no attribute
  'start_streaming'` when Epiphan isn't accessible at boot. All buttons
  guard against `None` services and show a hint to click "Reconnect
  hardware".
- Status / parameter values now refresh correctly after a reconnect; the
  GUI reads services through the manager rather than caching them.

## 2026-03-26 (pre-claude state)

- Initial Python translation of VMS serial commands in
  `vmscontroller.py` (CPN 522 only). Bounded check was off-by-one
  (exclusive); no apply / no auto-discovery.
- `EpiphanFrameGrabber` and library wrapper present but no Pyro
  exposure, no diagnostic GUI, no polygon controller.
