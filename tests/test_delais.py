import unittest
from mytk import *
#import pylablib
#from pylablib.devices.Thorlabs import
from thorlabs_apt_device import APTDevice
import numpy as np
import serial
from serial.tools import list_ports
from hardwarelibrary.communication.usbport import USBPort

class TestDelais(unittest.TestCase):
    @unittest.SkipTest
    def test000_init(self):
        usb_port = USBPort()
        self.assertTrue(usb_port)
        devices = usb_port.allDevices()
        print(devices)

    @unittest.SkipTest
    def test001_port(self):
        ports_list = serial.tools.list_ports.comports()
        self.assertIsNotNone(ports_list)
        print(ports_list)

    #@unittest.SkipTest
    def test002_find_device(self):
        init_thorlabs = APTDevice()
        self.assertTrue(init_thorlabs)
        print(init_thorlabs)

    def test003_connection(self):
        init_thorlabs = APTDevice()
        self.assertTrue(init_thorlabs)
        print(init_thorlabs)
        init_thorlabs.close()
    


if __name__ == "__main__":
    unittest.main()
