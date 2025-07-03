""" Port USB """
import serial
import struct
from serial.tools import list_ports
import binascii
import time


# CONTROLLER_SERIAL_PATH = "/dev/cu.USA19QW3d1P1.1"
CONTROLLER_SERIAL_PATH = "/dev/cu.usbserial-A907SJ89"


class VMSController:
    def __init__(self):
        self.default_write_parameters = {
            "WRITE_DAC_START": 19200,
            "WRITE_DAC_INCREMENT": 32,
            "WRITE_NUMBER_OF_LINES_FOR_VSYNC": 6,
            "WRITE_NUMBER_OF_LINES_PER_FRAME": 576,
        }

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

    def initialize(self):
        self.port = serial.Serial(
            CONTROLLER_SERIAL_PATH, baudrate=19200, timeout=3
        )

        version = self.send_command("READ_FIRMWARE_VERSION")
        if version[0] != 4:
            raise RuntimeError("Unrecognized firmware version on controller")

        # print(self.build_info())

    def shutdown(self):
        if self.port is not None:
            self.port.close()

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

            if minimum < values < maximum:
                is_valid[parameter_name] = None  # OK
            else:
                is_valid[parameter_name] = (minimum, maximum)  # Erreur

        return is_valid

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
