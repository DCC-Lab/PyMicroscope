# AGENTS.md - Working notes for AI assistants on this subsystem

Conventions and ground rules for any agent (Claude or otherwise)
modifying the Epiphan acquisition node. Read alongside `CLAUDE.md`
(architecture) and `TODO.md` (open work).

## Ground rules

1. **No new runtime dependencies.** The old Mac can rarely install
   anything. Stick to: `numpy`, `Pillow`, `Pyro5`, `pyserial`, `psutil`,
   `pybind11`, stdlib. If you need something else, raise it with the
   user before writing the code.
2. **Tk only on the main thread on macOS.** Don't try to spawn a Tk
   window from the Pyro daemon thread. The current layout (Tk on main,
   Pyro daemon on background) is correct — preserve it.
3. **One owner of the Epiphan device.** `EpiphanFrameGrabber` is opened
   exactly once, by `HardwareManager._try_open_epiphan`. The legacy
   multiprocessing `EpiphanImageProvider` must not run alongside the
   daemon.
4. **All hardware subsystems are optional at boot.** If something fails
   to come up, log it and continue. Surface failure in the status bar
   and let the user click "Reconnect hardware". Never raise out of the
   daemon's main loop because one cable was unplugged.
5. **Update the progress files.** Whenever you change behaviour, append
   to `CHANGELOG.md` and adjust `TODO.md`. If a constraint or invariant
   changes, update `CLAUDE.md`.
6. **Preserve the synchronisation order in `Apply`**: pause polygon →
   write VMS → write TMR1 → resume polygon. Documented in `CLAUDE.md`.
7. **Tests run on the dev machine; hardware tests run on the old Mac.**
   `tests/test_polygon_controller.py` is mocked and must keep passing
   anywhere. Hardware bring-up steps live in `TODO.md`.

## Workflow recipe

For a typical change:

1. Read the relevant section of `CLAUDE.md` to confirm constraints.
2. Make code edits (prefer Edit on existing files; only create new
   modules when the layout in `CLAUDE.md` calls for it).
3. Run `python -m unittest tests.test_polygon_controller` from the
   `tests/` directory — must stay green.
4. If the change touches the GUI or hardware path, manually verify on
   the old Mac (steps in `TODO.md`).
5. Append a dated entry in `CHANGELOG.md`. Move completed items out of
   `TODO.md`.

## What lives where

| Path                                                            | Purpose                                  |
|-----------------------------------------------------------------|------------------------------------------|
| `src/pymicroscope/acquisition/vmscontroller.py`                 | VMS (CPN 522) serial driver              |
| `src/pymicroscope/acquisition/epiphan/polygoncontroller.py`     | Polygon (CPN 607) serial driver          |
| `src/pymicroscope/acquisition/epiphan/epiphanlibwrapper.py`     | ctypes binding to `libfrmgrab.dylib`     |
| `src/pymicroscope/acquisition/epiphan/pyroservices.py`          | `@expose` wrappers + numpy serialisation |
| `src/pymicroscope/acquisition/epiphan/acquisitiondaemon.py`     | Entry point + `HardwareManager`          |
| `src/pymicroscope/acquisition/epiphan/diagnosticgui.py`         | Tk window                                |
| `tests/test_polygon_controller.py`                              | Mocked-serial unit tests                 |
| `epiphan/vrscdt.m`                                              | MATLAB reference (opcodes, ranges)       |
| `epiphan/iPhotonRT2.5.4erbel47/Contents/Resources/`             | Legacy app plists (working defaults)     |
| `epiphan/progress/`                                             | This folder                              |

## Communication style with the user

- The user runs the actual hardware tests; you cannot. When you change
  something hardware-facing, summarise what to test and what symptom to
  watch for.
- Notes appear as `progress/YYYYMMDD-notes_epiphan.txt`. Read them at
  the start of any session — they describe behaviour you can't observe
  remotely.
- The user does not want extensive narration. Keep responses tight.
