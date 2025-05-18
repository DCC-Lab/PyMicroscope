import envtest  # setup environment for testing
from pymicroscope.acquisition.epiphan import *


class EpiphanWrapperTestCase(envtest.CoreTestCase):
    def test000_init_library(self) -> None:
        try:
            EpiphanLibraryWrapper.setup_library()
            self.assertIsNotNone(EpiphanLibraryWrapper.lib)
        finally:
            EpiphanLibraryWrapper.cleanup_library()

    def test010_library_has_fct_definitions(self) -> None:
        try:
            EpiphanLibraryWrapper.setup_library()
            self.assertIsNotNone(EpiphanLibraryWrapper.lib.FrmGrab_Init)
        finally:
            EpiphanLibraryWrapper.cleanup_library()

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


if __name__ == "__main__":
    envtest.main()
