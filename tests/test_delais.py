import unittest
from mytk import *
import pylablib
import Thorpy
from pylablib.devices.Thorlabs import kinesis
from thorlabs_apt_device import APTDevice
from thorlabs_apt_device.devices import TDC001
from thorlabs_apt_device.enums import EndPoint, LEDMode
import numpy as np
import serial
from serial.tools import list_ports
from hardwarelibrary.communication.usbport import USBPort



CONTROLLER_SERIAL_PATH = "/dev/cu.wlan-debug"

class TestDelais(unittest.TestCase):
    def setUp(self):
        self.init_thorlabs = APTDevice()
        self.init_thorlabs.__init__()
        self.port = serial.Serial(CONTROLLER_SERIAL_PATH, baudrate=19200, timeout=3)
        self.port.reset_input_buffer()
        self.port.reset_output_buffer()
        self.thorpy = Thorpy()


    def tearDown(self):
        if self.init_thorlabs is not None:
            self.init_thorlabs.close()
        if self.port is not None:
            self.port.close()

    @unittest.SkipTest
    def test010_list_ports(self):
        ports_list = serial.tools.list_ports.comports()
        self.assertIsNotNone(ports_list)

        for port_info in ports_list:
            print(f"Device:{port_info.device} vid:{port_info.vid} pid:{port_info.pid}")

        self.assertTrue(len(ports_list) > 0)

    @unittest.SkipTest
    def test020_list_kinesis_device(self):
        list = kinesis.list_kinesis_devices()
        print(list)

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

    @unittest.SkipTest
    def test002_find_device(self):
        self.assertTrue(self.init_thorlabs)
        print(self.init_thorlabs)

    @unittest.SkipTest
    def test003_information_device(self):
        print(self.init_thorlabs._log)

        print(self.init_thorlabs._port)

        print(self.init_thorlabs.controller, self.init_thorlabs.bays, self.init_thorlabs.channels)

    @unittest.SkipTest
    def test004_commande(self):
        self.init_thorlabs._write(LEDMode.MOVING)    


if __name__ == "__main__":
    unittest.main()
