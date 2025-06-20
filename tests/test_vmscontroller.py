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
        self.controller.lines_per_frame = 570
        self.assertEqual(self.controller.lines_per_frame, 570)

    def test030_get_lines_for_vsync(self):
        self.assertIsNotNone(self.controller.lines_for_vsync)

    def test040_get_lines_for_vsync(self):
        self.controller.lines_for_vsync = 4
        self.assertEqual(self.controller.lines_for_vsync, 4)

    def test_firmware_version(self):
        version = self.controller.send_command("READ_FIRMWARE_VERSION")
        self.assertEqual(version, (4, 0, 0))

    def test040_repeated_get_set(self):
        for i in range(100):
            self.controller.lines_per_frame = i
            self.assertEqual(self.controller.lines_per_frame, i)


if __name__ == "__main__":
    unittest.main()
