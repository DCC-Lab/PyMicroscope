"""Polygon mirror speed-control circuit (CPN 607).

Drives a separate serial port from VMSController. Translated from the CPN 607
section of epiphan/vrscdt.m. The circuit is an RS-232 programmable TTL
frequency generator. TMR1_RELOAD sets the polygon clock period.

  polygonClockFrequency [Hz] = 5_000_000 / (65535 - TMR1_RELOAD)
  polygonRPM = polygonClockFrequency / 2 * 60
"""
import struct

import serial
from serial.tools import list_ports


POLYGON_SERIAL_PATH = None  # set to a /dev/cu.* path to bypass auto-detect

EXPECTED_CPN = 607
TMR1_MIN = 40535
TMR1_MAX = 60327
POLYGON_FACES = 36


class PolygonController:
    def __init__(self, serial_path: str | None = None):
        self.serial_path = serial_path or POLYGON_SERIAL_PATH
        self.port: serial.Serial | None = None
        self.is_accessible = False
        self._clock_enabled = False

        self.commands = {
            "READ_FIRMWARE_VERSION": {
                "command_code": 0x7F,
                "command_bytes_format": ">b",
                "response_bytes_format": "3b",
            },
            "READ_CID": {
                "command_code": 0x6C,
                "command_bytes_format": ">b",
                "response_bytes_format": "2b",
            },
            "READ_CPN": {
                "command_code": 0x6D,
                "command_bytes_format": ">b",
                "response_bytes_format": ">h",
            },
            "READ_SN": {
                "command_code": 0x6B,
                "command_bytes_format": ">b",
                "response_bytes_format": "2b",
            },
            "READ_BUILD_TIME": {
                "command_code": 0x6A,
                "command_bytes_format": ">b",
                "response_bytes_format": "8cx",
            },
            "READ_BUILD_DATE": {
                "command_code": 0x69,
                "command_bytes_format": ">b",
                "response_bytes_format": "11c",
            },
            "READ_TMR1_RELOAD": {
                "command_code": 0x75,
                "command_bytes_format": ">b",
                "response_bytes_format": ">H",
            },
            "WRITE_TMR1_RELOAD": {
                "command_code": 0x7D,
                "command_bytes_format": ">bH",
                "response_bytes_format": "",
                "minimum": TMR1_MIN,
                "maximum": TMR1_MAX,
            },
            "ENABLE_POLYGON_CLOCK": {
                "command_code": 0x70,
                "command_bytes_format": ">b",
                "response_bytes_format": "",
            },
            "DISABLE_POLYGON_CLOCK": {
                "command_code": 0x71,
                "command_bytes_format": ">b",
                "response_bytes_format": "",
            },
        }

    def initialize(self):
        path = self.serial_path or self._auto_discover()
        if path is None:
            raise RuntimeError("No candidate serial port found for polygon circuit")

        self.port = serial.Serial(path, baudrate=19200, timeout=3)
        self.serial_path = path

        cpn = self.send_command("READ_CPN")
        if cpn is None or cpn[0] != EXPECTED_CPN:
            self.port.close()
            self.port = None
            raise RuntimeError(
                f"Polygon circuit on {path} reported CPN={cpn} (expected {EXPECTED_CPN})"
            )

        self.is_accessible = True

    def shutdown(self):
        if self.port is not None:
            try:
                self.disable_clock()
            except Exception:
                pass
            self.port.close()
        self.port = None
        self.is_accessible = False

    def _auto_discover(self) -> str | None:
        # Probe every /dev/cu.* USB serial candidate. First one that answers
        # READ_CPN with 607 wins. Skip Bluetooth/AirPods/debug ports.
        skip_substrings = ("Bluetooth", "debug-console", "wlan-debug")
        for info in list_ports.comports():
            path = info.device
            if any(s in path for s in skip_substrings):
                continue
            if "/cu." not in path and "/tty." not in path and "cu." not in path:
                continue
            try:
                with serial.Serial(path, baudrate=19200, timeout=1) as s:
                    s.write(struct.pack(">b", 0x6D))  # READ_CPN
                    s.flush()
                    raw = s.read(2)
                    if len(raw) != 2:
                        continue
                    cpn = struct.unpack(">h", raw)[0]
                    if cpn == EXPECTED_CPN:
                        return path
            except (serial.SerialException, OSError):
                continue
        return None

    def send_command(self, command_name: str, parameter=None):
        if self.port is None:
            raise RuntimeError("Polygon serial port not open")

        command_dict = self.commands[command_name]
        code = command_dict["command_code"]
        cmd_fmt = command_dict["command_bytes_format"]

        if parameter is not None:
            payload = struct.pack(cmd_fmt, code, parameter)
        else:
            payload = struct.pack(cmd_fmt, code)

        self.port.write(payload)
        self.port.flush()

        resp_fmt = command_dict["response_bytes_format"]
        nbytes = struct.calcsize(resp_fmt)
        if nbytes == 0:
            return None

        raw = self.port.read(nbytes)
        if len(raw) != nbytes:
            return None
        return struct.unpack(resp_fmt, raw)

    def build_info(self) -> str:
        try:
            fw = self.send_command("READ_FIRMWARE_VERSION")
            cid = self.send_command("READ_CID")
            cpn = self.send_command("READ_CPN")
            sn = self.send_command("READ_SN")
            date = self.send_command("READ_BUILD_DATE")
            tm = self.send_command("READ_BUILD_TIME")
            return (
                f"Polygon (CPN {cpn[0] if cpn else '?'}) CID:{cid[0] if cid else '?'} "
                f"SN:{sn} FW:{fw[0]}.{fw[1]}.{fw[2]} "
                f"[Build {b''.join(date).decode(errors='replace')}, "
                f"{b''.join(tm).decode(errors='replace')}]"
            )
        except Exception as err:
            return f"Polygon: <unreadable: {err}>"

    @property
    def tmr1_reload(self) -> int:
        result = self.send_command("READ_TMR1_RELOAD")
        return result[0] if result else 0

    @tmr1_reload.setter
    def tmr1_reload(self, value: int):
        if not (TMR1_MIN <= value <= TMR1_MAX):
            raise ValueError(
                f"TMR1 reload {value} out of range [{TMR1_MIN}, {TMR1_MAX}]"
            )
        self.send_command("WRITE_TMR1_RELOAD", value)

    @property
    def polygon_rev_per_min(self) -> int:
        tmr1 = self.tmr1_reload
        if tmr1 >= 65535:
            return 0
        clock_hz = 5_000_000 / (65535 - tmr1)
        return round(clock_hz / 2 * 60)

    def set_rpm(self, target_rpm: int):
        clock_hz = target_rpm / 60.0 * 2.0
        if clock_hz <= 0:
            raise ValueError("RPM must be positive")
        tmr1 = round(65535 - 5_000_000 / clock_hz)
        self.tmr1_reload = tmr1

    @staticmethod
    def rpm_for_tmr1(tmr1: int) -> int:
        if tmr1 >= 65535:
            return 0
        clock_hz = 5_000_000 / (65535 - tmr1)
        return round(clock_hz / 2 * 60)

    @staticmethod
    def tmr1_for_rpm(rpm: int) -> int:
        clock_hz = rpm / 60.0 * 2.0
        return round(65535 - 5_000_000 / clock_hz)

    def enable_clock(self):
        self.send_command("ENABLE_POLYGON_CLOCK")
        self._clock_enabled = True

    def disable_clock(self):
        self.send_command("DISABLE_POLYGON_CLOCK")
        self._clock_enabled = False

    @property
    def clock_enabled(self) -> bool:
        return self._clock_enabled
