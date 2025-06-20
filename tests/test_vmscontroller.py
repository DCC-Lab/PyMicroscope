""" Port USB """
import unittest

from vmscontroller import VMSController


class TestController(unittest.TestCase):
    def setUp(self):
        self.controller = VMSController()
        self.controller.initialize()

    def tearDown(self):
        self.controller.shutdown()

    def test000_init(self):
        self.assertIsNotNone(VMSController())

    def test010_get_lines_per_frame(self):
        self.assertIsNotNone(self.controller.lines_per_frame)

    def test020_get_lines_per_frame(self):
        self.controller.lines_per_frame = 576
        self.assertEqual(self.controller.lines_per_frame, 576)

    def test030_get_lines_for_vsync(self):
        self.assertIsNotNone(self.controller.lines_for_vsync)

    def test040_get_lines_for_vsync(self):
        self.controller.lines_for_vsync = 6
        self.assertEqual(self.controller.lines_for_vsync, 6)

    def test050_firmware_version(self):
        version = self.controller.send_command("READ_FIRMWARE_VERSION")
        self.assertTrue(version == (4, 0, 0))
    
    def test060_get_dac_start(self):
        self.assertIsNotNone(self.controller.dac_start)

    def test070_get_dac_start(self):
        self.controller.dac_start = 19200
        self.assertEqual(self.controller.dac_start, 19200)



if __name__ == "__main__":
    unittest.main()
