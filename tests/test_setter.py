""" Port USB """
import unittest
import serial
import struct
from serial.tools import list_ports
import binascii
import time
from hardwarelibrary.motion import sutterdevice
from hardwarelibrary.communication.serialport import SerialPort



# CONTROLLER_SERIAL_PATH = "/dev/cu.USA19QW3d1P1.1"
#CONTROLLER_SERIAL_PATH = 
#id_setter = SIDG2TGX

class Sutter(unittest.TestCase):
    #def setUp(self):
    #    self.port = serial.Serial(CONTROLLER_SERIAL_PATH, baudrate=19200, timeout=3)
    #    self.port.reset_input_buffer()
    #    self.port.reset_output_buffer()

    #def tearDown(self):
    #    if self.port is not None:
    #        self.port.close()

    #@unittest.SkipTest
    def test000_list_ports(self):
        sutter = sutterdevice.SutterDevice(serialNumber="debug")
        self.assertIsNotNone(sutter)
        #print(sutter.idVendor)
        sutter.doInitializeDevice()
        print(sutter)
        #ports_list = serial.tools.list_ports.comports()
        #self.assertIsNotNone(ports_list)
        #print(ports_list)

        position = sutter.doGetPosition()
        print(position)

        #move to position (5, 23, 6)
        move = sutter.moveTo((5, 23, 6))
        print(position)
        print(move)
        if move == None:
            print("the value didn't move")
            
        #for port, desc, hwid in sutter:
        #    print(f"Port: {port}, Description: {desc}, HWID: {hwid}")

        #self.assertTrue(len(ports_list) > 0)
    


if __name__ == "__main__":
    unittest.main()