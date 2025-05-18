import envtest  # setup environment for testing
from pymicroscope.acquisition.epiphan import *


class EpiphanWrapperTestCase(envtest.CoreTestCase):
    def setUp(self):
        super().setUp()
        try:
            EpiphanLibraryWrapper.setup_library()
            self.assertIsNotNone(EpiphanLibraryWrapper.lib)
        except Exception as err:
            self.fail(f"Unable to initialize Epiphan library: {err}")

    def tearDown(self):
        super().tearDown()
        try:
            EpiphanLibraryWrapper.cleanup_library()
        except Exception as err:
            pass

    def test000_init_library(self) -> None:
        self.assertIsNotNone(EpiphanLibraryWrapper.lib)

    def test020_can_open_grabber(self) -> None:
        self.assertIsNotNone(
            EpiphanLibraryWrapper.lib.FrmGrab_Open("local".encode("utf-8"))
        )


if __name__ == "__main__":
    envtest.main()
