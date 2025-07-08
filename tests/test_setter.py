""" Port USB """
import unittest
import serial
import struct
from serial.tools import list_ports
import binascii
import time

# CONTROLLER_SERIAL_PATH = "/dev/cu.USA19QW3d1P1.1"
#CONTROLLER_SERIAL_PATH = 


class TestReadWrite(unittest.TestCase):
    #def setUp(self):
    #    self.port = serial.Serial(CONTROLLER_SERIAL_PATH, baudrate=19200, timeout=3)
    #    self.port.reset_input_buffer()
    #    self.port.reset_output_buffer()

    #def tearDown(self):
    #    if self.port is not None:
    #        self.port.close()

    #@unittest.SkipTest
    def test003_list_ports(self):
        ports_list = serial.tools.list_ports.comports()
        self.assertIsNotNone(ports_list)
        print(ports_list)

        for port_info in ports_list:
            print(f"Device:{port_info.device} vid:{port_info.vid} pid:{port_info.pid}")

        self.assertTrue(len(ports_list) > 0)



if __name__ == "__main__":
    unittest.main()