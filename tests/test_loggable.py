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


class LoggableTestCase(envtest.CoreTestCase):
    """Tests for the Loggable base class and related utilities."""

    def test010_loggable_standalone(self):
        """Verify Loggable can be used as a standalone mixin."""
        from pymicroscope.utils.loggable import Loggable
        obj = Loggable(log_name="test.standalone", log_level=logging.DEBUG)
        self.assertEqual(obj.log_name, "test.standalone")
        self.assertEqual(obj.log_level, logging.DEBUG)

    def test020_loggable_default_log_level(self):
        """Verify default log level is used when none specified."""
        from pymicroscope.utils.loggable import Loggable, DEFAULT_LOG_LEVEL
        obj = Loggable()
        self.assertEqual(obj.log_level, DEFAULT_LOG_LEVEL)

    def test030_loggable_log_property(self):
        """Verify log property returns a Logger instance."""
        from pymicroscope.utils.loggable import Loggable
        obj = Loggable(log_name="test.property")
        self.assertIsInstance(obj.log, logging.Logger)

    def test040_configured_log_returns_logger(self):
        """Verify configured_log function returns a properly configured logger."""
        from pymicroscope.utils.loggable import configured_log
        log = configured_log("test.configured", log_level=logging.WARNING)
        self.assertIsInstance(log, logging.Logger)
        self.assertEqual(log.level, logging.WARNING)
        self.assertFalse(log.propagate)

    def test050_configured_log_default_level(self):
        """Verify configured_log uses DEFAULT_LOG_LEVEL when none specified."""
        from pymicroscope.utils.loggable import configured_log, DEFAULT_LOG_LEVEL
        log = configured_log("test.default_level")
        self.assertEqual(log.level, DEFAULT_LOG_LEVEL)

    def test060_configured_log_clears_handlers(self):
        """Verify that calling configured_log twice doesn't duplicate handlers."""
        from pymicroscope.utils.loggable import configured_log
        log1 = configured_log("test.handlers")
        n_handlers = len(log1.handlers)
        log2 = configured_log("test.handlers")
        self.assertEqual(len(log2.handlers), n_handlers)

    def test070_pretty_format(self):
        """Verify pretty_format returns a formatted string."""
        from pymicroscope.utils.loggable import Loggable
        obj = Loggable()
        result = obj.pretty_format({"key": "value", "number": 42})
        self.assertIn("key", result)
        self.assertIn("value", result)
        self.assertIsInstance(result, str)

    def test080_show_loggers(self):
        """Verify show_loggers runs without error."""
        from pymicroscope.utils.loggable import Loggable
        with CaptureStdout() as output:
            Loggable.show_loggers()
        self.assertIsInstance(output.text, str)

    def test090_silence_werkzeug(self):
        """Verify silence_werkzeug adds filter to werkzeug logger."""
        from pymicroscope.utils.loggable import Loggable, PostGetFilter
        Loggable.silence_werkzeug()
        werkzeug_logger = logging.getLogger("werkzeug")
        has_filter = any(isinstance(f, PostGetFilter) for f in werkzeug_logger.filters)
        self.assertTrue(has_filter)

    def test100_post_get_filter_blocks_post(self):
        """Verify PostGetFilter blocks messages containing POST."""
        from pymicroscope.utils.loggable import PostGetFilter
        f = PostGetFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "POST /api/data", (), None)
        self.assertFalse(f.filter(record))

    def test110_post_get_filter_blocks_get(self):
        """Verify PostGetFilter blocks messages containing GET."""
        from pymicroscope.utils.loggable import PostGetFilter
        f = PostGetFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "GET /api/data", (), None)
        self.assertFalse(f.filter(record))

    def test120_post_get_filter_passes_normal(self):
        """Verify PostGetFilter allows normal messages through."""
        from pymicroscope.utils.loggable import PostGetFilter
        f = PostGetFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "Starting server", (), None)
        self.assertTrue(f.filter(record))

    def test130_viscosity_filter_is_post_get_filter(self):
        """Verify ViscosityFilter is a subclass of PostGetFilter."""
        from pymicroscope.utils.loggable import ViscosityFilter, PostGetFilter
        self.assertTrue(issubclass(ViscosityFilter, PostGetFilter))
        f = ViscosityFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "POST /data", (), None)
        self.assertFalse(f.filter(record))

    def test140_configured_log_with_override_level(self):
        """Verify Loggable.configured_log accepts level override."""
        from pymicroscope.utils.loggable import Loggable
        obj = Loggable(log_name="test.override", log_level=logging.INFO)
        log = obj.configured_log(log_level=logging.DEBUG)
        self.assertEqual(log.level, logging.DEBUG)


class ThreadUtilsTestCase(envtest.CoreTestCase):
    """Tests for thread_utils module."""

    def test000_is_main_thread_from_main(self):
        """Verify is_main_thread returns True from the main thread."""
        from pymicroscope.utils.thread_utils import is_main_thread
        self.assertTrue(is_main_thread())

    def test010_is_main_thread_from_secondary(self):
        """Verify is_main_thread returns False from a secondary thread."""
        from pymicroscope.utils.thread_utils import is_main_thread
        results = []

        def check():
            results.append(is_main_thread())

        t = threading.Thread(target=check)
        t.start()
        t.join()
        self.assertFalse(results[0])


if __name__ == "__main__":
    envtest.main()
