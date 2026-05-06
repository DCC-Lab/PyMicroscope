"""Single-process entry point for the Epiphan acquisition node.

What it does, in order:
  1. Make sure a Pyro5 nameserver is reachable (start a local one if not).
  2. Try to open the Epiphan frame grabber + VMS and Polygon serial circuits.
     Any subsystem that fails is left as None; the GUI's "Reconnect" button
     can retry later, which matters because USB serial adapters and the
     Epiphan card are sometimes powered on AFTER the app starts.
  3. Run a Pyro5 daemon in a background thread, registering names lazily
     as services come up:
       ca.dccmlab.imageprovider.epiphan
       ca.dccmlab.hardware.vms
       ca.dccmlab.hardware.polygon
  4. Open the local Tk diagnostic GUI on the main thread (Tk on macOS
     requires the main thread).

Run with: ``PYTHONPATH=src python3 -m pymicroscope.acquisition.epiphan.acquisitiondaemon``
"""
from __future__ import annotations

import logging
import sys
import threading
import time

from Pyro5.api import Daemon
from Pyro5.errors import NamingError

from pymicroscope.utils.pyroprocess import PyroProcess
from pymicroscope.acquisition.vmscontroller import VMSController
from pymicroscope.acquisition.epiphan.epiphanlibwrapper import EpiphanFrameGrabber
from pymicroscope.acquisition.epiphan.polygoncontroller import PolygonController
from pymicroscope.acquisition.epiphan.pyroservices import (
    EpiphanPyroService,
    VMSPyroService,
    PolygonPyroService,
)


IMAGE_PYRO_NAME = "ca.dccmlab.imageprovider.epiphan"
VMS_PYRO_NAME = "ca.dccmlab.hardware.vms"
POLYGON_PYRO_NAME = "ca.dccmlab.hardware.polygon"

log = logging.getLogger(__name__)


class HardwareManager:
    """Owns the three optional hardware handles and their Pyro service
    wrappers. Lets the GUI retry connection at any time.

    Concurrency: ``reconnect()`` is intentionally synchronous and called from
    the Tk main thread. The Pyro daemon's request loop runs on a background
    thread but only touches the service objects via Pyro proxies, never the
    raw hardware handles, so no extra locking is needed for the
    instantiation step.
    """

    def __init__(self, daemon: Daemon, ns):
        self.daemon = daemon
        self.ns = ns

        self.grabber: EpiphanFrameGrabber | None = None
        self.vms: VMSController | None = None
        self.polygon: PolygonController | None = None

        self.image_service: EpiphanPyroService | None = None
        self.vms_service: VMSPyroService | None = None
        self.polygon_service: PolygonPyroService | None = None

        self._registered: set[str] = set()

    # ---- public API -----------------------------------------------------

    def reconnect(self) -> dict[str, str]:
        """Try to (re)open every subsystem that is currently down.

        Returns a status dict ``{subsystem: "ok" | "<error>"}`` for the GUI
        to display.
        """
        status = {}
        status["epiphan"] = self._try_open_epiphan()
        status["vms"] = self._try_open_vms()
        status["polygon"] = self._try_open_polygon()
        return status

    def shutdown(self):
        # Unregister from nameserver
        for name in list(self._registered):
            try:
                self.ns.remove(name)
            except (NamingError, Exception):
                pass
            self._registered.discard(name)

        # Stop streaming and release devices
        if self.image_service is not None:
            try:
                self.image_service.stop_streaming()
            except Exception:
                pass
        if self.grabber is not None:
            try:
                self.grabber.shutdown_device()
            except Exception:
                pass
        if self.vms is not None:
            try:
                self.vms.shutdown()
            except Exception:
                pass
        if self.polygon is not None:
            try:
                self.polygon.shutdown()
            except Exception:
                pass

    # ---- per-subsystem connect helpers ----------------------------------

    def _try_open_epiphan(self) -> str:
        if self.image_service is not None:
            return "ok"
        try:
            grabber = EpiphanFrameGrabber()
            grabber.initialize_device()
        except Exception as err:
            log.warning("Epiphan failed to initialise: %s", err)
            return f"error: {err}"
        self.grabber = grabber
        self.image_service = EpiphanPyroService(grabber)
        self._register(IMAGE_PYRO_NAME, self.image_service)
        log.info("Epiphan ready.")
        return "ok"

    def _try_open_vms(self) -> str:
        if self.vms_service is not None:
            return "ok"
        try:
            c = VMSController()
            c.initialize()
        except Exception as err:
            log.warning("VMS failed to initialise: %s", err)
            return f"error: {err}"
        self.vms = c
        self.vms_service = VMSPyroService(c)
        self._register(VMS_PYRO_NAME, self.vms_service)
        log.info("VMS ready on %s.", c.serial_path)
        return "ok"

    def _try_open_polygon(self) -> str:
        if self.polygon_service is not None:
            return "ok"
        try:
            c = PolygonController()
            c.initialize()
        except Exception as err:
            log.warning("Polygon failed to initialise: %s", err)
            return f"error: {err}"
        self.polygon = c
        self.polygon_service = PolygonPyroService(c)
        self._register(POLYGON_PYRO_NAME, self.polygon_service)
        log.info("Polygon ready on %s.", c.serial_path)
        return "ok"

    def _register(self, name: str, obj):
        try:
            uri = self.daemon.register(obj)
            self.ns.register(name, uri)
            self._registered.add(name)
            log.info("Registered %s -> %s", name, uri)
        except Exception as err:
            log.warning("Failed to register %s: %s", name, err)


# ---- nameserver bootstrap ---------------------------------------------------

def _ensure_nameserver():
    ns = PyroProcess.locate_ns(timeout=1)
    if ns is not None:
        return ns
    log.info("No nameserver reachable; starting a local one.")
    PyroProcess.start_nameserver()
    for _ in range(50):
        ns = PyroProcess.locate_ns(timeout=0.5)
        if ns is not None:
            return ns
        time.sleep(0.1)
    raise RuntimeError("Nameserver did not start within 5 s")


# ---- entry point ------------------------------------------------------------

def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    ns = _ensure_nameserver()
    daemon = Daemon(host=PyroProcess.get_local_ip())
    manager = HardwareManager(daemon, ns)

    # Initial connect attempt (silent on failure - GUI shows status)
    manager.reconnect()

    stop_event = threading.Event()

    def _serve():
        daemon.requestLoop(loopCondition=lambda: not stop_event.is_set())

    daemon_thread = threading.Thread(target=_serve, name="pyro-daemon", daemon=True)
    daemon_thread.start()

    try:
        from pymicroscope.acquisition.epiphan.diagnosticgui import DiagnosticWindow
        win = DiagnosticWindow(manager)
        win.mainloop()
    finally:
        stop_event.set()
        try:
            daemon.shutdown()
        except Exception:
            pass
        manager.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
