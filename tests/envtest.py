"""
Adjust the import path to include the root directory of the project.

This is useful for testing modules locally, even when the script is run from
a subdirectory.

Example:
    Running `python tests/test_http.py` can still import the present module
    to test on the real source code if project root is added to sys.path early.

    test_http.py:
    ```
    import envtest

    class MyTestCase(envtest.CoreTestCase):
        def test(self):

    ```
"""

from unittest import main, TestCase, skipIf, expectedFailure, SkipTest, skip
import unittest  # to remove
import os

os.environ["COVERAGE_PROCESS_START"] = ".coveragerc"


import io
import sys
import subprocess
from http.server import (
    SimpleHTTPRequestHandler,
    ThreadingHTTPServer,
)
import threading
import logging
import time
from queue import Full, Empty, Queue
import psutil

path = os.path.join(os.path.dirname(__file__), "../src")
sys.path.append(path)

from pymicroscope.utils import configured_log


TEST_LOG_LEVEL = logging.INFO


class CaptureStdout:
    """
    Context manager to capture stdout (print output) as a string.

    Example:
        with CaptureStdout() as cap:
            print("Hello")
            self.assertEqual(cap.text, "Hello")
    """

    def __init__(self):
        self._iostring = None

    @property
    def text(self):
        """
        The captured text
        """
        return self._iostring.getvalue()

    def __enter__(self):
        self._iostring = io.StringIO()
        sys.stdout = self._iostring
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = sys.__stdout__


class CaptureStdError:
    """
    Context manager to capture stderr (print output for errors) as a string.

    Example:
        with CaptureStdError() as cap:
            raise ValueError("Oops")  # Captured error
            self.assertEqual(cap.text, "Oops")
    """

    def __init__(self):
        self._iostring = None

    @property
    def text(self):
        """
        The captured text
        """
        return self._iostring.getvalue()

    def __enter__(self):
        self._iostring = io.StringIO()
        sys.stderr = self._iostring
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stderr = sys.__stderr__


class TestHTTPRequestHandler(SimpleHTTPRequestHandler):
    """
    A request handler for simulating HTTP GET and POST requests in tests.

    Tracks the requested paths and post data to allow test assertions.

    Example:
        Used in conjunction with TestHTTPServer in a `with` block:
            with TestHTTPServer(("localhost", 4000)) as server:
                urllib.request.urlopen("http://localhost:4000/test")
                print(server.last_path)  # "/test"
    """

    last_path = None
    paths = []
    last_post_data = None

    def log_message(self, *args):
        pass  # Suppresses output

    def do_GET(self):  # pylint: disable=invalid-name
        """Records GET requests and responds with a configurable status code."""

        code = self.server.get_test_request_response()
        self.send_response(code)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        # self.wfile.write("GET request for {}".format(self.path).encode('utf-8'))
        TestHTTPRequestHandler.last_path = self.path
        TestHTTPRequestHandler.paths.append(self.path)

    def do_POST(self):  # pylint: disable=invalid-name
        """Records POST path and data; responds with test code."""

        code = self.server.get_test_request_response()

        content_length = int(
            self.headers["Content-Length"]
        )  # <--- Gets the size of data
        TestHTTPRequestHandler.last_path = self.path
        TestHTTPRequestHandler.paths.append(self.path)
        TestHTTPRequestHandler.last_post_data = self.rfile.read(content_length)

        self.send_response(code)
        self.send_header("Content-type", "text/html")
        self.end_headers()


