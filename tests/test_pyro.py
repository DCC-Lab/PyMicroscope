import envtest  # setup environment for testing
import subprocess
import time
import threading
import re
import select

# pylint: disable=unused-import
from typing import Optional, Union, Type, Any, Callable, Tuple
import numpy as np

from Pyro5.nameserver import start_ns
from Pyro5.api import expose, Daemon, locate_ns, Proxy
from src.utils.pyroprocess import PyroProcess


class PyroProcessTestCase(envtest.CoreTestCase):
    """
    Unit tests for process logging, naming, signal-based log control,
    and multiprocessing safety using TestLoggableProcess.
    """

    def setUp(self):
        super().setUp()
        self.assertIsNotNone(
            PyroProcess.locate_ns(),
            "Start a Pyro5 nameserver in the terminal `python3 -m Pyro5.nameserver --host=0.0.0.0`",
        )

    def test000_init_pyroprocess(self):
        """
        Can I init my object?
        """
        self.assertIsNotNone(PyroProcess("test-object"))

    def test005_start_local_nameserver(self):
        """ """
        PyroProcess.start_nameserver()
        self.assertIsNotNone(PyroProcess.locate_ns())
        PyroProcess.stop_nameserver()

    def test010_pyroprocess_echo_works(self):
        """
        Is my object advertised and usable?
        """
        pyro_obj = PyroProcess("test-object")
        self.assertEqual(pyro_obj.echo("Test-echo"), "Test-echo")

    def test030_start_pyroprocess_with_context(self):
        """
        Is my object advertised and usable?
        """
        with PyroProcess("test-object"):
            uri = PyroProcess.locate_ns().lookup("test-object")
            with Proxy(uri) as pyro_proxy:
                self.assertEqual(pyro_proxy.echo("Test-echo"), "Test-echo")

    def test035_get_local_ip(self):
        """
        Can I get my IP?
        """
        self.assertIsNotNone(PyroProcess.get_local_ip())

    def test035_get_all_ipv4(self):
        """
        Can I get my IPv4?
        """
        addrs = PyroProcess.get_all_ip_addresses(include_v6=False)
        self.assertIsNotNone(addrs)

        for addr in addrs:
            self.assertIsNotNone(re.search(r"\d+\.\d+\.\d+\.\d+", addr))

    def test037_get_all_include_ipv6(self):
        """
        Can I get my IPv6?
        """
        addrs = PyroProcess.get_all_ip_addresses(include_v6=True)
        self.assertIsNotNone(addrs)

        for addr in addrs:
            m = re.search(r"\d+\.\d+\.\d+\.\d+", addr)
            if m is None:
                m = re.search(r"([0-9a-f]*):?", addr)  # Not sure how to do this simply
                self.assertIsNotNone(m, addr)

    def test040_locate_remote_nameserver(self):
        """
        Is there a nameserver somewhere on the sub-network?
        """

        start_time = time.time()
        while time.time() < start_time + 5:
            try:
                ns = PyroProcess.locate_ns()
                self.assertIsNotNone(ns)
                break
            except:
                pass

    def test050_register_to_remote_nameserver(self):
        """
        Is my object advertised and usable?
        """

        ns = PyroProcess.locate_ns()
        self.assertIsNotNone(ns)
        with PyroProcess("test-object") as proc:
            with PyroProcess.by_name("test-object") as pyro_proxy:
                self.assertEqual(pyro_proxy.echo("Test-echo"), "Test-echo")

    def test060_available_objects(self):
        with PyroProcess("test-object-1") as proc1, PyroProcess(
            "test-object-2"
        ) as proc2:
            objects = PyroProcess.available_objects()
            self.assertTrue("test-object-1" in objects)
            self.assertTrue("test-object-2" in objects)

    def test_remote_provider_to_image_server(self):
        with RemoteImageServer(pyro_name="remote-image-server") as image_server:
            with RemoteImageProvider(
                image_server_name="remote-image-server", pyro_name="remote-provider"
            ) as provider:
                time.sleep(1)


@expose
class RemoteImageServer(PyroProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.images = []

    def new_image_captured(self, image):
        self.images.append(image)


@expose
class RemoteImageProvider(PyroProcess):
    def __init__(self, image_server_name=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if image_server_name is None:
            image_server_name = "remote-image-server"
        self.image_server = PyroProcess.by_name(image_server_name)

    def capture_packaged_image(self):
        image_array = self.capture_image()
        return {
            "data": image_array.tobytes(),
            "shape": image_array.shape,
            "dtype": str(image_array.dtype),
        }

    def capture_image(self, stream=None) -> Tuple[[np.ndarray], [dict], dict]:
        image_array = np.random.randint(
            0,
            high=256,
            size=(300, 300),
            dtype=np.uint8,
        )

        return image_array

    def run(self) -> None:
        """
        The run method for this Pyro object still supports CallableProcess
        """
        with Daemon(host=self.get_local_ip()) as daemon:
            with self.syncing_context() as must_terminate_now:
                uri = daemon.register(self)
                self.locate_ns().register(self.pyro_name, uri)

                while not must_terminate_now:
                    self.handle_remote_call_events()
                    self.handle_pyro_events(daemon)

                    img_tuple = self.capture_packaged_image()
                    if self.image_server is not None:
                        try:
                            call_time = time.time()
                            self.image_server.new_image_captured(img_tuple)
                        except Exception as err:
                            self.log.error(f"Error sending image to image-server {err}")

                self.locate_ns().remove(self.pyro_name)


if __name__ == "__main__":
    envtest.main()
