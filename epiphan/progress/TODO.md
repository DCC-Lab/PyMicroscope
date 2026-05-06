# TODO - Epiphan acquisition node

Living list. Move items to `CHANGELOG.md` when done; delete obsolete
entries.

## Blockers found 2026-04-30 hardware test

1. **`libfrmgrab.dylib` won't load on OS X 10.9.5.** dyld error
   `load command 0x80000034 is unknown` — the bundled dylib in
   `src/pymicroscope/acquisition/epiphan/libfrmgrab.dylib` was built for
   a newer macOS (uses `LC_BUILD_VERSION`, introduced in 10.13). iPhotonRT
   statically links FrmGrab inside `HardwareLibrary.framework` with
   internal linkage, so we can't dlopen and reuse it. **Action:** the
   user needs to source an older Epiphan SDK build of `libfrmgrab.dylib`
   (Epiphan SDK ~2014 era, when 10.9 was current). Drop it in
   `src/pymicroscope/acquisition/epiphan/libfrmgrab.dylib`. Verify with
   `file libfrmgrab.dylib` (should report MinimumOS ≤ 10.9 — use
   `otool -l libfrmgrab.dylib | grep -A3 LC_VERSION_MIN_MACOSX`).

2. **Polygon serial port not auto-detected.** The auto-discover filter
   was too narrow (`usbserial`/`USA` substring). Broadened on 2026-04-30
   to probe every `/dev/cu.*` (skipping Bluetooth/debug). Re-run and
   confirm.

## Now (next user-facing test on the old Mac)

1. **Bring-up sequence the user should run**:
   ```bash
   cd /Users/dcclab/Desktop/PyMicroscope
   PYTHONPATH=src python3 -m pymicroscope.acquisition.epiphan.acquisitiondaemon
   ```
   - The window should open even if no hardware is connected.
   - With hardware powered off: status bar shows "VMS: not accessible",
     "Polygon: not accessible", "Epiphan: not accessible". Clicking
     **Start streaming** should show a warning, not crash.
   - Power on hardware → click **Reconnect hardware** → status bar
     should switch to firmware/CPN/SN strings within ~2 s.

2. **Confirm `/dev/cu.*` device names** on the old Mac:
   ```bash
   ls /dev/cu.*
   ```
   The auto-detect filter currently looks for `usbserial` or `USA` in
   the path. If the actual port names don't match (e.g. some Keyspan
   adapters use `KeySerial`), edit the filter in:
   - `src/pymicroscope/acquisition/vmscontroller.py:_auto_discover`
   - `src/pymicroscope/acquisition/epiphan/polygoncontroller.py:_auto_discover`

3. **Verify image pipeline after Reconnect** with VMS + Polygon + Epiphan
   all up:
   - Click **Start streaming**.
   - "Combined" tab should fill with a frame.
   - R / G / B tabs should show one channel each.
   - FPS should hit roughly the polygon-derived vsync rate (~32 Hz for
     the 1000x500 preset).

## Soon

- **VGA mode programming.** Right now we inherit whatever VGA mode the
  Epiphan card was last left in. Add a routine that calls
  `FrmGrab_SetProperty` to write the VGA timing registers (h/v
  resolutions, porches, sync times, sampling phase, PLL shift, gains,
  offsets) directly from our Python code. The values in
  `iPhotonRT2.5.4erbel47/Contents/Resources/defaultsEpiphan.plist` are
  a known-good *reference* for what those registers can hold (use them
  to validate the protocol, not to mimic the legacy app's behaviour).
  - Reference: `epiphanlibwrapper.py:frame_grabber_set_video_mode` (the
    skeleton is there but broken — it references `self.lib` which
    doesn't exist on `EpiphanFrameGrabber`).
- **VMS-only minimal window.** The user mentioned wanting a stripped-down
  Tk window that opens only the VMS serial port and exposes the four
  parameters (no Epiphan, no polygon, no preview) for bench tests. ~80
  lines, reuses `VMSController`.
- **Polygon RPM round-trip on hardware.** Set RPM via the GUI, read back
  `READ_TMR1_RELOAD`, confirm it matches.
- **Pyro round-trip from a second computer**: connect from the newer
  machine, call `vms.build_info()` and `image_service.grab()`. Document
  the firewall/IP requirements.

## Later

- **Frame queue for remote consumers.** `EpiphanPyroService.grab()`
  triggers a fresh capture on every call. For a remote GUI streaming at
  N Hz, run a producer thread that grabs into a shared latest-frame slot
  and have `latest_frame()` return that slot. Saves device round-trips.
- **Persist GUI settings.** Save the last-used preset and free-form
  overrides to a `~/.pymicroscope-epiphan.json` so the next launch
  starts where you left off.
- **Watchdog on `_grab_rgb_array`.** The Epiphan driver can hang if the
  DVI input drops. Add a thread + timeout so the GUI doesn't freeze.
- **Unit tests for `VMSController.apply_settings`.** Mirror the polygon
  test pattern.

## Won't do (unless asked)

- Migrating the existing multiprocessing `ImageProvider` /
  `EpiphanImageProvider` plumbing into the new daemon. They were left
  in place but the daemon does not use them.
- Adding `mytk`, `hardwarelibrary`, OpenCV, or any other heavy dep on
  the old Mac.

## Notes from `20260430-notes_epiphan.txt`

Addressed in this commit:

- ✅ `'NoneType' object has no attribute 'start_streaming'` — fixed
  with None-guards in `diagnosticgui._on_start` and friends.
- ✅ "VMS / Polygon / Epiphan not accessible after the fact" — fixed
  with `HardwareManager.reconnect()` and the **Reconnect hardware**
  button.
- ⏳ "Acquisition works perfectly in iPhotonRT but not here" — likely
  the VGA mode programming gap (see "Soon" above). To verify on next
  hardware test.
