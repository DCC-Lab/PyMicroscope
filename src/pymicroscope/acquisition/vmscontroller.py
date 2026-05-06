""" Port USB """
import serial
import struct
from serial.tools import list_ports
import binascii
import time


# CONTROLLER_SERIAL_PATH = "/dev/cu.USA19QW3d1P1.1"
CONTROLLER_SERIAL_PATH = "/dev/cu.usbserial-A907SJ89"

VMS_EXPECTED_CPN = 522


class VMSController:
    def __init__(self, serial_path: str | None = None):
        self.serial_path = serial_path or CONTROLLER_SERIAL_PATH
        self.default_write_parameters = {
            "WRITE_DAC_START": 19200,
            "WRITE_DAC_INCREMENT": 32,
            "WRITE_NUMBER_OF_LINES_FOR_VSYNC": 6,
            "WRITE_NUMBER_OF_LINES_PER_FRAME": 576,
        }
        self.default_other_parameters = {"Number_Of_Faces_Of_Polygon": 36, "TMR1_Reload_Value": 60327, "PixelsPerLine": 1024}

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
            "READ_STATE_OF_SWITCHES_AND_TTL_IOS": {
                "command_code": 0x7E,
                "command_bytes_format": ">b",
                "response_bytes_format": "B",
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
            "READ_NUMBER_OF_LINES_PER_FRAME": {
                "command_code": 0x74,
                "command_bytes_format": ">b",
                "response_bytes_format": ">h",
            },
            "READ_DAC_START": {
                "command_code": 0x73,
                "command_bytes_format": ">b",
                "response_bytes_format": ">h",
            },
            "READ_DAC_INCREMENT": {
                "command_code": 0x72,
                "command_bytes_format": ">b",
                "response_bytes_format": ">h",
            },
            "READ_NUMBER_OF_LINES_FOR_VSYNC": {
                "command_code": 0x6E,
                "command_bytes_format": ">b",
                "response_bytes_format": ">h",
            },
            "WRITE_DAC_START": {
                "command_code": 0x7B,
                "command_bytes_format": ">bh",
                "response_bytes_format": "",
                "parameter": self.default_write_parameters["WRITE_DAC_START"],
                "minimum": 0,
                "maximum": 65535,
            },
            "WRITE_DAC_INCREMENT": {
                "command_code": 0x7A,
                "command_bytes_format": ">bh",
                "response_bytes_format": "",
                "parameter": self.default_write_parameters["WRITE_DAC_INCREMENT"],
                "minimum": 0,
                "maximum": 65535,
            },
            "WRITE_NUMBER_OF_LINES_FOR_VSYNC": {
                "command_code": 0x6F,
                "command_bytes_format": ">bh",
                "response_bytes_format": "",
                "parameter": self.default_write_parameters["WRITE_NUMBER_OF_LINES_FOR_VSYNC"],
                "minimum": 1,
                "maximum": 575,
            },
            "WRITE_NUMBER_OF_LINES_PER_FRAME": {
                "command_code": 0x7C,
                "command_bytes_format": ">bh",
                "response_bytes_format": "",
                "parameter": self.default_write_parameters["WRITE_NUMBER_OF_LINES_PER_FRAME"],
                "minimum": 36,
                "maximum": 65520,
            },
        }

        self.port = None
        self.is_accessible = False
        
    def initialize(self):
        path = self.serial_path or self._auto_discover()
        if path is None:
            raise RuntimeError("No candidate serial port found for VMS circuit")

        self.port = serial.Serial(path, baudrate=19200, timeout=3)
        self.serial_path = path

        version = self.send_command("READ_FIRMWARE_VERSION")
        if version is None or version[0] != 4:
            self.port.close()
            self.port = None
            raise RuntimeError("Unrecognized firmware version on controller")

        cpn = self.send_command("READ_CPN")
        if cpn is None or cpn[0] != VMS_EXPECTED_CPN:
            self.port.close()
            self.port = None
            raise RuntimeError(
                f"VMS circuit on {path} reported CPN={cpn} (expected {VMS_EXPECTED_CPN})"
            )

        self.is_accessible = True

    def _auto_discover(self):
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
                    if cpn == VMS_EXPECTED_CPN:
                        return path
            except (serial.SerialException, OSError):
                continue
        return None

    def shutdown(self):
        if self.port is not None:
            self.port.close()
        self.is_accessible = False

    def build_info(self):
        fw = self.send_command("READ_FIRMWARE_VERSION")
        cid = self.send_command("READ_CID")
        cpn = self.send_command("READ_CPN")
        serial_number = self.send_command("READ_SN")
        build_time = self.send_command("READ_BUILD_TIME")
        build_date = self.send_command("READ_BUILD_DATE")
        return f"VMS Controller: CID: {cid[0]}, CPN: {cpn[0]}, Serial #: {serial_number},\nFireware version: {fw[0]}.{fw[1]}.{fw[2]} [Build: {b''.join(build_date).decode()}, {b''.join(build_time).decode()}]\n"

    def send_command(self, command_name, parameter=None):
        command_dict = self.commands[command_name]

        command_code = command_dict["command_code"]
        command_bytes_format = command_dict["command_bytes_format"]

        if parameter is not None:
            payload = struct.pack(command_bytes_format, command_code, parameter)
        else:
            payload = struct.pack(command_bytes_format, command_code)

        self.port.write(payload)
        self.port.flush()

        response_bytes_format = command_dict["response_bytes_format"]
        bytes_returned = struct.calcsize(response_bytes_format)
        unpacked_response = None
        if bytes_returned != 0:
            response_bytes = self.port.read(bytes_returned)
            unpacked_response = struct.unpack(
                response_bytes_format, response_bytes
            )

        return unpacked_response


    def parameters_are_valid(self, parameters):
        is_valid = {}

        for parameter_name, values in parameters.items():
            command_dict = self.commands[parameter_name]
            minimum = command_dict["minimum"]
            maximum = command_dict["maximum"]

            if minimum <= values <= maximum:
                is_valid[parameter_name] = None  # OK
            else:
                is_valid[parameter_name] = (minimum, maximum)  # Erreur

        return is_valid

    def apply_settings(self, settings: dict):
        """Atomically write a coherent set of VMS parameters.

        Validates against parameters_are_valid first; raises ValueError if any
        value is out of range. Only writes the WRITE_* keys present in settings.
        """
        write_keys = {
            "WRITE_DAC_START",
            "WRITE_DAC_INCREMENT",
            "WRITE_NUMBER_OF_LINES_FOR_VSYNC",
            "WRITE_NUMBER_OF_LINES_PER_FRAME",
        }
        to_write = {k: v for k, v in settings.items() if k in write_keys}
        validation = self.parameters_are_valid(to_write)
        bad = {k: v for k, v in validation.items() if v is not None}
        if bad:
            raise ValueError(f"Out-of-range VMS settings: {bad}")

        # Order: line counts before dac so geometry is consistent
        for key in (
            "WRITE_NUMBER_OF_LINES_PER_FRAME",
            "WRITE_NUMBER_OF_LINES_FOR_VSYNC",
            "WRITE_DAC_START",
            "WRITE_DAC_INCREMENT",
        ):
            if key in to_write:
                self.send_command(key, to_write[key])

    @property
    def lines_per_frame(self):
        return self.send_command("READ_NUMBER_OF_LINES_PER_FRAME")[0]

    @lines_per_frame.setter
    def lines_per_frame(self, value):
        self.send_command("WRITE_NUMBER_OF_LINES_PER_FRAME", value)

    @property
    def lines_for_vsync(self):
        return self.send_command("READ_NUMBER_OF_LINES_FOR_VSYNC")[0]

    @lines_for_vsync.setter
    def lines_for_vsync(self, value):
        self.send_command("WRITE_NUMBER_OF_LINES_FOR_VSYNC", value)

    @property
    def dac_start(self):
        return self.send_command("READ_DAC_START")[0]

    @dac_start.setter
    def dac_start(self, value):
        self.send_command("WRITE_DAC_START", value)

    @property
    def dac_increment(self):
        return self.send_command("READ_DAC_INCREMENT")[0]

    @dac_increment.setter
    def dac_increment(self, value):
        self.send_command("WRITE_DAC_INCREMENT", value)

    # TMR1 / polygon-clock derived rates live on PolygonController; the
    # synchronisation maths (hsync / vsync / pixel frequency) is computed
    # in the diagnostic GUI from the polygon RPM and the active line counts.
