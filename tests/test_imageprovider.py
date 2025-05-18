import time
import logging
from typing import Optional, Tuple, Any
import base64

import numpy as np

import envtest  # setup environment for testing
from pymicroscope.utils.pyroprocess import PyroProcess
from pymicroscope.acquisition.imageprovider import (
    ImageProvider,
    ImageProviderClient,
    DebugImageProvider,
    show_provider,
)

from Pyro5.nameserver import start_ns
from Pyro5.api import expose


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

    def test030_create_client(self) -> None:
        """
        Verify that a TestClient can be created, registered, and terminated.
        """
        image_client = ImageProviderClient(pyro_name="test-client")
        image_client.start_synchronously()
        self.assertIsNotNone(PyroProcess.by_name(image_client.pyro_name))
        image_client.terminate_synchronously()

    def test040_init_running_debug_provider_with_client(self) -> None:
        """
        Start a DebugImageProvider with a client and verify client communication.
        """
        image_client = ImageProviderClient(
            pyro_name="test-client", log_level=logging.INFO
        )
        image_client.start_synchronously()
        client_proxy = PyroProcess.by_name(image_client.pyro_name)

        prov = DebugImageProvider(
            pyro_name="ca.dccmlab.debug.image-provider",
            log_level=logging.INFO,
        )
        prov.start_synchronously()
        prov.add_client(client_proxy)
        provider_proxy = PyroProcess.by_name(prov.pyro_name)
        self.assertIsNotNone(provider_proxy)

        time.sleep(0.5)
        provider_proxy.set_frame_rate(100)
        time.sleep(0.5)
        prov.terminate_synchronously()
        image_client.terminate_synchronously()

    def test050_set_client_by_name(self) -> None:
        """
        Start a DebugImageProvider and assign its client after startup.
        """
        image_client = ImageProviderClient(
            pyro_name="test-client", log_level=logging.DEBUG
        )
        image_client.start_synchronously()

        prov = DebugImageProvider(
            pyro_name="ca.dccmlab.debug.image-provider",
            log_level=logging.DEBUG,
        )
        prov.start_synchronously()
        provider_proxy = PyroProcess.by_name(prov.pyro_name)
        self.assertIsNotNone(provider_proxy)

        time.sleep(0.5)
        provider_proxy.add_client("test-client")
        time.sleep(0.5)
        prov.terminate_synchronously()
        image_client.terminate_synchronously()

    def test050_set_client_by_uri(self) -> None:
        """
        Start a DebugImageProvider and assign its client after startup.
        """
        image_client = ImageProviderClient(
            pyro_name="test-client", log_level=logging.DEBUG
        )
        image_client.start_synchronously()
        ns = PyroProcess.locate_ns()
        client_uri = ns.lookup(image_client.pyro_name)

        prov = DebugImageProvider(
            pyro_name="ca.dccmlab.debug.image-provider",
            log_level=logging.DEBUG,
        )
        prov.start_synchronously()
        provider_proxy = PyroProcess.by_name(prov.pyro_name)
        self.assertIsNotNone(provider_proxy)

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

        self.provider = DebugImageProvider(
            log_level=logging.DEBUG, pyro_name="ca.dccmlab.imageprovider.debug"
        )
        self.provider.start_synchronously()

    def tearDown(self):
        if self.provider is not None:
            self.provider.terminate_synchronously()

        super().tearDown()

    def test100_imageprovider_with_local_client(self) -> None:
        """
        Start a DebugImageProvider with a local (in-process) client.
        """
        image_client = ImageProviderClient(
            pyro_name="test-client", log_level=logging.INFO
        )

        prov = DebugImageProvider(
            pyro_name="ca.dccmlab.debug.image-provider",
            log_level=logging.INFO,
        )
        prov.start_synchronously()

        time.sleep(0.5)
        prov.terminate_synchronously()

    def new_image(self, image):
        print("New image recevied")

    def test110_imageprovider_with_RemoteImageProviderClient(self) -> None:
        """
        Start a DebugImageProvider with a local (in-process) client.
        """
        image_client = ImageProviderClient(pyro_name="ca.dccmlab.image-provider.client")
        image_client.start_synchronously()

        prov = DebugImageProvider(
            pyro_name="ca.dccmlab.debug.image-provider",
            log_level=logging.INFO,
        )
        prov.add_client(image_client.pyro_name)
        self.assertTrue(len(prov.clients) > 0)

        prov.start_synchronously()

        time.sleep(0.5)
        prov.terminate_synchronously()

        reply = image_client.call_method_remotely("self", "images")
        self.assertTrue(len(reply.result) > 0)

        image_client.terminate_synchronously()

    def test200_get_running_provider(self) -> None:
        prov = PyroProcess.by_name("ca.dccmlab.imageprovider.debug")
        self.assertIsNotNone(prov)

    def test210_get_running_provider_set_client(self) -> None:
        prov = ImageProvider.by_name("ca.dccmlab.imageprovider.debug")
        self.assertIsNotNone(prov)
        prov.set_frame_rate(5)

    def test210_display_provider(self) -> None:
        show_provider("ca.dccmlab.imageprovider.debug", duration=5)

    def test300_get_objects(self):
        pyro_objects = PyroProcess.available_objects()
        for pyro_obj in pyro_objects:
            print(pyro_obj)


if __name__ == "__main__":
    envtest.main(defaultTest="DebugProviderOnNetworkTestCase.test300_get_objects")
    # envtest.main()
