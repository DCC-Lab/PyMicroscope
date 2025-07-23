""" Port USB """
import unittest
import serial
import struct
from serial.tools import list_ports
import binascii
import time
from hardwarelibrary.motion import sutterdevice
from hardwarelibrary.communication.serialport import SerialPort
from pymicroscope.myMicroscope import MicroscopeApp



# CONTROLLER_SERIAL_PATH = "/dev/cu.USA19QW3d1P1.1"
#CONTROLLER_SERIAL_PATH = "/dev/cu.SIDG2TGX"
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

        position = sutter.position()
        print(position)

        #move to position (5, 23, 6)
        sutter.moveTo((5, 23, 6))
        #newposition_in_mycroscope = sutter.positionInMicrosteps()
        #print(newposition_in_mycroscope)
        last_position = sutter.position()
        print(last_position)


            
        #for port, desc, hwid in sutter:
        #    print(f"Port: {port}, Description: {desc}, HWID: {hwid}")

        #self.assertTrue(len(ports_list) > 0)
    @unittest.SkipTest
    def test002_parameter(self):
        microscope_app = MicroscopeApp()
        print(microscope_app.parameters)
        print(type(microscope_app.parameters))



    


if __name__ == "__main__":
    unittest.main()