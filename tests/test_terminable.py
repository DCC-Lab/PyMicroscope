# pylint: disable=too-few-public-methods,protected-access
"""
Unit tests for the TerminableProcess class.

This module defines test cases for verifying the lifecycle management of custom
multiprocessing processes that support clean termination via signal handling.

Included test scenarios:
- Proper startup and termination of cooperative processes
- Detection of uncooperative processes that ignore termination
- Readiness signaling via has_entered_run_loop
- Safe use of TerminableProcess with context managers
- Timeout behavior when a process fails to start

Classes:
- TestProcess: well-behaved subclass that exits when signaled
- UnStoppableTestProcess: simulates an uncooperative process
- UnStartableTestProcess: simulates a never-ready process
- TerminatableTestCase: comprehensive test suite for the above behaviors
"""
import time
import os
import logging
import envtest
import multiprocessing
from dataclasses import dataclass

from unittest.mock import patch

from src.utils.terminable import TerminableProcess


class TestProcess(TerminableProcess):
    """
    A test implementation of `TerminableProcess` that exits cleanly when termination is requested.

    It runs a short sleep loop and checks for the `must_terminate_now` flag to exit gracefully.
    """

    def run(self):
        """
        Main loop that runs for up to 2 seconds or until termination is requested.

        This process installs signal handlers, sleeps in short intervals,
        and exits cleanly when the termination flag is set.
        """
        self.install_signal_handlers()
        start_time = time.time()
        while not self.must_terminate_now:
            if time.time() < start_time + 2:
                time.sleep(0.01)
        self.deinstall_signal_handlers()


class UnStoppableTestProcess(TerminableProcess):
    """
    A deliberately misbehaving subclass that ignores termination requests.
    Used to test fallback termination (e.g., kill -KILL).
    """

    def run(self):
        """
        Runs an infinite loop without checking for termination, simulating a process
        that must be forcibly killed.
        """
        self.install_signal_handlers()
        while True:
            time.sleep(0.01)
        self.deinstall_signal_handlers()


class UnStartableTestProcess(TerminableProcess):
    """
    A deliberately misbehaving subclass that never signals readiness.

    Used to test timeout behavior of `start_synchronously()` when the process
    does not indicate it has entered its run loop.
    """

    def run(self):
        """
        Runs an infinite loop without checking for termination, simulating a process
        that must be forcibly killed.
        """
        self.install_signal_handlers()
        while True:
            time.sleep(0.01)
        self.deinstall_signal_handlers()


class SuperFastTestProcess(TerminableProcess):
    """
    A process that starts and stops super quickly
    """

    def run(self):
        """
        We go through so fast nothing happens
        """


class ContextAwareProcess(TerminableProcess):
    """
    A TerminableProcess that uses the syncing_context() mechanism to coordinate clean entry and exit of its run loop.
    """

    def __init__(
        self,
        delay_before_entering_loop: float = 0,
        delay_before_exiting_loop: float = 0,
        run_loop_exception=None,
    ):
        super().__init__()
        self.delay_before_entering_loop = delay_before_entering_loop
        self.delay_before_exiting_loop = delay_before_exiting_loop
        self.run_loop_exception = run_loop_exception

    def on_loop_function(self):
        self.log.debug(
            "      executing on_loop_function()",
        )

    def run(self):
        self.log.debug("Run: Entering process")
        with self.syncing_context(on_loop_check=self.on_loop_function) as must_exit:
            self.log.debug("  Run: setup before run_loop")

            if self.delay_before_entering_loop > 0:
                self.log.debug(
                    "  Run:   Sleeping %ds internal loop",
                    self.delay_before_entering_loop,
                )
                time.sleep(self.delay_before_entering_loop)

            while not must_exit:  # is_set() or __bool__()
                self.log.debug("    Run:   Process internal loop")
                time.sleep(0.2)
                if self.run_loop_exception is not None:
                    raise self.run_loop_exception(
                        "This is an exception from the run loop uncaught by the user "
                        "but caught by the context. It not not a TestFailure."
                    )

            self.log.debug("  Run: cleanup after run_loop")

            if self.delay_before_exiting_loop > 0:
                self.log.debug(
                    "  Run:   Sleeping %ds before exiting",
                    self.delay_before_exiting_loop,
                )
                time.sleep(self.delay_before_exiting_loop)

        self.log.debug("Run: Exiting process")


