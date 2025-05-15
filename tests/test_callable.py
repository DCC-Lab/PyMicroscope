"""
Test suite for validating inter-process communication and attribute resolution
in CallableProcess-based subprocesses.

This module defines a `TestProcess` class extending `CallableProcess`, used to verify:
- Proper propagation and isolation of state between parent and child processes.
- Behavior of method and attribute resolution both locally and across processes.
- Command queue handling and error detection when disabled.
- Integrity of variable access when using `call_method`, `call_method_remotely`, and `get_property`.
"""

import time
import logging
from threading import Thread
from multiprocessing import Value
from queue import Empty

import envtest  # setup environment for testing
from src.utils import TerminableProcess, CallableProcess, Reply


class TestProcess(CallableProcess):
    """A minimal subclass of CallableProcess for unit testing variable access and IPC behavior.

    CallableProcess is also a TerminableProcess so it can manage its termination properly
    """

    def __init__(
        self,
        no_check=False,
        delay_before_check=0,
        delay_after_check=0,
        test_process_loop_timeout=4,
        *args,
        **kwargs,
    ):
        """
        Initialize the test process with internal state and optional command queue checking.

        Args:
            no_check (bool): If True, disables the command queue checking during run.
            slow_run_loop (bool): If true, slows down the loop
        """
        super().__init__(*args, **kwargs)

        self.a = 1
        self.b = 2

        self._no_check = no_check
        self.delay_before_check = delay_before_check
        self.delay_after_check = delay_after_check
        self._test_process_loop_timeout = test_process_loop_timeout
        self.call_count = Value("i", 0)

    def run(self):
        """
        Entry point for the test subprocess.

        """
        with self.syncing_context(
            time_limit=self._test_process_loop_timeout
        ) as must_terminate_now:
            self.a = 4  # to confirm self.a is different inside and outside run()

            while not must_terminate_now:
                time.sleep(self.delay_before_check)

                if self._no_check:
                    continue

                self.check_command_queue()

                time.sleep(self.delay_after_check)

            self._exit_now_signal_flag = True
            self.check_command_queue()

    def increase_call_count(self):
        with self.call_count.get_lock():
            self.call_count.value += 1

    def get_a(self):
        return self.a

    def slow_get_a(self, delay):
        time.sleep(delay)
        return self.a

    def slow_get_a_and_count(self, delay):
        self.increase_call_count()
        return self.slow_get_a(delay)

    def set_a(self, value):
        self.a = value

    def set_b(self, value):
        self.b = value

    def get_b(self):
        return self.b


