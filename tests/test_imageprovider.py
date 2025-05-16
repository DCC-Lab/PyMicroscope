import time
import logging
from typing import Optional, Tuple, Any
import base64

import numpy as np

import envtest  # setup environment for testing
from pymicroscope.utils.pyroprocess import PyroProcess
from pymicroscope.acquisition.imageprovider import (
    ImageProvider,
    RemoteImageProvider,
    ImageProviderClient,
    DebugRemoteImageProvider,
)

from Pyro5.nameserver import start_ns
from Pyro5.api import expose


@expose
class TestClient(PyroProcess, ImageProviderClient):
    """
    A test client that stores the last captured image tuple.
    """

    def __init__(
        self, pyro_name: str = "test-client", *args: Any, **kwargs: Any
    ) -> None:
        """
        Initialize the test client process.

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
    Unit tests for the image provider system including client registration,
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
        Verify that the DebugRemoteImageProvider can be instantiated.
        """
        self.assertIsNotNone(
            DebugRemoteImageProvider(pyro_name="ca.dccmlab.debug.image-provider")
        )

    def test020_init_running_debug_provider(self) -> None:
        """
        Start and stop the debug provider to verify lifecycle.
        """
        prov = DebugRemoteImageProvider(pyro_name="ca.dccmlab.debug.image-provider")
        prov.start_synchronously()
        time.sleep(0.2)
        prov.terminate_synchronously()

    def test030_create_client(self) -> None:
        """
        Verify that a TestClient can be created, registered, and terminated.
        """
        image_client = TestClient()
        image_client.start_synchronously()
        self.assertIsNotNone(PyroProcess.by_name(image_client.pyro_name))
        image_client.terminate_synchronously()

    def test040_init_running_debug_provider_with_client(self) -> None:
        """
        Start a DebugRemoteImageProvider with a client and verify client communication.
        """
        image_client = TestClient(log_level=logging.INFO)
        image_client.start_synchronously()
        client_proxy = PyroProcess.by_name(image_client.pyro_name)

        prov = DebugRemoteImageProvider(
            pyro_name="ca.dccmlab.debug.image-provider",
            log_level=logging.INFO,
        )
        prov.start_synchronously()
        prov.add_client(client_proxy)
        provider_proxy = PyroProcess.by_name(prov.pyro_name)

        time.sleep(0.5)
        provider_proxy.set_frame_rate(100)
        time.sleep(0.5)
        prov.terminate_synchronously()
        image_client.terminate_synchronously()

    def test050_set_client_by_name(self) -> None:
        """
        Start a DebugRemoteImageProvider and assign its client after startup.
        """
        image_client = TestClient(pyro_name="test-client", log_level=logging.DEBUG)
        image_client.start_synchronously()

        prov = DebugRemoteImageProvider(
            pyro_name="ca.dccmlab.debug.image-provider",
            log_level=logging.DEBUG,
        )
        prov.start_synchronously()
        provider_proxy = PyroProcess.by_name(prov.pyro_name)

        time.sleep(0.5)
        provider_proxy.add_client("test-client")
        time.sleep(0.5)
        prov.terminate_synchronously()
        image_client.terminate_synchronously()

    def test050_set_client_by_uri(self) -> None:
        """
        Start a DebugRemoteImageProvider and assign its client after startup.
        """
        image_client = TestClient(pyro_name="test-client", log_level=logging.DEBUG)
        image_client.start_synchronously()
        ns = PyroProcess.locate_ns()
        client_uri = ns.lookup(image_client.pyro_name)

        prov = DebugRemoteImageProvider(
            pyro_name="ca.dccmlab.debug.image-provider",
            log_level=logging.DEBUG,
        )
        prov.start_synchronously()
        provider_proxy = PyroProcess.by_name(prov.pyro_name)

        time.sleep(0.5)
        provider_proxy.add_client(client_uri)
        time.sleep(0.5)
        prov.terminate_synchronously()
        image_client.terminate_synchronously()


class DebugProviderOnNetworkTestCase(envtest.CoreTestCase):
    def setUp(self):
        super().setUp()

        if PyroProcess.locate_ns() is None:
            PyroProcess.start_nameserver()

        self.provider = DebugRemoteImageProvider(
            log_level=logging.DEBUG, pyro_name="ca.dccmlab.imageprovider.debug"
        )
        self.provider.start_synchronously()

    def tearDown(self):
        if self.provider is not None:
            self.provider.terminate_synchronously()

        super().tearDown()

    def test100_imageprovider_with_local_client(self) -> None:
        """
        Start a DebugRemoteImageProvider with a local (in-process) client.
        """
        image_client = TestClient(log_level=logging.INFO)

        prov = DebugRemoteImageProvider(
            pyro_name="ca.dccmlab.debug.image-provider",
            log_level=logging.INFO,
        )
        prov.start_synchronously()

        time.sleep(0.5)
        prov.terminate_synchronously()

    def test200_get_running_provider(self) -> None:
        prov = PyroProcess.by_name("ca.dccmlab.imageprovider.debug")
        self.assertIsNotNone(prov)

    def test210_get_running_provider_set_client(self) -> None:
        prov = PyroProcess.by_name("ca.dccmlab.imageprovider.debug")
        self.assertIsNotNone(prov)
        prov.set_frame_rate(5)

    def test210_get_running_provider_get_last_image(self) -> None:
        import matplotlib.pyplot as plt
        import numpy as np
        import time

        prov = PyroProcess.by_name("ca.dccmlab.imageprovider.debug")
        self.assertIsNotNone(prov)
        prov.set_frame_rate(100)

        plt.ion()  # Turn on interactive mode

        fig, ax = plt.subplots()
        image = np.random.rand(480, 640, 3)
        im = ax.imshow(image, cmap="gray")
        plt.show(block=False)

        for i in range(100):
            img_pack = prov.get_last_packaged_image()
            self.assertIsNotNone(img_pack)
            array = ImageProvider.image_from_package(img_pack)
            im.set_data(array)
            fig.canvas.draw()
            fig.canvas.flush_events()

        plt.ioff()
        plt.close(fig)


if __name__ == "__main__":
    envtest.main()
