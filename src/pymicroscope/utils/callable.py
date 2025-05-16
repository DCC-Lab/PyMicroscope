"""
Provides `CallableProcess`, a `multiprocessing.Process` subclass that allows
the parent process to invoke methods on the subprocess using a
message-passing protocol built on `Queue` and `dataclass`ed `Command`/`Reply`
objects.

This framework is particularly useful when building long-running service-like
processes (e.g., hardware control loops) that expose internal methods for
remote control. By sending structured `Command` objects across a command
queue and retrieving `Reply` objects from a private response queue, it
guarantees synchronous, thread-safe, and process-safe communication.

Key Concepts:
-------------
- Method invocations are represented as `Command` objects, placed on a shared
  command queue.
- Each command includes a **private reply queue**, created using
  `multiprocessing.Manager().Queue()`, which can safely be passed between
  processes.
- The subprocess reads and executes commands using `handle_remote_call_events
  ()` inside its `run()` method.
- Responses, including exceptions, are returned as `Reply` objects through the
  private reply queue.
- `RemoteException` is used to transport remote failures back to the caller in
  a structured way.

Why Use a Private Queue?
------------------------
In multiprocess environments, especially when multiple remote calls are made
in parallel, using a shared reply queue introduces a risk of
desynchronization. A fast reply may be accidentally consumed by the wrong
caller, especially if replies arrive out of order. To avoid this, each
`Command` carries its own dedicated `Manager().Queue()` for the reply,
ensuring:
  - Replies are isolated to the originating caller
  - No need for complex locking, tagging, or requeueing
  - Fully safe concurrent access from multiple processes

Example Usage:
--------------
    class Worker(CallableProcess): def run(self): while True:
    self.handle_remote_call_events()

    worker = Worker() worker.start() result = worker.call_method
    ("self", "some_remote_method", args=(1, 2))

    # or use get_property() to fetch a dynamic attribute

Notes:
------
- The subprocess must call `handle_remote_call_events()` frequently in its `run
  ()` loop.
- handle_remote_call_events() will synchronously block until the call to any
  function has completed.
- Calls made before the subprocess is ready or not calling
  `handle_remote_call_events()` in the run() method of the child class will raise a
  `RuntimeError`.
- This system supports method calls and property accesses alike, and returns
  remote exceptions transparently.

"""

from multiprocessing import Process, Value, Queue, Manager, Event, current_process
from threading import current_thread, main_thread
import time
from dataclasses import dataclass
from queue import Empty
from typing import Any, Optional, Callable, Union, Tuple

from pymicroscope.utils.terminable import TerminableProcess


@dataclass
class Reply:
    """
    Replies passed back onto the queue from remote calls
    """

    result: Optional[Any] = None
    exception: Optional[Exception] = None

    def result_or_raise_if_exception(self):
        """
        Convenience function to return the result or raise the
        exception that was returned.
        """
        if self.exception:
            raise self.exception
        return self.result


@dataclass
class Command:
    """
    Commands passed onto the queue for remote calls
    """

    target_name: str  # e.g. "self" or "camera"
    method_name: str  # name of method or property
    reply_queue: Any  # Manager().Queue() for response
    method_args: Optional[tuple] = None  # positional args
    method_kwargs: Optional[dict] = None  # keyword args
    ignore_result: bool = False
    is_discardable: bool = False


