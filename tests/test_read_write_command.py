""" Port USB """
import unittest
import serial
import struct
from serial.tools import list_ports
import binascii
import time

# CONTROLLER_SERIAL_PATH = "/dev/cu.USA19QW3d1P1.1"
CONTROLLER_SERIAL_PATH = "/dev/cu.usbserial-A907SJ89"


class TestReadWrite(unittest.TestCase):
    def setUp(self):
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
            },
            "WRITE_DAC_INCREMENT": {
                "command_code": 0x7A,
                "command_bytes_format": ">bh",
                "response_bytes_format": "",
                "parameter": self.default_write_parameters["WRITE_DAC_INCREMENT"],
            },
            "WRITE_NUMBER_OF_LINES_FOR_VSYNC": {
                "command_code": 0x6F,
                "command_bytes_format": ">bb",
                "response_bytes_format": "",
                "parameter": self.default_write_parameters[
                    "WRITE_NUMBER_OF_LINES_FOR_VSYNC"
                ],
            },
            "WRITE_NUMBER_OF_LINES_PER_FRAME": {
                "command_code": 0x7C,
                "command_bytes_format": ">bh",
                "response_bytes_format": "",
                "parameter": self.default_write_parameters[
                    "WRITE_NUMBER_OF_LINES_PER_FRAME"
                ],
            },
        }

        try:
            self.port = serial.Serial(CONTROLLER_SERIAL_PATH, baudrate=19200, timeout=3)
            self.port.reset_input_buffer()
            self.port.reset_output_buffer()
        except:
            self.fail(f"Port {CONTROLLER_SERIAL_PATH} not available")
            
    def tearDown(self):
        if self.port is not None:
            self.port.close()

    def test000_init(self):
        self.assertTrue(True)

    @unittest.SkipTest
    def test003_list_ports(self):
        ports_list = serial.tools.list_ports.comports()
        self.assertIsNotNone(ports_list)

        for port_info in ports_list:
            print(f"Device:{port_info.device} vid:{port_info.vid} pid:{port_info.pid}")

        self.assertTrue(len(ports_list) > 0)

    @unittest.SkipTest
    def test005_find_keyspan_port(self):
        KEYSPAN_VID = 1027  # ancienne valeur 1741
        ports_list = serial.tools.list_ports.comports()
        self.assertIsNotNone(ports_list)

        keyspan_ports = []
        for port_info in ports_list:
            if port_info.vid == KEYSPAN_VID:
                keyspan_ports.append(port_info)

        self.assertTrue(len(keyspan_ports) != 0)
        for port_info in keyspan_ports:
            print(f"Device:{port_info.device} vid:{port_info.vid} pid:{port_info.pid}")

    def get_keyspan_ports(self):
        KEYSPAN_VID = 1027  # ancienne valeur 1741
        ports_list = serial.tools.list_ports.comports()

        keyspan_ports = []
        for port_info in ports_list:
            if port_info.vid == KEYSPAN_VID:
                keyspan_ports.append(port_info)

        return keyspan_ports

    def test010_create_serial_port(self):
        possible_ports = self.get_keyspan_ports()

        usable_ports = []
        for port_info in possible_ports:
            try:
                port = serial.Serial(port_info.device, baudrate=19200, timeout=3)
                usable_ports.append(port_info.device)
            except:
                pass

        self.assertTrue(len(usable_ports) > 0)

    def get_usable_ports(self):
        keyspan_ports = self.get_keyspan_ports()

        usable_ports = []
        for port_info in keyspan_ports:
            try:
                port = serial.Serial(port_info.device, baudrate=19200, timeout=3)
                usable_ports.append(port_info.device)
                port.close()
            except:
                pass

        return usable_ports

    def test015_validate_usable_ports(self):
        usable_ports = self.get_usable_ports()
        self.assertTrue(CONTROLLER_SERIAL_PATH in usable_ports)

    @unittest.skip
    def test_060_polygonClockFrequency(self):
        READ_TMR1_RELOAD = [0x75]
        globalTMR1ReloadValue = 60327

        self.port.write(READ_TMR1_RELOAD)  # bizare, à revoir il devrait y en avoir 2
        data_bytes = self.port.read(2)
        self.assertIsNotNone(data_bytes)
        # self.assertEqual(len(data_bytes), 2)
        part_number = struct.unpack("b", data_bytes)[0]  # devrait être <h
        self.assertTrue(part_number == 0)

        #TMR1ReloadValueMinimum = 40535
        #TMR1ReloadValueMaximum = 60327
        #TMR1ReloadValueMostSignificantByte = part_number / 256
        #TMR1ReloadValueLeastSignificantByte = part_number % 256

        polygonClockFrequency = 5000000 / (65535 - part_number)
        # self.assertTrue(polygonClockFrequency == pass)
        if polygonClockFrequency is True:
            minimumiPhotonNumberOfPixelsSupported = 1
            maximumiPhotonNumberOfPixelsSupported = 262144
            iPhotonNumberOfPixelsPerLine = (
                None  # we don't know his value with the mathlab code
            )
            # iPhotonRT 1.1 beta14 has an upper limit of 2048 pixels

            numberOfFacesOfPolygon = 36
            polygonRevolutionsPerMinute = polygonClockFrequency / 2 * 60
            HSyncFrequency = polygonRevolutionsPerMinute * numberOfFacesOfPolygon
            self.assertIsNotNone(HSyncFrequency)
            pixelFrequency = iPhotonNumberOfPixelsPerLine * HSyncFrequency

            maximumPixelFrequency = 20e6
            self.assertTrue(maximumPixelFrequency >= pixelFrequency)
            if pixelFrequency > maximumPixelFrequency:
                raise ValueError("The frequence is to hig")
            else:
                pass

            numberOfLinesPerFrame = 576
            VSyncFrequency = HSyncFrequency / numberOfLinesPerFrame
            self.assertIsNotNone(VSyncFrequency)

            # Polygon clock: %0.1f Hz, HSync: %0.0f Hz, VSync %0.1f Hz, pixel frequency %0.2e Hz

    def test_070_read_write_commands(self):
        for command_name, command_dict in self.commands.items():
            command_code = command_dict["command_code"]
            command_bytes_format = command_dict["command_bytes_format"]
            parameter = command_dict.get("parameter")

            if parameter is not None:
                payload = struct.pack(command_bytes_format, command_code, parameter)
            else:
                payload = struct.pack(command_bytes_format, command_code)

            self.port.write(payload)

            response_bytes_format = command_dict["response_bytes_format"]
            bytes_returned = struct.calcsize(response_bytes_format)
            if bytes_returned != 0:
                response_bytes = self.port.read(bytes_returned)
                self.assertEqual(
                    len(response_bytes),
                    bytes_returned,
                    f"Response wrong length for {command_name}",
                )
                unpacked_response = struct.unpack(response_bytes_format, response_bytes)
                self.assertIsNotNone(unpacked_response)
                # print(f"{command_name}, {unpacked_response}")


if __name__ == "__main__":
    unittest.main()
