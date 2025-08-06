""" Port USB """
import unittest
import time
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

    def test080_get_dac_increment(self):
        self.assertIsNotNone(self.controller.dac_increment)

    def test090_get_dac_increment(self):
        self.controller.dac_increment = 32
        self.assertEqual(self.controller.dac_increment, 32)

    def test100_build_time(self):
        version = self.controller.send_command("READ_BUILD_TIME")
        self.assertTrue(version == (b'1', b'5', b':', b'1', b'8', b':', b'4', b'1'))
        self.assertTrue(len(version) == 8)

    def test110_buid_date(self):
        version = self.controller.send_command("READ_BUILD_DATE")
        self.assertTrue(len(version) == 11)
        self.assertTrue(version == (b'F', b'e', b'b', b' ', b'0', b'6', b' ', b'2', b'0', b'1', b'2'))

    def test120_cid(self):
        version = self.controller.send_command("READ_CID")
        self.assertTrue(version == (0, 0))

    def test130_cpn(self):
        version = self.controller.send_command("READ_CPN")
        self.assertTrue(version == (522,))
    
    def test140_sn(self):
        version = self.controller.send_command("READ_SN")
        self.assertTrue(version == (0, 0))

    def test150_state_of_switches_and_ttl_ios(self):
        version = self.controller.send_command("READ_STATE_OF_SWITCHES_AND_TTL_IOS")
        self.assertTrue(version == (3,))

    def test160_build_info(self):
        print(self.controller.build_info())




if __name__ == "__main__":
    unittest.main()
    #controller = VMSController()
    #controller.initialize()

    #print("Changing lines from 576 to 512")
    #controller.lines_per_frame = 576
    #time.sleep(5)
    #controller.lines_per_frame = 468
    #time.sleep(5)
    #controller.lines_per_frame = 576

    #print("Changing lines from 6 to 150")
    #controller.lines_for_vsync = 6
    #time.sleep(5)
    #controller.lines_for_vsync = 350
    #time.sleep(5)
    #controller.lines_for_vsync = 6

    #print("Changing dac_start from 19200 to 15200")
    #controller.dac_start = 19200
    #time.sleep(5)
    #controller.dac_start = 15200
    #time.sleep(5)
    #controller.dac_start = 19200

    #print("Changing dac_increment from 32 to 10")
    #controller.dac_increment = 32
    #time.sleep(5)
    #controller.dac_increment = 10
    #time.sleep(5)
    #controller.dac_increment = 32



    #controller.shutdown()
