""" Port USB """
import unittest
import serial
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
        cpn_data = port.read(2)
        self.assertIsNotNone(cpn_data)
        self.assertTrue(cpn_data[0] == 2)
        self.assertTrue(cpn_data[1] == 10)
    

    def test050_many_commands(self):
        try :
            port = serial.Serial(CONTROLLER_SERIAL_PATH, baudrate=19200, timeout=0.5)
        except serial.SerialException as err:
            self.fail(f"Unable to open port : {CONTROLLER_SERIAL_PATH}. Verify that device is connected to your computer.")

        all_commands = { "READ_FIRMWARE_VERSION" : {"command_bytes":[0x7f], "bytes_returned":3},
                         "READ_CID" : {"command_bytes":[0x6c], "bytes_returned":2},
                         "READ_CPN" : {"command_bytes":[0x6d], "bytes_returned":2},
                         "READ_SN" : {"command_bytes":[0x6b], "bytes_returned":2},
                         "READ_EEPROM_ADDRESS" : {"command_bytes":[0x76], "bytes_returned":1},
                         "READ_STATE_OF_SWITCHES_AND_TTL_IOS" : {"command_bytes":[0x7e], "bytes_returned":1},
                         "READ_BUILD_TIME" : {"command_bytes":[0x6a], "bytes_returned":9},
                         "READ_BUILD_DATE" : {"command_bytes":[0x69], "bytes_returned":11},
                         "READ_TMR1_RELOAD" : {"command_bytes":[0x75], "bytes_returned":2},
                         "READ_NUMBER_OF_LINES_PER_FRAME" : {"command_bytes":[0x74], "bytes_returned":2},
                         "READ_DAC_START" : {"command_bytes":[0x73], "bytes_returned":2},
                         "READ_DAC_INCREMENT" : {"command_bytes":[0x72], "bytes_returned":2},
                         "READ_NUMBER_OF_LINES_FOR_VSYNC" : {"command_bytes":[0x6e], "bytes_returned":2}
                     }

        for command_name, command_dict in all_commands.items():
            command_bytes = command_dict['command_bytes']
            bytes_returned = command_dict['bytes_returned']

            port.write(command_bytes)
            cpn_data = port.read(bytes_returned)
            self.assertIsNotNone(cpn_data)
            self.assertIsNotNone(len(cpn_data) == bytes_returned)
            print(f"Testing {command_name}: returned {cpn_data}")
            

if __name__ == "__main__":
    unittest.main()

