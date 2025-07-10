"""
Provides `TerminableProcess`, a `multiprocessing.Process` subclass that
handles termination gracefully using OS-level signal handlers.

This class is designed for processes that interact with hardware or shared
system resources (e.g., cameras, I/O devices) that must be terminated cleanly
to ensure resources are properly released and not left in a locked or
undefined state.

To do so, it manages the life cycle of the Process with various events that
indicate where the execution is.  With a context-aware syntax and
syncing_context, we can manage everything automatically.

Finally, it is possible to group processes in a "process group" and then
send a signal (e.g., SIGTERM) to every process in the group. This is
perfect to request a clean exit from several interconnected processes
instead of abruptly terminating them.


Key Features:
-------------
- Overrides signal handling for `SIGINT` and `SIGTERM` to set an internal
  termination flag.
- Introduces `must_terminate_now` for clean shutdown logic in the `run
  ()` loop.
- Provides `start_synchronously()` and `terminate_synchronously()` for
  reliable process lifecycle control.
- Implements context manager support (`__enter__`/`__exit__`) for safe usage
  in `with` blocks.
- Eliminates race conditions commonly caused by arbitrary sleep-based
  readiness checks.
- Provides a syncing_context() to manage the life cycle automatically.

Usage:
------
Subclass `TerminableProcess` and override `run()`:

    class MyProcess(TerminableProcess):
        def run(self):
            self.install_signal_handlers()
            while not self.must_terminate_now:
                do_some_work()

Use synchronously or with context manager:

    p = MyProcess()
    p.start_synchronously()
    ...
    p.terminate_synchronously()

    # or

    with MyProcess() as p:
        do_something()

Notes:
------
- The class is compatible with Python 3.8+ and respects `join_timeout`.

"""
from multiprocessing import Event
import os
import signal
import time
from typing import Any, Optional, Callable, Type
from types import TracebackType
from contextlib import contextmanager
import warnings
import functools

import psutil


#from pymicroscope.utils import LoggableProcess
from pymicroscope.utils import LoggableProcess


def deprecated(reason: str = ""):
    """Decorator to mark functions as deprecated with a reason."""

    def decorator(func):
        message = f"Call to deprecated function '{func.__name__}'. {reason}"

        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            warnings.warn(
                message,
                category=DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)

        return wrapped

    return decorator


