import time
from typing import Optional, Union, Type, Any, Callable, Tuple
import logging

import envtest  # setup environment for testing
from pymicroscope.utils.pyroprocess import PyroProcess
from pymicroscope.acquisition.imageprovider import ImageProvider

from Pyro5.nameserver import start_ns
from Pyro5.api import expose, Daemon, locate_ns, Proxy

import numpy as np


class DebugImageProvider(ImageProvider):
    def capture_image(self) -> np.ndarray:
        """
        Generate an 8-bit random image of shape (size[0], size[1], channels).

        Args:
            size (tuple): Height and width of the image.
            channels (int): Number of channels (e.g., 1=grayscale, 3=RGB).

        Returns:
            np.ndarray: Random image as uint8 array.

        Example:
            >>> img = random_image(256, 3)
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
class TestDelegate(PyroProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(pyro_name="image-provider-delegate", *args, **kwargs)
        self.img_tuple = None

    def new_image_captured(self, img_tuple):
        self.img_tuple = img_tuple


class ImageProviderTestCase(envtest.CoreTestCase):
    """
    Unit tests for process logging, naming, signal-based log control,
    and multiprocessing safety using TestLoggableProcess.
    """

    def test000_init_provider(self):
        """
        Can I init my abstract provider? (no)
        """
        with self.assertRaises(TypeError):
            self.assertIsNotNone(ImageProvider())

    def test010_init_debugprovider(self):
        """
        Can I init my debug provider? yes
        """
        self.assertIsNotNone(
            DebugImageProvider(pyro_name="ca.dccmlab.debug.image-provider")
        )

    def test020_init_running_debug_provider(self):
        """
        Can I init my debug provider? yes
        """
        prov = DebugImageProvider(pyro_name="ca.dccmlab.debug.image-provider")
        prov.start_synchronously()
        time.sleep(0.2)
        prov.terminate_synchronously()

    def test030_create_delegate(self):
        """
        Can I init my debug provider? yes
        """
        image_delegate = TestDelegate()
        image_delegate.start_synchronously()
        self.assertIsNotNone(PyroProcess.by_name(image_delegate.pyro_name))
        image_delegate.terminate_synchronously()

    def test040_init_running_debug_provider_with_delegate(self):
        """
        Can I init my debug provider? yes
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

    def test050_set_delegate_later(self):
        """
        Can I init my debug provider? yes
        """
        image_delegate = TestDelegate(log_level=logging.DEBUG)
        image_delegate.start_synchronously()

        prov = DebugImageProvider(
            pyro_name="ca.dccmlab.debug.image-provider",
            log_level=logging.DEBUG,
        )
        prov.start_synchronously()
        provider_proxy = PyroProcess.by_name(prov.pyro_name)

        time.sleep(0.5)
        provider_proxy.delegate_by_name = image_delegate.pyro_name
        time.sleep(0.5)
        prov.terminate_synchronously()

        image_delegate.terminate_synchronously()


if __name__ == "__main__":
    envtest.main()