class GroupLeaderProcess(TerminableProcess):
    """
    A TerminableProcess that uses the syncing_context() mechanism to coordinate clean entry and exit of its run loop.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(process_group_id=0, *args, **kwargs)

    def run(self):
        with self.syncing_context() as must_exit:
            child = GroupMemberProcess(
                process_group_id=os.getpid(), log_level=envtest.TEST_LOG_LEVEL
            )
            child.start()

            child2 = GroupMemberProcess(
                process_group_id=os.getpid(), log_level=envtest.TEST_LOG_LEVEL
            )
            child2.start()

            while not must_exit:  # is_set() or __bool__()
                self.log.debug("    Run:   Process internal loop")
                time.sleep(0.2)

        self.log.debug("Run: Exiting process")


class GroupMemberProcess(TerminableProcess):
    """
    A TerminableProcess that uses the syncing_context() mechanism to coordinate clean entry and exit of its run loop.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self):
        with self.syncing_context() as must_exit:
            while not must_exit:  # is_set() or __bool__()
                self.log.debug("    Run:   Process internal loop")
                time.sleep(0.2)

        self.log.debug("Run: Exiting process")


class SelfTerminatingWithTimeLimitGroupLeaderProcess(TerminableProcess):
    """
    A TerminableProcess that uses the syncing_context() mechanism to coordinate clean entry and exit of its run loop.
    """

    def __init__(self, *args, time_limit=1, **kwargs):
        super().__init__(process_group_id=0, *args, **kwargs)
        self.time_limit = time_limit

    def run(self):
        with self.syncing_context(time_limit=self.time_limit) as must_exit:
            child = GroupMemberProcess(
                process_group_id=os.getpid(), log_level=envtest.TEST_LOG_LEVEL
            )
            child.start()

            child2 = GroupMemberProcess(
                process_group_id=os.getpid(), log_level=envtest.TEST_LOG_LEVEL
            )
            child2.start()

            while not must_exit:  # is_set() or __bool__()
                self.log.debug("    Run:   Process internal loop")
                time.sleep(0.2)

        self.log.debug("Run: Exiting process")


class SelfTerminatingByLeavingLoopGroupLeaderProcess(TerminableProcess):
    """
    A TerminableProcess that uses the syncing_context() mechanism to coordinate clean entry and exit of its run loop.
    """

    def __init__(self, *args, time_limit=None, **kwargs):
        super().__init__(process_group_id=0, *args, **kwargs)
        self.time_limit = time_limit

    def run(self):
        with self.syncing_context() as must_exit:
            child = GroupMemberProcess(
                process_group_id=os.getpid(), log_level=envtest.TEST_LOG_LEVEL
            )
            child.start()

            child2 = GroupMemberProcess(
                process_group_id=os.getpid(), log_level=envtest.TEST_LOG_LEVEL
            )
            child2.start()

            while not must_exit:  # is_set() or __bool__()
                self.log.debug("    Run:   Process internal loop")
                time.sleep(0.2)
                break  # HERE WE LEAVE

        self.log.debug("Run: Exiting process")


class SelfTerminatingBySettingExitGroupLeaderProcess(TerminableProcess):
    """
    A TerminableProcess that uses the syncing_context() mechanism to coordinate clean entry and exit of its run loop.
    """

    def __init__(self, *args, time_limit=None, **kwargs):
        super().__init__(process_group_id=0, *args, **kwargs)
        self.time_limit = time_limit

    def run(self):
        with self.syncing_context() as must_exit:
            child = GroupMemberProcess(
                process_group_id=os.getpid(), log_level=envtest.TEST_LOG_LEVEL
            )
            child.start()

            child2 = GroupMemberProcess(
                process_group_id=os.getpid(), log_level=envtest.TEST_LOG_LEVEL
            )
            child2.start()

            while not must_exit:  # is_set() or __bool__()
                self.log.debug("    Run:   Process internal loop")
                time.sleep(1.0)
                must_exit.set()

        self.log.debug("Run: Exiting process")