class CallableTestCase(envtest.CoreTestCase):  # pylint: disable=too-many-public-methods
    """Unit tests for the callable process interface using TestProcess."""

    def setUp(self):
        super().setUp()
        """
        Set up a shared variable for introspection tests.
        """
        self.variable = 1

    def test000_init(self):
        """Ensure TestProcess initializes without error."""
        self.assertIsNotNone(TestProcess())

    def test010_starts_properly_no_exception(self):
        """Test that the process starts and terminates without raising exceptions."""
        proc = TestProcess()
        proc.start()
        time.sleep(0.3)
        proc.terminate()

    def test020_start_copies_variables_local_dont_change(self):
        """
        Ensure local variables in the parent are not affected by the child process mutation.
        """
        proc = TestProcess()
        self.assertEqual(proc.a, 1)
        proc.start_synchronously()  # the run() command changes 'a'
        self.assertEqual(proc.a, 1)
        self.assertTrue(proc.get_property("a") != proc.a)
        self.assertEqual(proc.a, 1)
        proc.terminate_synchronously()
        self.assertEqual(proc.a, 1)

    def test025_getattr_understanding(self):
        """
        Test Python's getattr to retrieve a dynamically named attribute.
        """
        self.variable = 2
        the_property = getattr(self, "variable")
        self.assertIsNotNone(the_property)
        self.assertEqual(the_property, 2)

    def test030_resolve_method_not_started(self):
        """
        Test resolution of method names on the parent object before the process is started.
        """
        proc = TestProcess()
        target, _ = proc._resolve("self", "set_a")  # pylint: disable=protected-access
        self.assertEqual(target, proc)

    def test030_resolve_property_not_started(self):
        """
        Test resolution of attribute names on the parent object before the process is started.
        """
        proc = TestProcess()
        target, prop = proc._resolve("self", "a")  # pylint: disable=protected-access
        self.assertEqual(prop, 1)
        self.assertEqual(target, proc)

    def test040_resolve_locally_method_started(self):
        """
        Resolve a method name in a subprocess after it has been started.
        """
        proc = TestProcess()
        proc.start_synchronously()
        target, method = proc._resolve(  # pylint: disable=protected-access
            "self", "set_a"
        )
        self.assertEqual(target, proc)
        self.assertIsNotNone(method)
        proc.terminate_synchronously()

    def test040_resolve_locally_property_started(self):
        """
        Resolve an attribute name in a subprocess after it has been started.
        """
        proc = TestProcess()
        proc.start_synchronously()

        target, prop = proc._resolve("self", "a")  # pylint: disable=protected-access
        self.assertEqual(prop, 1)
        self.assertEqual(target, proc)
        proc.terminate_synchronously()

    def test040_get_remotely_method_started_but_no_check(self):
        """
        Verify RuntimeError is raised when calling a method remotely with no check.
        """
        proc = TestProcess(no_check=True)
        proc.start_synchronously()
        self.assertFalse(proc.has_checked_commands)
        with self.assertRaises(TimeoutError):
            _ = proc.call_method_remotely("self", "set_a", method_args=(10,))
        proc.terminate_synchronously()

    def test040_get_remotely_property_started_but_no_check(self):
        """
        Verify RuntimeError is raised when accessing a property remotely with no check.
        """
        proc = TestProcess(no_check=True)
        proc.start_synchronously()
        self.assertFalse(proc.has_checked_commands)
        with self.assertRaises(TimeoutError):
            _ = proc.call_method_remotely("self", "a", method_args=(10,))
        proc.terminate_synchronously()

    def test040_get_remotely_method_started_with_check(self):
        """
        Test remote call to a method after command checking is enabled.

        Validates that state changes in subprocess are correctly returned
        without affecting parent process state.
        """
        proc = TestProcess()
        proc.start_synchronously()
        result = proc.call_method("self", "get_a")
        self.assertEqual(result, 4)  # has changed
        self.assertEqual(proc.a, 1)  # has not changed
        proc.terminate_synchronously()

    def test040_get_property_started_with_check(self):
        """
        Test remote property access after command checking is enabled.
        """
        proc = TestProcess()
        proc.start_synchronously()
        result = proc.get_property("a")
        self.assertEqual(result, 4)  # has changed
        self.assertEqual(proc.a, 1)  # has not changed
        proc.terminate_synchronously()

    def test040_get_property_with_call_method_started_with_check(self):
        """
        Test property access via `call_method` interface with subprocess command checking.
        """
        proc = TestProcess()
        proc.start_synchronously()
        result = proc.call_method("self", "a")
        self.assertEqual(result, 4)  # has changed
        self.assertEqual(proc.a, 1)  # has not changed
        proc.terminate_synchronously()

    def test040_get_property_with_call_method_remotely_started_with_check(self):
        """
        Test remote property access using `call_method_remotely` with subprocess checking enabled.
        """
        proc = TestProcess()
        proc.start_synchronously()
        reply = proc.call_method_remotely("self", "a")
        self.assertEqual(reply.result, 4)  # has changed
        self.assertEqual(proc.a, 1)  # has not changed
        proc.terminate_synchronously()

    def test040_get_method_locally(self):
        """
        Call method on process object without starting it, purely local execution.
        """
        proc = TestProcess()
        result = proc.call_method("self", "get_a")
        self.assertEqual(result, proc.a)  # has not changed

    def test040_get_property_locally(self):
        """
        Get property on process object without subprocess, purely local access.
        """
        proc = TestProcess()
        result = proc.get_property("a")  # what a wasteful way of doing things == proc.a
        self.assertEqual(result, proc.a)  # has not changed

    def test040_get_property_locally_with_call_method(self):
        """
        Get property locally using the call_method interface (same as getattr).
        """
        proc = TestProcess()
        result = proc.call_method("self", "a")
        self.assertEqual(result, proc.a)  # has not changed

    def test050_call_nonexistent_method(self):
        """
        Exceptions raised remotely are caught and raised locally with nonexistent_method
        """

        proc = TestProcess()
        proc.start_synchronously()
        with self.assertRaises(CallableProcess.RemoteException):
            proc.call_method("self", "nonexistent_method")
        proc.terminate_synchronously()

    def test051_get_nonexistent_property(self):
        """
        Exceptions raised remotely are caught and raised locally with nonexistent attributes
        """
        proc = TestProcess()
        proc.start_synchronously()
        with self.assertRaises(CallableProcess.RemoteException):
            proc.get_property("nonexistent_attribute")
        proc.terminate_synchronously()

    def test052_set_property_remotely(self):
        """
        Can we set a property remotely
        """
        proc = TestProcess()
        proc.start_synchronously()
        proc.call_method("self", "set_a", method_args=(42,))
        self.assertEqual(proc.call_method("self", "get_a"), 42)
        proc.terminate_synchronously()

    def test055_call_remote_method_ignore_return(self):
        """
        Can we ignore return value and return quickly, but compute all of them
        """
        proc = TestProcess()
        proc.start_synchronously()
        start_time = time.time()

        for i in range(10):
            proc.call_method("self", "increase_call_count", ignore_result=True)
        elapsed_time = time.time() - start_time
        self.assertTrue(elapsed_time < 1, f"Elapsed time was: {elapsed_time}")
        time.sleep(2)
        self.assertEqual(proc.call_count.value, 10)
        proc.terminate_synchronously()

    def test057_call_remote_method_ignore_return_and_discard(self):
        """
        Can we ignore return value and return quickly, but discard all but one
        if too slow and overflowing the queue
        """
        proc = TestProcess(delay_after_check=0.5, test_process_loop_timeout=0.8)
        proc.start_synchronously()
        start_time = time.time()

        for i in range(10):
            proc.call_method(
                "self",
                "slow_get_a_and_count",
                method_args=(0.5,),
                ignore_result=True,
                is_discardable=True,
            )

        elapsed_time = time.time() - start_time
        self.assertTrue(elapsed_time < 0.1, f"Elapsed time was: {elapsed_time}")
        time.sleep(1.1)  # cannot take more than 10*0.1s
        # So slow will discard every but one
        self.assertEqual(proc.call_count.value, 1)
        proc.terminate_synchronously()

    def test058_call_remote_method_ignore_return_and_not_discardable(self):
        """
        If too slow and non discardable, will kill everything before its done.
        """
        proc = TestProcess(delay_after_check=0.5, test_process_loop_timeout=0.8)
        proc.start()
        time.sleep(0.1)
        start_time = time.time()

        for i in range(10):
            proc.call_method(
                "self",
                "slow_get_a_and_count",
                method_args=(1.0,),
                ignore_result=True,
                is_discardable=False,
            )

        elapsed_time = time.time() - start_time
        self.assertTrue(elapsed_time < 0.1, f"Elapsed time was: {elapsed_time}")
        time.sleep(1)
        proc.terminate_synchronously()
        self.assertTrue(proc.call_count.value > 0 and proc.call_count.value < 10)

    def test060_many_concurrent_calls(self):
        """
        Validate concurrency: can we call periodically without losing synchronization?
        """

        def thread_calling(proc: TestProcess, duration: float, variable: str):
            start_time = time.time()
            while time.time() - start_time < duration:
                if variable == "a":
                    proc.set_a(2)
                else:
                    proc.set_b(3)

        duration = 3
        proc = TestProcess()
        proc.start_synchronously()

        thread1 = Thread(target=thread_calling, args=(proc, duration, "a"))
        thread2 = Thread(target=thread_calling, args=(proc, duration, "b"))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        proc.terminate_synchronously()

    def test060_slow_and_fast_concurrent_calls(self):
        """
        Validate concurrency: can we call periodically without losing synchronization?
        """

        def thread_calling(proc: TestProcess, duration: float, variable: str):
            start_time = time.time()
            while time.time() - start_time < duration:
                if variable == "a":
                    proc.set_a(2)
                    slow_a = proc.slow_get_a(0.1)
                    self.assertEqual(slow_a, 2)
                else:
                    proc.set_b(3)
                    b = proc.get_b()
                    self.assertEqual(b, 3)

        duration = 3
        proc = TestProcess()
        proc.start_synchronously()

        thread1 = Thread(target=thread_calling, args=(proc, duration, "a"))
        thread2 = Thread(target=thread_calling, args=(proc, duration, "b"))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        proc.terminate_synchronously()

    def test100_properly_drains_commands_queue_before_quitting(self):
        """
        When quitting, we would like to make sure we have executed all commands
        that have been put on the queue.  CallableProcess upon quitting
        will set is_accepting_commands to False, and further calls to
        call_method_remotely will raise an exception for the caller

        We then call check_command_queue() (inside the run loo) one last time,
        because it always empties the queue.

        If it takes too long, then terminate_synchronously() will actually kill it.

        """

        proc = TestProcess(delay_after_check=2)
        proc.start_synchronously()

        for i in range(10):
            reply = proc.call_method(
                "self",
                "slow_get_a_and_count",
                method_args=(0.1,),
                ignore_result=True,
                is_discardable=False,
            )
            self.assertEqual(reply, None)
        time.sleep(5)
        proc.terminate_synchronously()  # Process should take 3 seconds, but complete: default timeout is 5
        with proc.call_count.get_lock():
            self.assertEqual(proc.call_count.value, 10)

    def test120_wait_event_timeout(self):
        """
        The CallableProcess needs to have entered the loop
        and start checking the queue before we can put commands on the queue.
        This is checked in the call_method_remotely method.

        It is not a queue timeout, it is a timeout due to the Process
        not being ready yet.
        """

        with TestProcess(no_check=True, event_timeout=1.0) as proc:
            start_time = time.time()
            with self.assertRaises(TimeoutError):
                result = proc.call_method("self", "get_a")
            self.assertAlmostEqual(time.time() - start_time, 1.0, 1)

    def test130_call_method_timeout(self):
        """
        The call_timeout is the amount of the we are willing to wait for a
        call_method_remotely to complete. After that, the command may
        complete, but will will ignore the result.  We do not have to worry
        about the reply_queue because it is a private queue for this command only.
        It is simply ignored.
        """

        with TestProcess(call_timeout=2.0, loop_timeout=None) as proc:
            start_time = time.time()
            with self.assertRaises(TimeoutError):
                result = proc.call_method(
                    "self",
                    "slow_get_a",
                    method_args=(3,),
                )
            self.assertAlmostEqual(time.time() - start_time, 2, 0)

    def test140_loop_timeout_for_spinning(self):
        """
         The loop_timeout is the check_command_queue timeout within the
         loop.  There are two important situations that are completely different
         and deserve two very different timeouts. A callableProcess may have two
         different pruposes:

         1. It is accepting to be called remotely BUT DOES OTHER things in between.
            This situation requires that check_command_queue returns quickly if it is empty.
            A timeout of 1s would really slow down the loop for its other tasks.

            This is the case for "A Process" that does many things, including executing commands
            self.loop_timeout=None is optimal

        2. Its sole purpose is to watch the queue for a command to appear and then run it
            and looping again. In this case, the timeout must be higher to avoid spinning
            like a madman waiting for something to show up.  A timeout of 1s will not slow down
            the loop, it will make it efficient.

            This is the case for "An Agent" that does one thing:
            self.loop_timeout=0.5 is reasonable



        """

        # An Agent spinning and executing commands quickly
        with TestProcess(loop_timeout=None, test_process_loop_timeout=4) as proc:
            start_time = time.time()
            for i in range(100):
                result = proc.call_method_remotely("self", "increase_call_count")
            self.assertEqual(proc.call_count.value, 100)
            elapsed_time = time.time() - start_time
            self.assertTrue(
                elapsed_time < 2.0, f"Took {elapsed_time}s instead of less than 1.0s"
            )

        # A Process doing other things: once it enters the check_command_queue
        # method, it will get() and empty the queue esentially and be very quick
        # even if the loop is in fact a bit slow (delay_after_check=0.2)
        with TestProcess(
            loop_timeout=0.5, delay_after_check=0.2, test_process_loop_timeout=4
        ) as proc:
            start_time = time.time()
            for i in range(100):
                result = proc.call_method_remotely("self", "increase_call_count")
            self.assertEqual(proc.call_count.value, 100)
            self.assertTrue(time.time() - start_time < 2.0)


if __name__ == "__main__":
    envtest.main()