class TerminableProcess(LoggableProcess):
    """
    A process subclass that can be terminated cleanly using signal handlers.

    This is very important with classes that use global hardware resources
    (camera, IO, etc...) All processes need to terminate cleanly to avoid
    holding the resources and blocking them for use.

    Example:
        class MyProc(TerminableProcess):
            def run(self):
                self.install_signal_handlers()
                while not self.must_terminate_now:
                    work()

    Elsewhere:

    proc = MyProc()
    proc.start()
    ...
    proc.terminate() # to unambiguously shutdown for sure
    """

    def __init__(
        self,
        *args: Any,
        start_timeout: float = 5,
        exit_timeout: float = 5,
        process_group_id=None,
        **kwargs: Any,
    ) -> None:
        """
        Initializes a TerminableProcess with internal lifecycle events
        and sets up termination signaling.

        Note:
        -----
        The _exit_now_signal_flag must be a boolean because it is set
        inside a signal handler. Setting an Event() in a signal handler
        can cause deadlocks if the signal is received during a critical
        section.
        """
        super().__init__(*args, **kwargs)
        self.prev_sigint_handler = None
        self.prev_sigterm_handler = None

        self.start_timeout = start_timeout  # timeouts going in
        self.exit_timeout = exit_timeout  # timeouts coming out
        self.process_group_id = process_group_id

        self._has_called_start = Event()
        self._has_entered_run_context = Event()
        self._has_entered_run_loop = Event()
        self._has_raised_exception = Event()
        self._has_exited_run_loop = Event()
        self._will_exit_run_context = Event()

        # This variable is only set for the subprocess and is private
        # We also set a low-level timeout thatshould not be changed
        # This is wrong: self._exit_now = Event()
        self._exit_now_signal_flag = False

    def start(self):
        self._has_called_start.set()

        super().start()

    def start_synchronously(self, timeout: float = None):
        """
        This is called from the main thread.

        The goal of this method is to wait until the run() method has entered
        its loop. It is not sufficient to check is_alive() [it is a race
        condition] because it may be set but we have not really entered the
        loop.

        Normally, the run() method will check self.must_terminate_now like
        so:

        while not self.must_terminate_now:
            # Something


        but it is not guaranteed since the user of the class writes the run
        method. The property self._has_entered_run_loop will be set when
        accessing self.must_terminate_now (go see @property
        must_terminate_now), so we can use this as a guide that:

        1. we entered the loop without having the user of the class to flag it
        manually and we are ready to proceed.

        2. that the subclass is really using must_terminate_now to leave the
        run method properly(it is modified by the signal handlers). So if
        self._has_entered_run_loop is never set, then we know the subclass
        is not using the TerminableProcess parent class properly.

        Finally, the run() method could zip through so fast that it is done
        before we even have time to check anything.
        Again, _has_entered_run_loop should be set but there could be an
        error in the run() method of the subclass. But we can use
        `self.exitcode` to see if the process has actually terminated
        already. This would essentially correspond to an empty run() method.

        _has_entered_run_loop.wait is an Event(): we can `wait` for that event.
        If when waiting we timeout, then wait() will return False and we know
        something is wrong, but it could be an incorrect run() method.


        """
        if timeout is not None:
            warnings.warn(
                "'timeout' is deprecated and will be removed in a future version. "
                "Use the class property 'start_timeout' instead.",
                category=DeprecationWarning,
                stacklevel=2,
            )

        self.start()

        if not self._has_entered_run_loop.wait(self.start_timeout):
            if self.exitcode is not None:
                raise RuntimeError(
                    "TerminableProcess started and exited immediately without entering "
                    "the run_loop once. Check your run() method for errors "
                    "before entering the run_loop"
                )

            raise TimeoutError(
                f"Process has not started within {self.start_timeout}s. It could be started or not."
            )

    def wait_until_ready(self, timeout: float = None):
        """
        Convenience method for users of the class, to confirm the process
        is ready. We consider the process ready if it has entered the run loop.

        Using start_synchronously() would perform the same check, but it is
        not always possible to use it.

        Checking is_alive() is not sufficient, because the setting up at the
        beginning of the run() may take some time. This avoids this problem.
        """
        if timeout is not None:
            warnings.warn(
                "'timeout' is deprecated and will be removed in a future version. "
                "Use the class property 'start_timeout' instead.",
                category=DeprecationWarning,
                stacklevel=2,
            )

        if not self._has_entered_run_loop.wait(self.start_timeout):
            raise TimeoutError(
                f"The process was never ready within {self.start_timeout}s. "
                "Make sure the run() method uses syncing_context"
            )

    @property
    def has_entered_run_loop(self):
        """
        For convenience for users of the class.

        When starting a process, we may want to make sure it is "actually"
        started before calling various methods.

        Remember that start_synchronously() does just that.

        """
        return self._has_entered_run_loop.is_set()

    def terminate_synchronously(self, timeout: float = None) -> int:
        """

        Terminate and joins the process, sending SIGKILL if necessary. The
        opposite of Process.start_synchronously()

        timeout is the maximum of time you are willing to wait before it is
        killed for sure. This depends on what the process does: are you willing
        to kill it abruptly or are you willing to wait?

        We return the exitcode : will be zero if it exited normally, -9 if KILLed
        """
        if timeout is not None:
            warnings.warn(
                "'timeout' is deprecated and will be removed in a future version. "
                "Use the class property 'exit_timeout' instead.",
                category=DeprecationWarning,
                stacklevel=2,
            )

        if not self._has_called_start.wait(self.start_timeout):
            raise RuntimeError("Process has not been started")

        if self.is_alive():
            self.terminate()  # This will set the _exit_flag
            self.join(timeout=self.exit_timeout)
            if self.is_alive():
                os.kill(self.pid, signal.SIGKILL)  # kill -KILL will abruptly terminate
                self.join()

        return self.exitcode

    def terminate_group(self) -> int:
        """
        If a process is the group leader, then it is allowed to send
        SIGTERM to other processes so they can exit nicely.

        Note: if they DO NOT exit nicely, currently nothing is done.
        """
        if self.is_group_leader:
            self.log.debug(
                "Sending SIGTERM to group members %s", self.get_process_group_members()
            )
            os.killpg(os.getpid(), signal.SIGTERM)

    @property
    def is_group_leader(self):
        """
        A process is a group leader if its process id is its group id
        """
        return os.getpid() == os.getpgrp()

    def get_process_group_members(self, pgid=None):
        """
        Convenience function to get the members of a group for information
        """
        if pgid is None:
            pgid = os.getpgrp()  # get this process's group ID

        members = []
        for proc in psutil.process_iter(attrs=["pid"]):  # Only safe attributes
            try:
                if proc.pid != 0 and os.getpgid(proc.pid) == pgid:
                    members.append(proc.pid)
            except (
                psutil.NoSuchProcess,
                ProcessLookupError,
                psutil.AccessDenied,
            ):
                continue
        return members

    def install_signal_handlers(self) -> None:
        """
        terminate() send a signal SIGINT or SIGTERM.  The most robust handling of
        process termination is to handle SIGINT and SIGTERM (which is a OS-level feature).
        We intercept the SIG and set a interrupt safe bool. WE CANNOT SET AN EVENT
        AT INTERRUPT TIME.
        The run loop must check on each loop if a termination has been requested by checking
        self._exit_now_signal_flag or (self.must_terminate_now for simplicity)
        and then exit as soon as possible after having cleared resources.

        If it does not do so quickly, it will get abruptly killed.
        """

        def exit_gracefully(signum, frame):  # pylint: disable=unused-argument
            self._exit_now_signal_flag = True

        self.prev_sigint_handler = signal.signal(
            signal.SIGINT, exit_gracefully
        )  # Intercepts SIGINT, will set flag
        self.prev_sigterm_handler = signal.signal(
            signal.SIGTERM, exit_gracefully
        )  # Same

    @property
    def is_quitting(self):
        """
        If we received _exit_now_signal_flag=True and we have exited the run loop
        we are quitting.  This is helpful for indicating we are in the process
        of cleaning up and should not accept items on queues for instance.
        """
        return self._exit_now_signal_flag or self._has_exited_run_loop.is_set()

    def deinstall_signal_handlers(self):
        """
        When we quit, we should return the SIGINT and SIGTERM to what they
        were. It should be completely useless since we are leaving this
        process any minute now, why put back the old handler?

        After your function exits, there is other code remaining to cleanup
        and it could raise an exception or something unhandled. The problem
        is that your SIG handler will prevent properly handling outside of
        your run(). It is safer to return the old handlers.

        """
        signal.signal(signal.SIGINT, self.prev_sigint_handler)
        signal.signal(signal.SIGTERM, self.prev_sigterm_handler)

    def __enter__(self):
        """
        A context-aware Process that start the process and wait for it to be
        ready. Supports usage with the `with` statement:

        with TerminableProcess() as proc:
            # blabla

        and be sure it is started and then terminated within the context.

        Returns: self (TerminableProcess): the process instance itself.
        """
        self.start_synchronously()

        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ):
        """
        Ensures that the process is terminated cleanly on context exit,
        regardless of exception state.
        """
        self.terminate_synchronously()

    @contextmanager
    def syncing_context(
        self,
        on_loop_check: Callable[[], None] = None,
        on_loop_exit: Callable[[], None] = None,
        time_limit: float = None,
    ):
        """
        This is a complex and critical, but is a very important object: it
        allows the life cycle management of the process and its "run" method.

        It will go through the following events:

        1. _has_entered_run_context
           The setup code is run here before entering the loop
        2. _has_entered_run_loop
        3. call optional on_run_loop function
        4. periodically check bool(_exit_now_signal_flag), possibly catch
           exception and then set _has_raised_exception

           If time_limit is passed, will set _exit_now_signal_flag
        5. _has_exited_run_loop
           The clean up code is run here and must be short before leaving the context
        6. If the process is part of a group and the group leader, then it sends
           SIGTERM to the group.
        7. _will_exit_run_context

        It is used like this:


        with syncing_context(on_loop_check=somefunction, on_loop_exit=otherfunction) as must_exit_now:
            try:
                # setup code here

                while not must_exit_now: # this will call somefunction() everytime
                    # run loop code here
                    # You can do must_exit_now.set() if you want to quit.

                # it is ok to let exceptions propagate to the syncing_context
            except:
                # whatever you want to manage
            finally:
                #

            # when leaving syncing_context:
            # clean up code here otherfunction()
        """

        def is_process_alive(pid: int) -> bool:
            try:
                os.kill(pid, 0)  # Signal 0 does not kill, but checks for existence
            except ProcessLookupError:
                return False  # No such process
            except PermissionError:
                return True  # Exists but not accessible (different user, etc)

            return True

        self._has_entered_run_context.set()
        self.log.context("Entering context")
        self.log.context("Installing signal_handlers")
        self.install_signal_handlers()
        if self.process_group_id is not None:
            if self.process_group_id == 0:
                self.log.context(
                    f"Setting as process group leader {self.process_group_id}"
                )
            else:
                self.log.context(
                    f"Setting as member of process group {self.process_group_id}"
                )
            try:
                os.setpgid(0, self.process_group_id)
            except PermissionError as err:
                if not is_process_alive(self.process_group_id):
                    raise PermissionError(
                        f"Group leader {self.process_group_id} is not alive"
                    ) from err

        try:
            yield self._loop_runner(on_loop_check, time_limit=time_limit)
        except Exception as err:
            self.log.context(f"  Exception : {err}")
            self._has_raised_exception.set()
            self._exit_now_signal_flag = True
            raise  # Let the Process system machinery catch it, a traceback will be printed
        finally:
            self.log.context(" _has_exited_run_loop.set()")
            self._has_exited_run_loop.set()
            if on_loop_exit is not None:
                self.log.context(" Calling cleanup")
                on_loop_exit()
            if self.is_group_leader:
                self.log.context(" Requesting exit from children")
                self.terminate_group()

            self.log.context("Deinstalling signal_handlers")
            self.deinstall_signal_handlers()
            self.log.context("Exiting context")
            self._will_exit_run_context.set()

    def _loop_runner(
        self, on_loop_check: Callable[[], None] = None, time_limit: float = None
    ):
        # pylint: disable=no-self-argument
        class LoopWrapper:
            """
            Helper class for syncing_context that is necessary so we can:

            1. call on_run_loop every time
            2. set _has_entered_run_loop
            3. return self._exit_now_signal_flag

            """

            def __init__(inner_self):
                inner_self._exit_time = None
                if time_limit is not None:
                    inner_self._exit_time = time.time() + time_limit

                self.log.context(
                    f"   Entering loop wrapper with must_exit_now: {self._exit_now_signal_flag} [exit time: {inner_self._exit_time}]"
                )
                self.on_loop_check = on_loop_check

            def __bool__(inner_self):
                # When we are here:
                # 1. We are checking the loop exit condition, so we have entered the loop
                # 2. We can call on_loop_check periodically for the user
                if self.on_loop_check is not None:
                    self.on_loop_check()

                self._has_entered_run_loop.set()

                if (
                    inner_self._exit_time is not None
                    and time.time() > inner_self._exit_time
                ):
                    self._exit_now_signal_flag = True

                return self._exit_now_signal_flag

            def set(inner_self):
                """
                Cleanest method to leave the run loop: set the exit manually
                It is not strictly necessary, since exiting the loop will
                eventually exit the context, and once we are exiting the context
                we know we have exited the run_loop.  However, there will
                be a delay when we appear in the loop although we are not.
                """
                self.log.context("   Setting _must_exit_now manually")
                self._exit_now_signal_flag = True

        return LoopWrapper()

    @deprecated("Use terminate_synchronously()")
    def stop(self, timeout: float = None) -> int:
        """
        A synonym for convenience, but should be removed.
        """
        return self.terminate_synchronously(timeout)

    @deprecated("Use terminate_synchronously()")
    def shutdown(self) -> None:
        """
        For compatiblity only
        """
        self.terminate_synchronously()

    @property
    @deprecated(
        "Use `with syncing_context() as must_terminate_now` and check must_terminate_now"
    )
    def must_terminate_now(self) -> bool:
        """
        For compatiblity in the loop to check the exit flag:
        use syncing_context instead

        But we use this also to validate the user of the subclass has checked
        in the run() loop.
        """
        self._has_entered_run_loop.set()

        return self._exit_now_signal_flag


