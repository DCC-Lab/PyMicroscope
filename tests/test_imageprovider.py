import time
import logging
from typing import Optional, Tuple, Any

import numpy as np

import envtest  # setup environment for testing
from pymicroscope.utils.pyroprocess import PyroProcess
from pymicroscope.acquisition.imageprovider import (
    ImageProvider,
    RemoteImageProvider,
    ImageProviderDelegate,
)

from Pyro5.nameserver import start_ns
from Pyro5.api import expose


class DebugImageProvider(RemoteImageProvider):
    """
    An image provider that generates synthetic 8-bit images for testing.
    """

    def capture_image(self) -> np.ndarray:
        """
        Generate an 8-bit random image of shape (size[0], size[1], channels),
        simulating frame rate delay between frames.

        Returns:
            np.ndarray: Random image as a uint8 array.

        Example:
            >>> img = provider.capture_image()
            >>> img.shape
            (256, 256, 3)
        """
        img = np.random.randint(
            0, 256, (self.size[0], self.size[1], self.channels), dtype=np.uint8
        )

        frame_duration = 1 / self.frame_rate

        while (
            self._last_image is not None
            and time.time() < self._last_image + frame_duration
        ):
            time.sleep(0.001)

        self._last_image = time.time()
        self.log.debug("Image captured at %f", time.time() - self._start_time)
        return img


@expose
class TestDelegate(PyroProcess, ImageProviderDelegate):
    """
    A test delegate that stores the last captured image tuple.
    """

    def __init__(
        self, pyro_name: str = "test-delegate", *args: Any, **kwargs: Any
    ) -> None:
        """
        Initialize the test delegate process.

        Args:
            pyro_name (str): The Pyro name to register under.
            *args: Positional arguments for PyroProcess.
            **kwargs: Keyword arguments for PyroProcess.
        """
        super().__init__(*args, pyro_name=pyro_name, **kwargs)
        self.img_tuple: Optional[Tuple] = None

    def new_image_captured(self, img_tuple: Tuple) -> None:
        """
        Called when a new image is captured.

        Args:
            img_tuple (Tuple): The image and associated metadata.
        """
        self.img_tuple = img_tuple


class ImageProviderTestCase(envtest.CoreTestCase):
    """
    Unit tests for the image provider system including delegate registration,
    process lifecycle, and Pyro name resolution.
    """

    def test000_init_provider(self) -> None:
        """
        Verify that the abstract ImageProvider cannot be instantiated directly.
        """
        with self.assertRaises(TypeError):
            self.assertIsNotNone(ImageProvider())

    def test010_init_debugprovider(self) -> None:
        """
        Verify that the DebugImageProvider can be instantiated.
        """
        self.assertIsNotNone(
            DebugImageProvider(pyro_name="ca.dccmlab.debug.image-provider")
        )

    def test020_init_running_debug_provider(self) -> None:
        """
        Start and stop the debug provider to verify lifecycle.
        """
        prov = DebugImageProvider(pyro_name="ca.dccmlab.debug.image-provider")
        prov.start_synchronously()
        time.sleep(0.2)
        prov.terminate_synchronously()

    def test030_create_delegate(self) -> None:
        """
        Verify that a TestDelegate can be created, registered, and terminated.
        """
        image_delegate = TestDelegate()
        image_delegate.start_synchronously()
        self.assertIsNotNone(PyroProcess.by_name(image_delegate.pyro_name))
        image_delegate.terminate_synchronously()

    def test040_init_running_debug_provider_with_delegate(self) -> None:
        """
        Start a DebugImageProvider with a delegate and verify delegate communication.
        """
        image_delegate = TestDelegate(log_level=logging.INFO)
        image_delegate.start_synchronously()
        delegate_proxy = PyroProcess.by_name(image_delegate.pyro_name)

        prov = DebugImageProvider(
            pyro_name="ca.dccmlab.debug.image-provider",
            delegate=delegate_proxy,
            log_level=logging.INFO,
        )
        prov.start_synchronously()
        provider_proxy = PyroProcess.by_name(prov.pyro_name)

        time.sleep(0.5)
        provider_proxy.set_frame_rate(100)
        time.sleep(0.5)
        prov.terminate_synchronously()
        image_delegate.terminate_synchronously()

    def test050_set_delegate_by_name(self) -> None:
        """
        Start a DebugImageProvider and assign its delegate after startup.
        """
        image_delegate = TestDelegate(
            pyro_name="test-delegate", log_level=logging.DEBUG
        )
        image_delegate.start_synchronously()

        prov = DebugImageProvider(
            pyro_name="ca.dccmlab.debug.image-provider",
            log_level=logging.DEBUG,
        )
        prov.start_synchronously()
        provider_proxy = PyroProcess.by_name(prov.pyro_name)

        time.sleep(0.5)
        provider_proxy.set_delegate("test-delegate")
        time.sleep(0.5)
        prov.terminate_synchronously()
        image_delegate.terminate_synchronously()

    def test050_set_delegate_by_uri(self) -> None:
        """
        Start a DebugImageProvider and assign its delegate after startup.
        """
        image_delegate = TestDelegate(
            pyro_name="test-delegate", log_level=logging.DEBUG
        )
        image_delegate.start_synchronously()
        ns = PyroProcess.locate_ns()
        delegate_uri = ns.lookup(image_delegate.pyro_name)

        prov = DebugImageProvider(
            pyro_name="ca.dccmlab.debug.image-provider",
            log_level=logging.DEBUG,
        )
        prov.start_synchronously()
        provider_proxy = PyroProcess.by_name(prov.pyro_name)

        time.sleep(0.5)
        provider_proxy.set_delegate(delegate_uri)
        time.sleep(0.5)
        prov.terminate_synchronously()
        image_delegate.terminate_synchronously()

    def test100_imageprovider_with_local_delegate(self) -> None:
        """
        Start a DebugImageProvider with a local (in-process) delegate.
        """
        image_delegate = TestDelegate(log_level=logging.INFO)

        prov = DebugImageProvider(
            pyro_name="ca.dccmlab.debug.image-provider",
            delegate=image_delegate,
            log_level=logging.INFO,
        )
        prov.start_synchronously()

        time.sleep(0.5)
        prov.terminate_synchronously()


if __name__ == "__main__":
    envtest.main()