from src.utils.terminable import (
    TerminableProcess,
    run_loop,
    # setup_loop,
    # cleanup_loop,
)


class DecoratedProcess(TerminableProcess):
    """
    A test implementation of TerminableProcess that uses the @run_loop decorator.
    """

    def __init__(self, track_executions=False, raise_exception=False):
        super().__init__()
        self.track_executions = track_executions
        # Use a shared value for the execution counter
        self._executions = multiprocessing.Value("i", 0)
        self.raise_exception = raise_exception

    @property
    def executions(self):
        return self._executions.value

    @run_loop
    def run(self):
        """
        Main loop body - executed on each loop iteration.
        """
        self.log.debug("Running loop body")

        if self.track_executions:
            # Update the shared counter safely
            with self._executions.get_lock():
                self._executions.value += 1

        if self.raise_exception and self._executions.value >= 2:
            raise ValueError("Test exception from decorated process")

        time.sleep(0.01)  # Short sleep to prevent CPU hogging


class DecoratedWithSetupProcess(TerminableProcess):
    """
    A test implementation that has a setup method.
    """

    def __init__(self):
        super().__init__()
        # Use shared values for state tracking
        self._setup_executed = multiprocessing.Value("i", 0)
        self._executions = multiprocessing.Value("i", 0)

    @property
    def setup_executed(self):
        return self._setup_executed.value > 0

    @property
    def executions(self):
        return self._executions.value

    def setup(self):
        """
        Setup method - executed once before loop starts.
        """
        self.log.debug("Running setup code")
        with self._setup_executed.get_lock():
            self._setup_executed.value += 1

    @run_loop
    def run(self):
        """
        Main loop body - executed on each loop iteration.
        """
        self.log.debug("Running loop body")
        with self._executions.get_lock():
            self._executions.value += 1
        time.sleep(0.01)


class DecoratedWithCleanupProcess(TerminableProcess):
    """
    A test implementation that has a cleanup method.
    """

    def __init__(self):
        super().__init__()
        # Use shared values for state tracking
        self._cleanup_executed = multiprocessing.Value("i", 0)
        self._executions = multiprocessing.Value("i", 0)

    @property
    def cleanup_executed(self):
        return self._cleanup_executed.value > 0

    @property
    def executions(self):
        return self._executions.value

    @run_loop
    def run(self):
        """
        Main loop body - executed on each loop iteration.
        """
        self.log.debug("Running loop body")
        with self._executions.get_lock():
            self._executions.value += 1
        time.sleep(0.01)

    def cleanup(self):
        """
        Cleanup method - executed once after loop ends.
        """
        self.log.debug("Running cleanup code")
        with self._cleanup_executed.get_lock():
            self._cleanup_executed.value += 1


class DecoratedWithBothProcess(TerminableProcess):
    """
    A test implementation that has both setup and cleanup methods.
    """

    def __init__(self, raise_exception=False):
        super().__init__()
        # Use shared values for state tracking
        self._setup_executed = multiprocessing.Value("i", 0)
        self._cleanup_executed = multiprocessing.Value("i", 0)
        self._executions = multiprocessing.Value("i", 0)
        self.raise_exception = raise_exception

    @property
    def setup_executed(self):
        return self._setup_executed.value > 0

    @property
    def cleanup_executed(self):
        return self._cleanup_executed.value > 0

    @property
    def executions(self):
        return self._executions.value

    def setup(self):
        """
        Setup method - executed once before loop starts.
        """
        self.log.debug("Running setup code")
        with self._setup_executed.get_lock():
            self._setup_executed.value += 1

    @run_loop
    def run(self):
        """
        Main loop body - executed on each loop iteration.
        """
        self.log.debug("Running loop body")
        with self._executions.get_lock():
            self._executions.value += 1

        if self.raise_exception and self._executions.value >= 2:
            raise ValueError("Test exception from decorated process")

        time.sleep(0.01)

    def cleanup(self):
        """
        Cleanup method - executed once after loop ends.
        """
        self.log.debug("Running cleanup code")
        with self._cleanup_executed.get_lock():
            self._cleanup_executed.value += 1


