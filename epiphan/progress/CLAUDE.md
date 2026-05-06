# CLAUDE.md - Epiphan acquisition node

Read this before touching code in `src/pymicroscope/acquisition/epiphan/` or
`src/pymicroscope/acquisition/vmscontroller.py`. It captures decisions and
constraints that aren't obvious from the code itself.

## Hardware reality

- **Host**: 2012 Mac Pro, OS X 10.9.5, Python 3.11.9. **No internet** for
  pip is a working assumption — only modules already on disk count.
  Currently installed: `numpy 1.26.4`, `Pillow 9.5.0`, `Pyro5 5.15`,
  `pyserial 3.5`, `psutil 7.2.2`, `pybind11 2.10.4`. Stdlib `tkinter` and
  `ctypes` are available.
- **Frame grabber**: Epiphan DVI2PCIe via `libfrmgrab.dylib` (in
  `src/pymicroscope/acquisition/epiphan/`). **Only one process can own the
  device** — do not open it from two places.
- **VMS circuit (CPN 522)**: galvo DAC + frame line counts. Serial,
  19200 baud, 3 s timeout. Validates by reading CPN.
- **Polygon circuit (CPN 607)**: TMR1 reload register sets the polygon
  clock. Serial, 19200 baud. **Different USB port** from VMS.
- **PMT signals**: encoded as the R/G/B channels of the DVI signal. Each
  RGB frame *is* the three photodetector traces; "Combined" tab is the
  same array displayed in colour.

## Architecture

```
acquisitiondaemon.py (main thread = Tk; background thread = Pyro daemon)
  └── HardwareManager owns:
        ├── EpiphanFrameGrabber  --wrapped by-->  EpiphanPyroService
        ├── VMSController        --wrapped by-->  VMSPyroService
        └── PolygonController    --wrapped by-->  PolygonPyroService
```

Each subsystem is **independently optional**. The manager's `reconnect()`
retries any subsystem currently `None`. The GUI calls it from the
"Reconnect hardware" button — that is the user-facing recovery path when
hardware is plugged in / powered on after the app starts.

## Pyro names

Registered lazily as services come up:

| Pyro name                            | Object               |
|--------------------------------------|----------------------|
| `ca.dccmlab.imageprovider.epiphan`   | `EpiphanPyroService` |
| `ca.dccmlab.hardware.vms`            | `VMSPyroService`     |
| `ca.dccmlab.hardware.polygon`        | `PolygonPyroService` |

`EpiphanPyroService.grab()` returns `(bytes, shape, dtype_str)` because
serpent (Pyro5's default serializer) does not natively serialize numpy
arrays. In-process callers (the local Tk GUI) use `grab_array()` to skip
that detour.

## Synchronisation contract

1. **Polygon RPM → fast-axis line rate**: `lineRate = RPM/60 × 36`.
2. **Lines per frame** drives galvo travel; `dac_start + dac_increment ×
   active_lines` must stay in `[0, 65535]`.
3. **Width** is software crop applied after the grab — the Epiphan VGA
   mode is whatever the card was last configured for (the legacy
   iPhotonRT app configures it; we currently inherit that state).

The GUI's **Apply** button writes in this order to avoid transient
out-of-spec states:

1. Disable polygon clock (if it was on).
2. Write VMS line counts + DAC values.
3. Write polygon TMR1.
4. Re-enable polygon clock.

## Presets

The dropdown is loaded at import time from
`epiphan/iPhotonRT2.5.4erbel47/Contents/Resources/ScanningAcquisitionParameters.plist`
when present, falling back to the PDF transcription
(`vgaModesDefinition.pdf`). The plist is the canonical source — labels
are like `1000x500@32`.

## Things to NOT do

- Don't open the Epiphan device from `EpiphanImageProvider` (the legacy
  multiprocessing class) **and** the new `EpiphanPyroService` at the same
  time. The acquisition daemon owns the only handle.
- Don't add new runtime deps. If you really need one, ask first — many
  packages don't install on this OS.
- Don't put TMR1 / polygon-clock logic in `VMSController`. TMR1 lives on
  the polygon circuit (CPN 607), not on VMS (CPN 522).
- Don't use `.amend` or hooks-bypass flags when committing in this
  subdirectory.

## Reference

- `epiphan/vrscdt.m` — original MATLAB diagnostic tool (source of all
  serial opcodes).
- `epiphan/iPhotonRT2.5.4erbel47/` — compiled legacy Cocoa app
  (`.nib`/binary). **Reference for protocol/communication only**, not a
  model to follow for features or UX. Use it to confirm that the
  hardware *can* be made to acquire (it does in this app), and mine the
  plists in `Contents/Resources/` for known-good parameter values
  (Epiphan VGA registers, gain/offset/shift, scan presets). Do not
  reproduce its layout, workflow, or scope.
- `epiphan/vgaModesDefinition.pdf` — Fast VGA Modes table.
- `progress/` — this folder, plus dated `*-notes_epiphan.txt` from the
  user.
