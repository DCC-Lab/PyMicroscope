import sys
from multiprocessing import (
    Process,
    get_start_method,
    set_start_method,
    get_all_start_methods,
)

import warnings
from multiprocessing.queues import Queue as MPQueue
from queue import Empty
#from pymicroscope.utils import LoggableProcess, TerminableProcess, CallableProcess
from pymicroscope.utils import LoggableProcess, TerminableProcess, CallableProcess


class UnifiedProcess(CallableProcess):
    """
    The mother of all Process with all capabilities from
    LoggableProcess, CallableProcess, TerminableProcess
    """

    def install_signal_handlers(self) -> None:
        """
        install_signal_handlers exists in two subclasses,
        but not in Process, therefore the present class
        cannot call super().install_signal_handlers()
        and hope that everyting will be called properly.
        (It is a multiple inheritance problem and related to MRO)
        It doesn't matter, it's simple to do it oursleves.
        """
        TerminableProcess.install_signal_handlers(self)
        LoggableProcess.install_signal_handlers(self)

    def deinstall_signal_handlers(self) -> None:
        """
        Return handlers to original state
        """
        LoggableProcess.deinstall_signal_handlers(self)
        TerminableProcess.deinstall_signal_handlers(self)

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

        if isinstance(queue, MPQueue):
            queue.close()
            queue.join_thread()


def safe_set_start_method(preferred="spawn", force=False) -> str:
    """
    Sets a safe multiprocessing start method, favoring cross-platform consistency.

    Parameters:
        preferred (str): The preferred start method ("spawn", "fork", "forkserver").
                         Default is "spawn" for safety and compatibility.
        force (bool): Whether to force reinitialization (only allowed before any Process starts).

    Returns:
        str: The method that was actually set or already in use.

    Raises:
        ValueError: If the preferred method is unsupported.
    """
    valid_methods = get_all_start_methods()
    if preferred not in valid_methods:
        raise ValueError(f"'{preferred}' not in supported methods: {valid_methods}")

    # Detect platform and warn if default would differ
    platform_default = "fork" if sys.platform.startswith("linux") else "spawn"

    try:
        current = get_start_method(allow_none=True)
        if current is None or force:
            set_start_method(preferred, force=force)
            current = preferred
        elif current != preferred:
            warnings.warn(
                f"Multiprocessing start method is '{current}', but '{preferred}' was requested. "
                f"On {sys.platform}, the default is '{platform_default}'. "
                f"To override, use force=True at program start."
            )
        return current
    except RuntimeError as _:
        # Method already set and force=False
        return get_start_method()