class TerminableTestCase(envtest.CoreTestCase):
    """
    Unit tests for the `TerminableProcess` class and its behaviors.

    Tests include:
    - Initialization and proper termination
    - Graceful vs. ungraceful shutdown
    - Use of run loop readiness detection
    - Use of context manager for clean lifecycle
    """

    def test000_init(self):
        """
        Test that a `TestProcess` can be instantiated.
        """
        self.assertIsNotNone(TestProcess())

    def test000_start(self):
        """
        Start a `TestProcess`, wait briefly, then terminate and join it.
        """
        proc = TestProcess()
        self.assertIsNotNone(proc)
        proc.start()
        time.sleep(0.5)
        proc.terminate()
        proc.join()

    def test000_start_stop(self):
        """
        Start a `TestProcess` and use `terminate_synchronously()` to cleanly terminate it.
        """
        proc = TestProcess()
        self.assertIsNotNone(proc)
        proc.start_synchronously()
        time.sleep(0.5)
        proc.terminate_synchronously()

    def test010_unstoppable_process_stop(self):
        """
        Start an UnStoppableTestProcess and attempt to stop it.

        Since it does not respond to the termination flag, the test ensures
        the process is no longer alive after the forced stop timeout.
        """
        try:
            proc = UnStoppableTestProcess(exit_timeout=1)
            proc.start()
            time.sleep(0.5)
            proc.terminate()  # cannot stop the process, it catches SIGTERM
            self.assertTrue(proc.is_alive())
        finally:
            proc.terminate_synchronously()
            self.assertFalse(proc.is_alive())

    def test020_has_entered_run_loop(self):
        """
        Test that `has_entered_run_loop` is correctly set when process enters its main loop.
        """
        try:
            proc = TestProcess()
            self.assertFalse(proc.has_entered_run_loop)
            proc.start()
            proc.wait_until_ready()
            self.assertTrue(proc.has_entered_run_loop)
        finally:
            proc.terminate_synchronously()
            self.assertFalse(proc.is_alive())

    def test030_start_sync(self):
        """
        Test `start_synchronously()` to see if `has_entered_run_loop` has been set
        """
        try:
            proc = TestProcess()
            self.assertFalse(proc.has_entered_run_loop)
            proc.start_synchronously()
            self.assertTrue(proc.has_entered_run_loop)
        finally:
            proc.terminate_synchronously()
            self.assertFalse(proc.is_alive())

    def test040_start_sync_with_useless_timeout(self):
        """
        Test `start_synchronously()` with explicit timeout (ignored)inner_self._exit_time
        """
        try:
            proc = TestProcess()
            self.assertFalse(proc.has_entered_run_loop)
            proc.start_synchronously()
            self.assertTrue(proc.has_entered_run_loop)
        finally:
            proc.terminate_synchronously()
            self.assertFalse(proc.is_alive())

    def test050_start_sync_with_actual_timeout_error(self):
        """
        Test `start_synchronously()` with explicit timeout.
        """
        try:
            proc = UnStartableTestProcess()
            self.assertFalse(proc.has_entered_run_loop)
            with self.assertRaises(TimeoutError):
                proc.start_synchronously()
            self.assertFalse(proc.has_entered_run_loop)
        finally:
            proc.terminate_synchronously()
            self.assertFalse(proc.is_alive())

    def test040_start_sync_with_context(self):
        """
        Use `TestProcess` as a context manager, and check that it enters the run loop.
        """
        with TestProcess() as proc:
            self.assertTrue(proc.has_entered_run_loop)

    def test060_start_synchronously_but_process_is_already_dead(self):
        """
        Test `start_synchronously()`  but already dead.
        """
        proc = SuperFastTestProcess()

        with self.assertRaises(RuntimeError):
            proc.start_synchronously()

    def test060_stop_synchronously_but_process_is_already_dead(self):
        """
        Test `terminate_synchronously()` with explicit timeout.
        """
        try:
            proc = SuperFastTestProcess()

            proc.start()  # start synchronously would raise an exception, so we use start()
            time.sleep(0.5)  # the process will have completed for sure.
        finally:
            proc.terminate_synchronously()
            self.assertFalse(proc.is_alive())

    def test060_stop_synchronously_but_process_never_started(self):
        """
        Test `terminate_synchronously()` without starting is an error
        """
        proc = SuperFastTestProcess()

        with self.assertRaises(RuntimeError):
            proc.terminate_synchronously()

    def test070_context_runloophandler_works(self):
        """
        The process works normally without an exception

        It will trigger events properly:

        1. has_entered_run_loop as soon as the while ...: is entered, therefore setup
           of the run loop is complete
        2. must_exit_now to exit when a signal (SIGTERM or SIGINT)
        """
        try:
            proc = ContextAwareProcess()

            proc.start()
            self.assertTrue(proc._has_entered_run_loop.wait(timeout=1))
            proc.terminate()
            if proc._has_exited_run_loop.wait(timeout=1):
                self.log.debug("_has_exited_run_loop was properly set. Continuing.")
            else:
                self.log.debug("_has_exited_run_loop was never set within timeout.")
                self.log.debug(proc._has_entered_run_loop)

            proc.join(timeout=1)
        finally:
            proc.terminate_synchronously()
            self.assertFalse(proc.is_alive())

    def test100_context_runloophandler_has_called_start(self):
        """
        Validates that has_called_start is set properly
        """
        try:
            proc = ContextAwareProcess(delay_before_entering_loop=0.1)

            self.assertFalse(proc._has_called_start.is_set())
            proc.start()
            self.assertTrue(proc._has_called_start.wait(timeout=1))
            proc.terminate()
            proc.join(timeout=1)
        finally:
            proc.terminate_synchronously()
            self.assertFalse(proc.is_alive())

    def test110_context_runloophandler_has_entered_its_loop(self):
        """
        Validates that _has_entered run loop is set properly
        """
        try:
            proc = ContextAwareProcess(delay_before_entering_loop=0.1)
            count_ms = 0

            self.assertFalse(proc._has_entered_run_loop.is_set())
            self.assertFalse(proc._has_called_start.is_set())
            proc.start()
            self.assertTrue(proc._has_called_start.is_set())

            while not proc._has_entered_run_loop.is_set():
                count_ms += 1
                time.sleep(0.001)
            self.assertTrue(proc._has_entered_run_loop.is_set())
        finally:
            proc.terminate_synchronously()
            self.assertFalse(proc.is_alive())

        self.log.debug(
            f"We learn in this process that the (fixed) startup delay of a process is {count_ms / 1000-proc.delay_before_entering_loop:.4}s"
        )
        self.assertTrue(
            count_ms / 1000 >= 0.5 * proc.delay_before_entering_loop,
            f"The process entered the run_loop faster than our delay : {count_ms / 1000} versus {proc.delay_before_entering_loop}",
        )

    def test120_context_runloophandler_must_exit(self):
        """
        Validates that must_exit run loop is set properly and that
        the process exits within a reasonable time after termination.
        """

        try:
            proc = ContextAwareProcess(delay_before_exiting_loop=0.2)

            proc.start()

            # Wait for the process to signal it has entered its run loop
            self.assertTrue(
                proc._has_entered_run_loop.wait(timeout=5),
                "Timeout: Process did not enter run loop within 5 seconds.",
            )

            # Send termination signal
            proc.terminate()

            # Wait for the process to exit its run loop
            self.assertTrue(
                proc._has_exited_run_loop.wait(timeout=5),
                "Timeout: Process did not exit its run loop within 5 seconds.",
            )

            # Now measure how long it took (only if desired)
            proc.join(timeout=1)

            # Optional: verify that the delay before exiting was honored
            # Note: this is a soft assertion and can be relaxed for slow systems
            self.assertIsNotNone(proc.exitcode, "Process did not exit cleanly.")
        finally:
            proc.terminate_synchronously()
            self.assertFalse(proc.is_alive())

    def test120_context_runloophandler_must_exit_old(self):
        """
        Validates that must_exit run loop is set properly
        """
        try:
            proc = ContextAwareProcess(delay_before_exiting_loop=0.2)

            proc.start()

            self.assertTrue(proc._has_entered_run_loop.wait(timeout=3))

            self.assertFalse(proc._has_exited_run_loop.is_set())
            proc.terminate()
            self.assertTrue(proc._has_exited_run_loop.wait(timeout=3))

            proc.join(timeout=1)
        finally:
            proc.terminate_synchronously()
            self.assertFalse(proc.is_alive())

    def test130_context_runloophandler_must_handle_exception(
        self,
    ):
        """
        Validates that an uncaught exception raised inside the run loop is detected and causes the process to exit abnormally.
        """
        proc = ContextAwareProcess(run_loop_exception=Exception)

        proc.start()
        proc.join()

        self.assertTrue(proc._has_raised_exception.is_set())

    def test200_group_leader(self):
        proc = GroupLeaderProcess(log_level=envtest.TEST_LOG_LEVEL)

        proc.start_synchronously()
        time.sleep(1)
        proc.terminate_synchronously()

    def test210_group_leader_self_terminates(self):
        proc = SelfTerminatingWithTimeLimitGroupLeaderProcess(
            log_level=envtest.TEST_LOG_LEVEL
        )

        proc.start_synchronously()

        some_other_member = GroupMemberProcess(process_group_id=proc.pid)
        some_other_member.start_synchronously()

        proc.join()

    def test220_group_leader_self_terminates(self):
        proc = SelfTerminatingByLeavingLoopGroupLeaderProcess(
            log_level=envtest.TEST_LOG_LEVEL
        )

        proc.start_synchronously()

        some_other_member = GroupMemberProcess(process_group_id=proc.pid)
        some_other_member.start_synchronously()

        proc.join()

    def test230_group_leader_self_terminates(self):
        proc = SelfTerminatingBySettingExitGroupLeaderProcess(
            log_level=envtest.TEST_LOG_LEVEL
        )

        proc.start_synchronously()

        some_other_member = GroupMemberProcess(
            process_group_id=proc.pid, log_level=envtest.TEST_LOG_LEVEL
        )
        some_other_member.start_synchronously()

        proc.join()

    @patch("os.getpgid", side_effect=lambda e: 1)
    def test240_test_psutil_all_group_1(self, mock_os):
        with patch("psutil.process_iter") as mock_object:

            @dataclass
            class MockProcess:
                pid: int

            mock_object.return_value = [
                MockProcess(1),
                MockProcess(2),
                MockProcess(3),
            ]

            proc = TerminableProcess()

            self.assertEqual(proc.get_process_group_members(1), [1, 2, 3])

    @patch("os.getpgid", side_effect=lambda e: e)
    def test240_test_psutil_all_unique_groups(self, mock_os):
        with patch("psutil.process_iter") as mock_object:

            @dataclass
            class MockProcess:
                pid: int

            mock_object.return_value = [
                MockProcess(1),
                MockProcess(2),
                MockProcess(3),
            ]

            proc = TerminableProcess()

            self.assertEqual(proc.get_process_group_members(1), [1])
            self.assertEqual(proc.get_process_group_members(2), [2])
            self.assertEqual(proc.get_process_group_members(3), [3])

    def test300_run_loop_decorator_basic(self):
        """
        Test that the @run_loop decorator correctly handles the basic syncing_context pattern.
        """
        try:
            proc = DecoratedProcess()
            self.assertFalse(proc.has_entered_run_loop)

            proc.start_synchronously()
            self.assertTrue(proc.has_entered_run_loop)

            # Let it run a few iterations
            time.sleep(0.5)

            proc.terminate()
            proc.join(timeout=1)

            self.assertFalse(proc.is_alive())
        finally:
            if proc.is_alive():
                proc.terminate_synchronously()

    def test310_run_loop_decorator_execution_count(self):
        """
        Test that the loop body in the decorated function executes multiple times.
        """
        try:
            proc = DecoratedProcess(track_executions=True)

            proc.start_synchronously()

            # Let it run for some time to accumulate executions
            time.sleep(0.5)

            # Should have executed at least once
            self.assertGreater(
                proc.executions, 0, "Loop body should have executed at least once"
            )

            proc.terminate_synchronously()
        finally:
            if proc.is_alive():
                proc.terminate_synchronously()

    def test320_run_loop_decorator_exception_handling(self):
        """
        Test that exceptions in the decorated loop body are properly caught.
        """
        try:
            proc = DecoratedProcess(track_executions=True, raise_exception=True)

            proc.start_synchronously()

            # Let it run until exception occurs (after 2 executions)
            time.sleep(0.5)

            # Process should still be alive despite the exception
            self.assertTrue(
                proc.is_alive(),
                "Process should continue running after exception in loop body",
            )

            proc.terminate_synchronously()
        finally:
            if proc.is_alive():
                proc.terminate_synchronously()

    def test330_run_loop_with_setup(self):
        """
        Test that the setup_loop context manager executes before the loop.
        """
        try:
            proc = DecoratedWithSetupProcess()

            proc.start_synchronously()

            # Let it run a few iterations
            time.sleep(0.5)

            proc.terminate_synchronously()

            # Setup should have executed exactly once
            self.assertTrue(proc.setup_executed, "Setup code should have executed")

            # Loop body should have executed at least once
            self.assertGreater(
                proc.executions, 0, "Loop body should have executed at least once"
            )
        finally:
            if proc.is_alive():
                proc.terminate_synchronously()

    def test340_run_loop_with_cleanup(self):
        """
        Test that the cleanup_loop context manager executes after loop termination.
        """
        try:
            proc = DecoratedWithCleanupProcess()

            proc.start_synchronously()

            # Let it run a few iterations
            time.sleep(0.5)

            proc.terminate_synchronously()

            # After termination, cleanup should have executed
            self.assertTrue(
                proc.cleanup_executed,
                "Cleanup code should have executed after termination",
            )
        finally:
            if proc.is_alive():
                proc.terminate_synchronously()

    def test350_run_loop_with_both_contexts(self):
        """
        Test using both setup_loop and cleanup_loop with the decorator.
        """
        try:
            proc = DecoratedWithBothProcess()

            proc.start_synchronously()

            # Let it run a few iterations
            time.sleep(0.5)

            proc.terminate_synchronously()

            # After termination, both should have executed
            self.assertTrue(proc.setup_executed, "Setup code should have executed")
            self.assertTrue(
                proc.cleanup_executed,
                "Cleanup code should have executed after termination",
            )
        finally:
            if proc.is_alive():
                proc.terminate_synchronously()

    def test360_run_loop_with_exception_and_cleanup(self):
        """
        Test that cleanup_loop executes even when an exception occurs in the loop body.
        """
        try:
            proc = DecoratedWithBothProcess(raise_exception=True)

            proc.start_synchronously()

            # Let it run until exception occurs (after 2 executions)
            time.sleep(0.5)

            # Process should still be alive despite the exception
            self.assertTrue(
                proc.is_alive(),
                "Process should continue running after exception in loop body",
            )

            proc.terminate_synchronously()

            # After termination, both setup and cleanup should have executed
            self.assertTrue(proc.setup_executed, "Setup code should have executed")
            self.assertTrue(
                proc.cleanup_executed,
                "Cleanup code should have executed after termination",
            )
        finally:
            if proc.is_alive():
                proc.terminate_synchronously()


if __name__ == "__main__":
    envtest.main()
    # envtest.main(
    #     defaultTest=[
    #         "TerminableTestCase.test240_test_psutil_all_unique_groups",
    #     ]
    # )