def run_loop(func):
    """
    A decorator for TerminableProcess.run methods that simplifies the common pattern
    of using syncing_context with a while loop checking must_terminate_now.

    Instead of:

    def run(self):
        with self.syncing_context() as must_terminate_now:
            try:
                while not must_terminate_now:
                    self.log.debug("Starting loop")
                    try:
                        # actual work here
                    except Exception as err:
                        self.log.error(f"Error: {err}")
            finally:
                # cleanup code

    You can now write:

    @run_loop
    def run(self):
        # This is the main loop body
        self.log.debug("Starting loop iteration")
        # actual work here

    def setup(self):
        # Optional setup method
        # Runs once before the loop starts
        self.initialize_resources()

    def cleanup(self):
        # Optional cleanup method
        # Runs once after the loop ends
        self.release_resources()
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # Set _has_entered_run_loop immediately for proper process lifecycle
        # This is critical for start_synchronously() to work correctly
        self._has_entered_run_loop.set()

        with self.syncing_context() as must_terminate_now:
            try:
                # Run setup method if it exists
                if hasattr(self, "setup") and callable(self.setup):
                    try:
                        self.log.debug("Running setup")
                        self.setup()  # This should set setup_executed flag in test classes
                    except Exception as err:
                        self.log.error(f"Error in setup: {err}")

                # Main loop - this will call the decorated run method
                while not must_terminate_now:
                    try:
                        # Important: call the original function with self explicitly
                        # When wrapping instance methods, we need to pass self manually
                        func(self, *args, **kwargs)
                    except Exception as err:
                        self.log.error(f"Error in run loop: {err}")
                        # Continue to next iteration rather than breaking the loop
            finally:
                # Run cleanup method if it exists
                if hasattr(self, "cleanup") and callable(self.cleanup):
                    try:
                        self.log.debug("Running cleanup")
                        self.cleanup()  # This should set cleanup_executed flag in test classes
                    except Exception as err:
                        self.log.error(f"Error in cleanup: {err}")

                self.log.debug(f"{self.__class__.__name__} terminated")

    return wrapper
