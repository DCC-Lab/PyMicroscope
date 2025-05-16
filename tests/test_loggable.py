"""
Unit tests for the LoggableProcess class and its ability to handle logging,
signals, multiprocessing behavior, and graceful termination.

This suite validates:
- Log name and log level assignment
- Logging output at different log levels
- Signal-based log level escalation (e.g., via SIGUSR1)
- Safety of signal registration in secondary threads
- Proper termination handling using shared flags

The `TestLoggableProcess` subclass is used to instrument the behavior of
LoggableProcess for testing signal handling and queue polling.
"""

import time
import os
import sys
import signal
import logging
import threading

import envtest  # setup environment for testing
from envtest import CaptureStdout, CaptureStdError
from pymicroscope.utils import LoggableProcess, CallableProcess


class TestLoggableProcess(LoggableProcess):  # pylint: disable=too-few-public-methods
    """
    A subclass of LoggableProcess that runs a loop checking for termination flags
    and command queue messages, while demonstrating log level control via signals.
    """

    def run(self):
        """
        Main run method executed in the subprocess.

        Installs signal handlers, checks for early termination, and polls command queue
        until the shared termination flag is set.
        """
        super().install_signal_handlers()

        start_time = time.time()
        while True:
            if time.time() < start_time + 2:
                time.sleep(0.01)

        super().deinstall_signal_handlers()


class TestLoggableCallableProcess(
    CallableProcess, TestLoggableProcess
):  # pylint: disable=too-few-public-methods
    """
    A subclass of TestLoggableProcess and CallableProcess  that runs a loop
    checking for termination flags and command queue messages, while
    demonstrating log level control via signals.
    """

    def run(self):
        """
        Main run method executed in the subprocess.

        Installs signal handlers, checks for early termination, and polls
        command queue until the shared termination flag is set.
        """
        super().install_signal_handlers()

        start_time = time.time()
        while True:
            if time.time() < start_time + 2:
                time.sleep(0.01)
            self.handle_remote_call_events()

        super().deinstall_signal_handlers()


class TerminatableTestCase(envtest.CoreTestCase):
    """
    Unit tests for process logging, naming, signal-based log control,
    and multiprocessing safety using TestLoggableProcess.
    """

    def test000_init(self):
        """
        Verify that a TestLoggableProcess can be instantiated.
        """
        self.assertIsNotNone(TestLoggableProcess())

    def test001_default_name(self):
        """
        Ensure that a process without a log_name specified has log_name set to None.
        This will use the default system log
        """
        proc = TestLoggableProcess()
        self.assertIsNone(proc.log_name)

    def test002_default_name(self):
        """
        Confirm that a log_name specified during construction is properly set.
        """
        proc = TestLoggableProcess(log_name="test")
        self.assertIsNotNone(proc.log_name)
        self.assertEqual(proc.log_name, "test")

    def test003_default_name_log_actually_logs_for_real(self):
        """
        Ensure that a log message is emitted when it matches or exceeds the configured log_level.
        """
        proc = TestLoggableProcess(log_name="test", log_level=envtest.TEST_LOG_LEVEL)
        self.assertIsNotNone(proc.log_name)
        self.assertEqual(proc.log_name, "test")

        with CaptureStdout() as output:
            proc.log.info("Test-info")  # should be captured
            self.assertTrue("Test-info" in output.text, output.text)

    def test003_default_name_log_actually_logs_for_real_only_right_level(self):
        """
        Confirm that a log message below the configured log_level does not appear in output.
        """
        proc = TestLoggableProcess(log_name="test", log_level=logging.INFO)
        self.assertIsNotNone(proc.log_name)
        self.assertEqual(proc.log_name, "test")

        with CaptureStdout() as output:
            proc.log.debug("Test-info")  # should be ignored
            self.assertTrue("Test-info" not in output.text, output.text)

    @envtest.skipIf(
        sys.platform == "darwin",
        "macOS only allows setting the signal_handler for USR1/2 in the main thread ",
    )
    @envtest.skip
    def test004_increase_log_level_with_signal(self):
        """
        Verify that sending SIGUSR1 to the process increases its log level dynamically.

        This is a special test:  allows setting the signal_handler in the subprocess
        (i.e. run() ) but macOS doesn't and we often test on macOS.

        So for macOS, we will simply skip this test
        """
        proc = TestLoggableCallableProcess(
            log_name="test", log_level=envtest.TEST_LOG_LEVEL
        )
        proc.start()
        time.sleep(0.5)

        with CaptureStdout():
            os.kill(proc.pid, signal.SIGUSR1)

        time.sleep(0.5)

        # It is difficult to asses the log_level because it is "per process"
        # and I need the log_level in the running process.
        # However, I will cheat: I can use the CallableProcess functions
        # to get the value of log_level in the Process.run()

        actual_log_level = proc.get_property("log_level")
        self.assertTrue(logging.INFO != actual_log_level)
        proc.terminate()

    def secondary_thread(self):
        """
        Attempt to register a signal handler from a secondary thread.

        Expected to raise ValueError because Python restricts signal handling to the main thread.
        """

        def signal_handler(signum, frame):  # pylint: disable=unused-argument
            print("Handling")

        _ = signal.signal(signal.SIGUSR1, signal_handler)
        time.sleep(2)

    def test005_secondary_thread_set_signal(self):
        """
        Confirm that registering a signal handler in a non-main thread raises a ValueError,
        and that the error message is captured in stderr.
        """
        thread = threading.Thread(target=self.secondary_thread)

        with CaptureStdError() as output:
            thread.start()
            time.sleep(1)

            thread.join(timeout=0.0)
            self.assertFalse(thread.is_alive())
            self.assertTrue("ValueError" in output.text)

            thread.join()


if __name__ == "__main__":
    envtest.main()