class CallableProcess(TerminableProcess):
    """
    A `multiprocessing.Process` subclass that allows calling methods
    inside the process from the parent process using a queue-based protocol.

    This puts together the machinery to call a method or get a property from
    the process where run() is running. This is useful to share variables but
    mostly to call specific methods on the object in the run process. An
    example is a Process that runs a camera can make available set_control
    that can be called to change the settings of the object camera that is
    active in the process.

    Use `call_method_remotely()` to send function calls into the running process.
    More aqccurately, use `call_method` and let the class determine if it should
    get it remote or not.

    Example:
        class Worker(CallableProcess):
            def run(self):
                while True:
                    self.handle_remote_call_events()

        p = Worker()
        p.start()
        p.call_method("self", "some_method")


    """

    _manager = None

    class RemoteException(Exception):
        """
        Class returned when an exception occurs remotely. The exception will be raised
        at the caller, caught locally and returned through the queue, then raised,
        as if it had been raised locally.
        """

        def __init__(self, exception):
            self.remote_exception = exception

    def __init__(
        self,
        event_timeout=0.5,
        call_timeout=0.5,
        loop_timeout=0.0001,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        1.  The event_timeout is how long we are willing to wait for certain events to occur:
            1. how long before the run() method checks the command queue?
            2. how long before the queue has been emptied after being requested to do so?
            The default is probably always reasonable.

        2.  The call_timeout is the amount of time we are willing to wait for the return value of a
            remote call.  You may want to increase this timeout of your commands take a long time.

        3.  The loop_timeout is the amount of time we are willing to wait when
            extracting commands from the queue in the run() loop.  loop_timeout =
            None will not wait for elements (fast handle_remote_call_events() if empty)
            and loop_timeout = 0.5 is a good number of the loop is only executing
            commands and not doing anything else.

            The default assumes the process will do other things and does not want to wait
            for commands to appear.
        """
        super().__init__(*args, **kwargs)

        self.call_timeout = call_timeout
        self.loop_timeout = loop_timeout
        self.event_timeout = event_timeout

        self.smallest_check_delay = 0.001
        self.last_queue_check = None

        self.commands_in: Any = Queue()

        # must be available in both subprocesses
        self._has_checked_commands_queue = Event()
        self.__create_manager_on_main_thread_only()

    def __create_manager_on_main_thread_only(self):
        """
        Very important: to pass a Queue() onto another queue we need a Managed
        Queue (see call_method_remotely). The manager is slow to instanciate
        and must survive and nver go out of scope before the queue is
        discarded. The solution is to have a static _manager but it cannot
        be a instance property. This important function is critical.
        """
        if (
            CallableProcess._manager is None
            and current_thread() is main_thread()
            and current_process().name == "MainProcess"
        ):
            CallableProcess._manager = Manager()

    @property
    def has_checked_commands(self) -> bool:
        """
        Convenience method for the main process for testing

        This is often forgotten and leads to errors.
        """
        return self._has_checked_commands_queue.is_set()

    def _resolve(
        self, target_name: str, name: str
    ) -> Tuple[Any, Union[Callable[..., Any], Any]]:
        """Resolves the target method or property by name."""
        if target_name is None or target_name == "self":
            actual_target = self
        else:
            actual_target = getattr(self, target_name)

        prop_or_method = getattr(actual_target, name)

        return actual_target, prop_or_method

    def get_property(self, property_name: str, timeout: float = None) -> Any:
        """Convenience method to retrieve a property from the process."""
        return self.call_method(
            target_name="self", method_name=property_name, timeout=timeout
        )

    def call_method(
        self,
        target_name,
        method_name,
        method_args=None,
        method_kwargs=None,
        ignore_result=False,
        is_discardable=False,
        timeout: float = None,
    ):
        """Calls a method either remotely or locally based on process state."""

        if self.is_alive():
            reply = self.call_method_remotely(
                target_name,
                method_name,
                method_args=method_args,
                method_kwargs=method_kwargs,
                ignore_result=ignore_result,
                is_discardable=is_discardable,
                timeout=timeout,
            )
        else:
            reply = self.call_method_locally(
                target_name,
                method_name,
                method_args=method_args,
                method_kwargs=method_kwargs,
            )

        return reply.result_or_raise_if_exception()

    def call_method_remotely(
        self,
        target_name,
        method_name,
        method_args=None,
        method_kwargs=None,
        ignore_result=False,
        is_discardable=False,
        timeout: float = None,
    ) -> Reply:
        """
        Sends a method call to be executed within the subprocess on a command
        queue, and receives the reply on a private queue to avoid
        synchronisation issues(i.e. one command taking too long and getting
        the reply of another command instance).

        This method will encode a method call to be executed in the separate
        process that has been spawned by Process.start(). It is important to
        note that this is necessary: when calling Process.start(), a copy *at
        that moment in time* is performed and a separate process is created.
        The internal variables will not be synchronized anymore unless
        specific inter-process variables are used.

        If the process is not started yet, the local call should be used but
        it currently raises an exception.

        The process is responsible for calling handle_remote_call_events() in its
        run() method repeatedly so that calls are processed and executed.

        To execute self.set_some_parameters(value=1) you would call:

        call_method_remotely("self", "set_some_parameters", args=None, kwargs=
        {"value":1})

        To execute self.camera.set_controls({"AnalogueGain":1}) you would
        call:

        call_method_remotely("camera", "set_controls", args=(
        {"AnalogueGain":1}, ) kwargs=None)


        """

        if self.is_quitting:
            raise RuntimeError(
                "The process is shutting down and does not accept new commands"
            )

        if not self._has_checked_commands_queue.wait(timeout=self.event_timeout):
            raise TimeoutError(
                "The run() method must call self.handle_remote_call_events() periodically"
            )

        if self.is_alive():
            try:
                reply_queue = None
                if not ignore_result:
                    """
                    We receive the result on a private queue that we pass as
                    an argument.

                    DANGER: To pass the Queue() as an element onto another
                    Queue to another process, we must obtain it from Manager()
                    But creating a Manager() is very slow (0.15 s) to create.
                    Therefore we create it only once, but it must be created
                    on the main thread and cannot be a property of an
                    instance.  This is tricky and well documented on the web.

                    The solution is the method
                     __create_manager_on_main_thread_only that creates and
                    assigns a class property _manager a Manager() properly
                    and safely so it can be reused.

                    Since call_remotely should always (?) be called from a
                    main thread, CallableProcess._manager should always be
                    set, but I am checking for None just in case, which would
                    mean someone is trying to use call_method_remotely from a
                    subprocess, which I think will fail. I will warn.

                    Notice that this would still be ok if the caller decides
                    to ignore the result because in this case, we don't
                    create a queue.

                    A managed Queue() cannot and does not need to be close()
                    and join_thread()
                    """
                    if CallableProcess._manager is not None:
                        reply_queue = CallableProcess._manager.Queue()
                    else:
                        raise RuntimeError(
                            "call_method_remotely must be called from a main thread only or ignore_result=True"
                        )

                command = Command(
                    target_name=target_name,
                    method_name=method_name,
                    method_args=method_args,
                    method_kwargs=method_kwargs,
                    reply_queue=reply_queue,
                    ignore_result=ignore_result,
                    is_discardable=is_discardable,
                )

                self.commands_in.put(command)

                if ignore_result:
                    return Reply(None, None)

                return reply_queue.get(timeout=self.call_timeout)
            except (TimeoutError, Empty) as exc:
                """
                If reply_queue.get(timeout=timeout) times out, and Manager
                ().Queue() will get garbage collected because we are exiting
                the process and the remote process will crash trying to put
                the result onto the disappeared reply_queue. We would need a
                singletong Manager() that survives the method and normally
                this would be as a property of this object.  However, we
                cannot because a Process cannot have a Manager() because it
                is not picklable.

                1. BEST SOLUTION (implemented): A Manager(), class property _manager
                2. HACK: In handle_remote_call_events(), check for error (which I do anyway)

                """
                raise TimeoutError(
                    "The remote command did not reply within the call_timeout limit"
                ) from exc
        else:
            raise RuntimeError(
                "Process has not started yet: call the procedure directly"
            )

    def call_method_locally(
        self,
        target_name: str,
        method_name: str,
        method_args: Optional[tuple] = None,
        method_kwargs: Optional[dict[str, Any]] = None,
    ) -> Reply:
        """
        This method will take string arguments and decode them into actual calls that are
        then executed, can be a method/function or a property
        """

        result: Any = None
        try:
            _, method = self._resolve(target_name, method_name)

            if callable(method):  # Is a function, already bound to target
                if method_args is None and method_kwargs is None:
                    result = method()
                elif method_kwargs is None:
                    result = method(*method_args)
                elif method_args is None:
                    result = method(**method_kwargs)
                else:
                    result = method(*method_args, **method_kwargs)
            else:
                result = method  # Is a property
        except Exception as err:  # pylint: disable=broad-exception-caught
            return Reply(exception=CallableProcess.RemoteException(err))

        return Reply(result=result)

    def handle_remote_call_events(self, timeout=None) -> None:
        self.handle_remote_call_events()

    def handle_remote_call_events(self, timeout=None) -> None:
        """
        In your run(), you must call this non-blocking method frequently, If a
        command appears on the queue, it will be called within the new
        process (i.e. within the run()). It is possible to ignore the return value and not put the
        reply on the queue.  This way, the other process calling will be
        allowed to return immediately.

        We can put the target, method name, args and kwargs on the command
        queue to call the method within the present process.

        Commands have two relevant properties: ignore_result and is_discardable

        If a command is discardable AND it ignores the result, then duplicates
        will be removed from the queue. The reasoning is that these commands
        must be processed quickly and accumulating them on the queue is a sign
        that the processing is too slow and the queue is overflowing.

        However, if a command is_discardable, it must also ignore_result. It
        is an error to be discardable and not ignore the result (because the
        caller will be waiting for something).
        """

        self._has_checked_commands_queue.set()

        if not self.is_quitting and self.last_queue_check is not None:
            if time.time() - self.last_queue_check < self.smallest_check_delay:
                return

        self.last_queue_check = time.time()

        last_command = None

        try:
            command = None
            while True:
                if not self.is_quitting and self.loop_timeout is None:
                    command = self.commands_in.get_nowait()
                else:
                    command = self.commands_in.get(timeout=self.loop_timeout)

                if (
                    last_command is not None
                    and (command.method_name == last_command.method_name)
                    and command.is_discardable
                    and last_command.is_discardable
                    and command.ignore_result
                    and last_command.ignore_result
                ):
                    continue  # drop and loop

                last_command = command

                if self.is_quitting:
                    reply = Reply(
                        result=None, exception=RuntimeError("Process is quitting")
                    )
                else:
                    reply = self.call_method_locally(
                        target_name=command.target_name,
                        method_name=command.method_name,
                        method_args=command.method_args,
                        method_kwargs=command.method_kwargs,
                    )

                if not command.ignore_result:
                    # DANGER: If the reply_queue has disappeared, this will crash
                    # Because it was created in another process, I am being careful.
                    try:
                        command.reply_queue.put(reply)
                    except Exception as err:
                        pass

        except Empty:
            pass
        except Exception as err:
            print(err)

    def wait_for_queued_commands(self):
        """
        Give a chance to queued commands to complete before we terminate. This
        is called outside of the loop in the run() method before leaving the
        method. See the default run() implementation of CallableProcess.

        We prevent new commands from entering the queue and wait
        for the old ones to complete, but within the timeout provided.

        The timeout is not for the method, but for the queue.get().

        """

        self.handle_remote_call_events(timeout=self.event_timeout)

    def run(self):
        """
        A default run() implementation: if the class does not need to do anything
        except respond to call_method_remotely, then this run() implementation
        is sufficient. It is also efficient since it blocks for handle_remote_call_events

        Installs signal handlers, checks for and executes queued commands, and
        exits cleanly on termination signal.
        """

        with self.syncing_context(
            on_run_loop=self.handle_remote_call_events()
        ) as must_terminate_now:
            try:
                while not must_terminate_now:
                    time.sleep(0.001)

            finally:
                self.wait_for_queued_commands()
