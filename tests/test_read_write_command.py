""" Port USB """
import unittest
import serial
import struct
from serial.tools import list_ports

import time

#CONTROLLER_SERIAL_PATH = "/dev/cu.USA19QW3d1P1.1"
CONTROLLER_SERIAL_PATH = "/dev/cu.usbserial-A907SJ89"

class TestReadWrite(unittest.TestCase):
    def test000_init(self):
        self.assertTrue(True)

    def test003_list_ports(self):

        ports_list = serial.tools.list_ports.comports()
        self.assertIsNotNone(ports_list)
        #print(ports_list)

        #ftdi_ports = []
        for port_info in ports_list:
            print(f"Device:{port_info.device} vid:{port_info.vid} pid:{port_info.pid}")

        self.assertTrue(len(ports_list) > 0)

    def test005_find_keyspan_port(self):
        KEYSPAN_VID = 1027          # ancienne valeur 1741
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
        KEYSPAN_VID = 1027          # ancienne valeur 1741
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
                port = serial.Serial(port_info.device, baudrate=19200, timeout=0.5)
                usable_ports.append(port_info.device)            
            except:
                pass            

        self.assertTrue(len(usable_ports) > 0)


    def get_usable_ports(self):
        keyspan_ports = self.get_keyspan_ports()

        usable_ports = []
        for port_info in keyspan_ports:
            try:
                port = serial.Serial(port_info.device, baudrate=19200, timeout=0.5)
                usable_ports.append(port_info.device)
                port.close()
            except:
                pass            

        return usable_ports
  
    def test015_validate_usable_ports(self):
        usable_ports = self.get_usable_ports()
        self.assertTrue(CONTROLLER_SERIAL_PATH in usable_ports)
    
    def test020_read_firmware_version(self):
        usable_ports = self.get_usable_ports()
        self.assertTrue(CONTROLLER_SERIAL_PATH in usable_ports)

        READ_FIRMWARE_VERSION_BYTES = [0x7f]

        port = serial.Serial(CONTROLLER_SERIAL_PATH, baudrate=19200, timeout=0.5)
        
        port.write(READ_FIRMWARE_VERSION_BYTES)

        firmware_version_data = port.read(3)
        self.assertIsNotNone(firmware_version_data)
        
        self.assertTrue(firmware_version_data[0] == 4)
        self.assertTrue(firmware_version_data[1] == 0)
        self.assertTrue(firmware_version_data[2] == 0)
    
    def test030_read_cid(self):
        usable_ports = self.get_usable_ports()
        self.assertTrue(CONTROLLER_SERIAL_PATH in usable_ports)

        READ_CID = [0x6c]

        port = serial.Serial(CONTROLLER_SERIAL_PATH, baudrate=19200, timeout=0.5)
        
        port.write(READ_CID)
        cid_data = port.read(2)
        self.assertIsNotNone(cid_data)
        self.assertTrue(cid_data[0] == 0)
        self.assertTrue(cid_data[1] == 0)

    def test040_read_cpn(self):
        usable_ports = self.get_usable_ports()
        self.assertTrue(CONTROLLER_SERIAL_PATH in usable_ports)

        READ_CPN = [0x6d]

        port = serial.Serial(CONTROLLER_SERIAL_PATH, baudrate=19200, timeout=0.5)
        
        port.write(READ_CPN)
        data_bytes = port.read(2)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack(">h", data_bytes)
        self.assertTrue(part_number == 522)


    def test045_read_all_command(self):
        usable_ports = self.get_usable_ports()
        self.assertTrue(CONTROLLER_SERIAL_PATH in usable_ports)

        READ_FIRMWARE_VERSION = [0x7f]
        READ_CID = [0x6c]
        READ_CPN = [0x6d] 
        READ_SN = [0x6b]
        READ_EEPROM_ADDRESS = [0x76]
        READ_STATE_OF_SWITCHES_AND_TTL_IOS = [0x7e]
        READ_BUILD_TIME = [0x6a]
        READ_BUILD_DATE = [0x69]
        READ_TMR1_RELOAD = [0x75]
        READ_NUMBER_OF_LINES_PER_FRAME = [0x74]
        READ_DAC_START = [0x73]
        READ_DAC_INCREMENT = [0x72]
        READ_NUMBER_OF_LINES_FOR_VSYNC = [0x6e]

        port = serial.Serial(CONTROLLER_SERIAL_PATH, baudrate=19200, timeout=0.5)
        

        port.write(READ_FIRMWARE_VERSION)
        data_bytes = port.read(3)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack(">3h", data_bytes)
        self.assertTrue(part_number == (4, 0, 0))    #b'\x02\x00\x00'

        port.write(READ_CID)
        data_bytes = port.read(2)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack("2b", data_bytes)
        self.assertTrue(part_number == (0, 0))    #b'\x00\x00'

        port.write(READ_CPN)
        data_bytes = port.read(2)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack(">h", data_bytes) # j'aurais mis un p ou un c pas h
        self.assertTrue(part_number == 522)

        port.write(READ_SN)
        data_bytes = port.read(2)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack("2b", data_bytes)
        self.assertTrue(part_number == (0, 0))    #b'\x00\x00'

        port.write(READ_EEPROM_ADDRESS)
        data_bytes = port.read(1)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack("b", data_bytes)
        self.assertTrue(part_number == pass)

        port.write(READ_STATE_OF_SWITCHES_AND_TTL_IOS)
        data_bytes = port.read(1)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack("b", data_bytes)
        self.assertTrue(part_number == 0)

        port.write(READ_BUILD_TIME)
        data_bytes = port.read(9)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack("8cP", data_bytes)
        time_building = part_number.decode('utf-8')
        self.assertTrue(len(time_building) == 8)

        port.write(READ_BUILD_DATE)
        data_bytes = port.read(11)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack("3c2xc2x4cP", data_bytes)
        date_building = part_number.decode('utf-8')
        self.assertTrue(len(date_building) == 10)

        port.write(READ_TMR1_RELOAD)
        data_bytes = port.read(2)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack("2c", data_bytes)
        TMR1ReloadValue = part_number[0] * 256 + part_number[1]
        polygonClockFrequency = 5000000 / (65535 - TMR1ReloadValue)
        self.assertTrue(part_number == pass)
        self.assertTrue(polygonClockFrequency == pass)

        port.write(READ_NUMBER_OF_LINES_PER_FRAME)
        data_bytes = port.read(2)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack("2c", data_bytes)
        numberOfLines = part_number[0] * 256 + part_number[1]
        self.assertTrue(numberOfLines == pass)

        port.write(READ_DAC_START)
        data_bytes = port.read(2)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack("2c", data_bytes)
        dac_start = part_number[0] * 256 + part_number[1]
        self.assertTrue(dac_start == pass)

        port.write(READ_DAC_INCREMENT)
        data_bytes = port.read(2)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack("2c", data_bytes)
        dac_increment = part_number[0] * 256 + part_number[1]
        self.assertTrue(dac_increment == pass)

        port.write(READ_NUMBER_OF_LINES_FOR_VSYNC)
        data_bytes = port.read(2)
        self.assertIsNotNone(data_bytes)
        part_number = struct.unpack("2c", data_bytes)
        numberOfLines = part_number[0] * 256 + part_number[1]
        self.assertTrue(numberOfLines == pass)


    

    def test050_many_commands(self):
        try :
            port = serial.Serial(CONTROLLER_SERIAL_PATH, baudrate=19200, timeout=0.5)
        except serial.SerialException as err:
            self.fail(f"Unable to open port : {CONTROLLER_SERIAL_PATH}. Verify that device is connected to your computer.")

        all_commands = { "READ_FIRMWARE_VERSION" : {"command_bytes":[0x7f], "bytes_returned":3, "format":""},
                         "READ_CID" : {"command_bytes":[0x6c], "bytes_returned":2, "format":""},
                         "READ_CPN" : {"command_bytes":[0x6d], "bytes_returned":2, "format":">h"},
                         "READ_SN" : {"command_bytes":[0x6b], "bytes_returned":2, "format":""},
                         "READ_EEPROM_ADDRESS" : {"command_bytes":[0x76], "bytes_returned":1, "format":""},
                         "READ_STATE_OF_SWITCHES_AND_TTL_IOS" : {"command_bytes":[0x7e], "bytes_returned":1, "format":""},
                         "READ_BUILD_TIME" : {"command_bytes":[0x6a], "bytes_returned":9, "format":""},
                         "READ_BUILD_DATE" : {"command_bytes":[0x69], "bytes_returned":11, "format":""},
                         "READ_TMR1_RELOAD" : {"command_bytes":[0x75], "bytes_returned":2, "format":""},
                         "READ_NUMBER_OF_LINES_PER_FRAME" : {"command_bytes":[0x74], "bytes_returned":2, "format":""},
                         "READ_DAC_START" : {"command_bytes":[0x73], "bytes_returned":2, "format":""},
                         "READ_DAC_INCREMENT" : {"command_bytes":[0x72], "bytes_returned":2, "format":""},
                         "READ_NUMBER_OF_LINES_FOR_VSYNC" : {"command_bytes":[0x6e], "bytes_returned":2, "format":""}
                     }

        for command_name, command_dict in all_commands.items():
            command_bytes = command_dict['command_bytes']
            bytes_returned = command_dict['bytes_returned']

            port.write(command_bytes)
            data_bytes = port.read(bytes_returned)
            self.assertIsNotNone(data_bytes)
            self.assertIsNotNone(len(data_bytes) == bytes_returned)
            print(f"Testing {command_name}: returned {data_bytes}")
            

if __name__ == "__main__":
    unittest.main()