class TestHTTPServer(ThreadingHTTPServer):
    """
    A testable HTTP server that runs in a background thread for functional tests.

    Tracks received request paths and allows configuration of the response code.

    Example:
        with TestHTTPServer(("127.0.0.1", 4000)) as server:
            urllib.request.urlopen("http://127.0.0.1:4000/foo")
            print(server.last_path)  # Output: "/foo"
    """

    def __init__(self, host, reply_error=None):
        super().__init__(host, TestHTTPRequestHandler)
        self.host = host
        self.server_thread = None
        TestHTTPRequestHandler.last_post_data = None
        TestHTTPRequestHandler.last_path = None
        TestHTTPRequestHandler.paths = []
        self.test_request_code = 200
        self.reply_error = reply_error

    def get_test_request_response(self):
        """Returns the response code used for test replies."""
        return self.test_request_code

    @property
    def last_path(self):
        """Last HTTP path received (e.g., '/ping')."""
        return TestHTTPRequestHandler.last_path

    @last_path.setter
    def last_path(self, value):
        TestHTTPRequestHandler.last_path = value

    @property
    def paths(self):
        """All HTTP paths received in this session."""
        return TestHTTPRequestHandler.paths

    @property
    def last_post_data(self):
        """Payload of the last POST request."""
        return TestHTTPRequestHandler.last_post_data

    @last_post_data.setter
    def last_post_data(self, value):
        TestHTTPRequestHandler.last_post_data = value

    def __enter__(self):
        """Starts the server thread for use in a `with` block."""
        self.last_post_data = []
        self.last_path = []
        self.start_server_thread()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Stops the server thread cleanly."""
        super().__exit__(exc_type, exc_value, traceback)

    def start_server_thread(self):
        """Start serving requests in a new thread."""
        self.server_thread = threading.Thread(target=self.serve_forever)
        self.server_thread.daemon = False
        self.server_thread.start()
        return self.server_thread

    def stop_server_thread(self):
        """Stops the background server thread."""
        self.shutdown()
        if self.server_thread is not None:
            self.server_thread.join()
            self.server_thread = None


class CoreTestCase(TestCase):
    """
    Base test case for integration testing with local services.

    It will validate the environment to make sure everything is ok:

    1. service cheeseProbe not running
    2. server and host by default

    Example:
        class MyServerTest(CoreTestCase):
            def test_server_available(self):
                with TestHTTPServer(self.host) as server:
                    response = urllib.request.urlopen(self.server + "/hello")
                    self.assertEqual(server.last_path, "/hello")
    """

    test_start_time = None
    log = None

    @classmethod
    def setUpClass(cls):
        """
        Ensures that 'cheeseProbe' service is stopped before running tests.

        Raises:
            RuntimeError: If the service is still active after attempting to stop.
        """

        super().setUpClass()

        global TEST_LOG_LEVEL

        override_level = logging.INFO
        try:
            level_name = os.environ.get("TEST_LOG_LEVEL", "INFO").upper()
            override_level = getattr(logging, level_name)
        except:
            raise ValueError(
                f"logging.{level_name} is not valid.  Options are: {logging._nameToLevel}"
            )

        TEST_LOG_LEVEL = int(override_level)
        CoreTestCase.log = configured_log("global", log_level=TEST_LOG_LEVEL)

        os.environ["LIBCAMERA_LOG_LEVELS"] = "*:4"  # Prevent massive loggin to screen

        if cls.is_service_active("cheeseProbe.service"):
            cls.log.warning("Service is running: stopping it")
            _ = subprocess.run(
                ["systemctl", "stop", "cheeseProbe.service"],
                check=False,
                capture_output=True,
                text=True,
            )
        if cls.is_service_active("cheeseProbe"):  # It should be stopped, if not bail
            raise RuntimeError(
                "You must stop the service that is running is the background for testing"
            )

        cls.test_start_time = time.time()

    @classmethod
    def tearDownClass(cls):
        processes = cls.get_child_processes()

        if len(processes) > 2:  # Because always 2 Python processes during unittest
            msg = ", ".join(
                f"PID={p.pid}, PPID={p.ppid()}, Status={p.status()}" for p in processes
            )
            cls.log.warning(
                f"Feature-in-development: Found orphan or zombie processes after {cls}: {msg}"
            )

        proc = psutil.Process(os.getpid())
        open_files = proc.open_files()
        if open_files:
            cls.log.warning(f"{len(open_files)} open file(s):")
            for f in open_files:
                cls.log.warning(f.path)

        super().tearDownClass()

    @classmethod
    def is_service_active(cls, service_name: str) -> str:
        """
        Checks if a systemd service is active.

        Args:
            service_name (str): The name of the service.

        Returns:
            bool: True if the service is active, False otherwise.

        Example:
            CoreTestCase.is_service_active("ssh")  # → True or False
        """
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                check=False,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip() == "active"

        except FileNotFoundError:
            return False

    def setUp(self):
        super().setUp()

        self.log = configured_log(self._testMethodName, log_level=TEST_LOG_LEVEL)

        self.host = ("127.0.0.1", 4000)
        self.server = f"http://{self.host[0]}:{self.host[1]}"
        self.log.info("Starting test")
        self.start_time = time.time()

    def tearDown(self):
        pass

    @classmethod
    def get_processes(cls, max_run_time=100):
        my_uid = os.getuid()

        now = time.time()
        process_list = []
        for proc in psutil.process_iter(["pid", "name", "uids", "create_time"]):
            try:
                if (
                    proc.info["uids"].real == my_uid
                    and now - proc.info["create_time"] < max_run_time
                ):
                    process_list.append(
                        {
                            "pid": proc.info["pid"],
                            "name": proc.info["name"],
                            "create_time": now - proc.info["create_time"],
                        }
                    )
                    # print(f"PID={proc.info['pid']}, Name={proc.info['name']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return process_list

    @classmethod
    def get_child_processes(cls):
        # Get the current process
        parent = psutil.Process()

        # Recursively get all children (grandchildren, etc.)
        children = parent.children(recursive=True)

        return children

    @classmethod
    def drain_queue(cls, queue):
        """
        Safely empties the internal multiprocessing queue to prevent blocking
        on termination, and then close() and join()

        Avoids using queue size checks or non-blocking gets, which may lead to
        deadlocks.

        This is subtle: it is not reliable to check the size of a
        multiprocessing queue. We must block, then break on error
        (empty queue). It is not correct to use get_nowait() I lost 2 hours
        on this problem, because unreleased elements will block the quit
        process.
        """

        while True:
            try:
                queue.get(timeout=0.1)
            except Empty:
                # We are done.
                break

        try:
            queue.close()
            queue.join_thread()
        except AttributeError:
            pass


if __name__ == "__main__":
    print(CoreTestCase.get_child_processes())
