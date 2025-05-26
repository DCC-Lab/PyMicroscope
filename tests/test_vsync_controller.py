import unittest
import serial
from unittest.mock import patch
from unittest.mock import MagicMock


class MyMockTest(unittest.TestCase):
    @patch("serial.Serial")
    def test000_understanding_mock(self, SerialMock):
        port = serial.Serial(
            port="COM1",
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0,
        )

        self.assertIsNotNone(port)
        self.assertTrue(port is SerialMock.return_value)
        for key, value in SerialMock.call_args.kwargs.items():
            print(key, value)


path = "/dev/cu.USA19QW3d1P1.1"


class VSYNCTestCase(unittest.TestCase):
    @patch("serial.Serial")
    def test000_init(self, SerialMock):
        SerialMock.return_value.is_open = True

        port = serial.Serial(
            port=path,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0,
        )

        self.assertIsNotNone(port)
        self.assertEqual(port.is_open, True)
        port.close()


#     # def test005_ports(self):
#     #     from serial.tools import list_ports

#     #     ports = list_ports.comports()
#     #     for device in ports:
#     #         try:
#     #             port = serial.Serial(
#     #                 port=device.device,
#     #                 baudrate=9600,
#     #                 bytesize=serial.EIGHTBITS,
#     #                 parity=serial.PARITY_NONE,
#     #                 stopbits=serial.STOPBITS_ONE,
#     #                 timeout=0,
#     #             )
#     #             self.assertIsNotNone(port)
#     #             self.assertTrue(port.is_open)
#     #             port.write(bytes([0x7F]))
#     #             print(port.read(), device.device)
#     #         finally:
#     #             port.close()

#     # def test010_init(self):
#     #     try:
#     #         port = serial.Serial(
#     #             port=path,
#     #             baudrate=9600,
#     #             bytesize=serial.EIGHTBITS,
#     #             parity=serial.PARITY_NONE,
#     #             stopbits=serial.STOPBITS_ONE,
#     #             timeout=0,
#     #         )
#     #         self.assertIsNotNone(port)
#     #         self.assertTrue(port.is_open)
#     #         port.write(bytes([0x7F]))
#     #     finally:
#     #         port.close()


if __name__ == "__main__":
    unittest.main()
