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
        self.read_commands = {
            "READ_FIRMWARE_VERSION": {
                "command_code": 0x7F,
                "bytes_returned": 3,
                "bytes_format": "3b",
            },
            "READ_CID": {
                "command_code": 0x6C,
                "bytes_returned": 2,
                "bytes_format": "2b",
            },
            "READ_CPN": {
                "command_code": 0x6D,
                "bytes_returned": 2,
                "bytes_format": ">h",
            },
            "READ_SN": {
                "command_code": 0x6B,
                "bytes_returned": 2,
                "bytes_format": "2b",
            },
            "READ_STATE_OF_SWITCHES_AND_TTL_IOS": {
                "command_code": 0x7E,
                "bytes_returned": 1,
                "bytes_format": "B",
            },
            "READ_BUILD_TIME": {
                "command_code": 0x6A,
                "bytes_returned": 9,
                "bytes_format": "8cx",
            },
            "READ_BUILD_DATE": {
                "command_code": 0x69,
                "bytes_returned": 11,
                "bytes_format": "11c",
            },
            "READ_NUMBER_OF_LINES_PER_FRAME": {
                "command_code": 0x74,
                "bytes_returned": 2,
                "bytes_format": ">h",
            },
            "READ_DAC_START": {
                "command_code": 0x73,
                "bytes_returned": 2,
                "bytes_format": ">h",
            },
            "READ_DAC_INCREMENT": {
                "command_code": 0x72,
                "bytes_returned": 2,
                "bytes_format": ">h",
            },
            "READ_NUMBER_OF_LINES_FOR_VSYNC": {
                "command_code": 0x6E,
                "bytes_returned": 2,
                "bytes_format": ">h",
            },
        }

        self.default_write_parameters = {
            "WRITE_DAC_START": 19200,
            "WRITE_DAC_INCREMENT": 32,
            "WRITE_NUMBER_OF_LINES_FOR_VSYNC": 6,
            "WRITE_NUMBER_OF_LINES_PER_FRAME": 576,
        }

        self.write_commands = {
            "WRITE_DAC_START": {
                "command_code": 0x7B,
                "bytes_format": ">bh",
                "parameter": self.default_write_parameters["WRITE_DAC_START"],
            },
            "WRITE_DAC_INCREMENT": {
                "command_code": 0x7A,
                "bytes_format": ">bh",
                "parameter": self.default_write_parameters["WRITE_DAC_INCREMENT"],
            },
            "WRITE_NUMBER_OF_LINES_FOR_VSYNC": {
                "command_code": 0x6F,
                "bytes_format": ">bb",
                "parameter": self.default_write_parameters[
                    "WRITE_NUMBER_OF_LINES_FOR_VSYNC"
                ],
            },
            "WRITE_NUMBER_OF_LINES_PER_FRAME": {
                "command_code": 0x7C,
                "bytes_format": ">bh",
                "parameter": self.default_write_parameters[
                    "WRITE_NUMBER_OF_LINES_PER_FRAME"
                ],
            },
        }

        self.port = serial.Serial(CONTROLLER_SERIAL_PATH, baudrate=19200, timeout=3)
        self.port.reset_input_buffer()
        self.port.reset_output_buffer()

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

    def test020_read_firmware_version(self):
        READ_FIRMWARE_VERSION_BYTES = [0x7F]

        self.port.write(READ_FIRMWARE_VERSION_BYTES)

        firmware_version_data = self.port.read(3)
        self.assertIsNotNone(firmware_version_data)

        self.assertTrue(firmware_version_data[0] == 4)
        self.assertTrue(firmware_version_data[1] == 0)
        self.assertTrue(firmware_version_data[2] == 0)

    def test030_read_cid(self):
        READ_CID = [0x6C]

        self.port.write(READ_CID)
        cid_data = self.port.read(2)
        self.assertIsNotNone(cid_data)
        self.assertTrue(cid_data[0] == 0)
        self.assertTrue(cid_data[1] == 0)

    @unittest.SkipTest
    def test045_read_all_command(self):
        usable_ports = self.get_usable_ports()
        self.assertTrue(CONTROLLER_SERIAL_PATH in usable_ports)

        READ_FIRMWARE_VERSION = [0x7F]
        READ_CID = [0x6C]
        READ_CPN = [0x6D]
        READ_SN = [0x6B]
        READ_EEPROM_ADDRESS = [0x76]
        READ_STATE_OF_SWITCHES_AND_TTL_IOS = [0x7E]
        READ_BUILD_TIME = [0x6A]
        READ_BUILD_DATE = [0x69]
        READ_TMR1_RELOAD = [0x75]
        READ_NUMBER_OF_LINES_PER_FRAME = [0x74]
        READ_DAC_START = [0x73]
        READ_DAC_INCREMENT = [0x72]
        READ_NUMBER_OF_LINES_FOR_VSYNC = [0x6E]

        self.port.write(READ_FIRMWARE_VERSION)
        data_bytes = self.port.read(3)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack("3b", data_bytes)
        self.assertTrue(part_number == (4, 0, 0))  # b'\x02\x00\x00'

        self.port.write(READ_CID)
        data_bytes = self.port.read(2)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack("2b", data_bytes)
        self.assertTrue(part_number == (0, 0))  # b'\x00\x00'

        self.port.write(READ_CPN)
        data_bytes = self.port.read(2)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack(">h", data_bytes)[
            0
        ]  # j'aurais mis un p ou un c pas h
        self.assertTrue(part_number == 522)

        self.port.write(READ_SN)
        data_bytes = self.port.read(2)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack("2b", data_bytes)
        self.assertTrue(part_number == (0, 0))  # b'\x00\x00'

        # self.port.write(READ_EEPROM_ADDRESS)
        # data_bytes = self.port.read(1)
        # if self.assertIsNotNone(data_bytes):
        #    part_number = struct.unpack("c", data_bytes)
        #    self.assertTrue(part_number == "")
        # else:
        #    pass

        self.port.write(READ_STATE_OF_SWITCHES_AND_TTL_IOS)
        data_bytes = self.port.read(1)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack("B", data_bytes)[0]
        self.assertTrue(part_number == 255)

        self.port.write(READ_BUILD_TIME)
        data_bytes = self.port.read(9)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack("8cx", data_bytes)
        time_building = b"".join(part_number)
        self.assertTrue(len(time_building) == 8)

        self.port.write(READ_BUILD_DATE)
        data_bytes = self.port.read(11)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack("11c", data_bytes)
        date_building = b"".join(part_number)
        self.assertTrue(date_building == b"Feb 06 2012")

        self.port.write(READ_TMR1_RELOAD)  # bizare, à revoir il devrait y en avoir 2
        data_bytes = self.port.read(2)
        self.assertIsNotNone(data_bytes)
        # print(data_bytes)
        part_number = struct.unpack("b", data_bytes)[0]  # devrait être >h
        self.assertTrue(part_number == 0)
        # print(part_number)

        self.port.write(READ_NUMBER_OF_LINES_PER_FRAME)
        data_bytes = self.port.read(2)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack(">h", data_bytes)[0]
        self.assertTrue(part_number == 540)  # doit être entre [36, 65520]

        # To review the necessity of calculate it
        # numberOfLinesPerFrameMostSignificantByte = part_number / 256
        # numberOfLinesPerFrameLeastSignificantByte = part_number % 256

        self.port.write(READ_DAC_START)
        data_bytes = self.port.read(2)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack(">h", data_bytes)[0]
        self.assertTrue(part_number == 26288)

        self.port.write(READ_DAC_INCREMENT)
        data_bytes = self.port.read(2)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack(">h", data_bytes)[0]
        self.assertTrue(part_number == 24)

        self.port.write(READ_NUMBER_OF_LINES_FOR_VSYNC)
        data_bytes = self.port.read(2)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack(">h", data_bytes)[0]
        self.assertTrue(part_number == 6)  # doit être entre [1, 575]

        # To review the necessity of calculate it
        # numberOfLinesForVSyncMostSignificantByte = part_number/ 256
        # numberOfLinesForVSyncLeastSignificantByte = part_number % 256

    def test050_read_commands(self):
        for command_name, command_dict in self.read_commands.items():
            command_code = command_dict["command_code"]
            bytes_returned = command_dict["bytes_returned"]
            bytes_format = command_dict["bytes_format"]

            payload = struct.pack(">b", command_code)
            self.port.write(payload)
            data_bytes = self.port.read(bytes_returned)
            self.assertIsNotNone(data_bytes)
            self.assertTrue(
                len(data_bytes) == bytes_returned,
                f"Command {command_name} failed, incorrect number of bytes: received {len(data_bytes)}, expected {bytes_returned}",
            )
            unpacked_response = struct.unpack(bytes_format, data_bytes)
            self.assertIsNotNone(unpacked_response)

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

        TMR1ReloadValueMinimum = 40535
        TMR1ReloadValueMaximum = 60327
        TMR1ReloadValueMostSignificantByte = part_number / 256
        TMR1ReloadValueLeastSignificantByte = part_number % 256

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

    def test_070_write_commands(self):
        for command_name, command_dict in self.write_commands.items():
            command_code = command_dict["command_code"]
            bytes_format = command_dict["bytes_format"]
            parameter = command_dict["parameter"]

            payload = struct.pack(bytes_format, command_code, parameter)
            bytes_description = [f"{b:x}" for b in payload]
            self.port.write(payload)
            response_bytes = self.port.read()
            self.assertIsNotNone(response_bytes)
            self.assertEqual(response_bytes, b"")


if __name__ == "__main__":
    unittest.main()
