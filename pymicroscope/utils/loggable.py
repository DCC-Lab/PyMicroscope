# pylint: disable=too-many-arguments,too-many-positional-arguments
"""
Multiprocessing-safe logging and process control utilities for structured Python applications.

This module provides tools to enhance logging and subprocess management in distributed
or threaded systems. It includes support for:

- Consistent log formatting with filtering of HTTP noise.
- `Loggable` base class for adding contextual logging to any object.
- `LoggableProcess`, which combines all above for easy-to-manage, debuggable processes.
- Logging filters (`PostGetFilter`, `ViscosityFilter`) to suppress noisy GET/POST logs.


Example:
    from loggable import LoggableProcess

    class MyWorker(LoggableProcess):
        def run(self):
            self.install_signal_handlers()
            while not self.must_terminate_now:
                self.check_command_queue()
                self.log.info("Working...")

        def ping(self):
            return "pong"

    p = MyWorker(log_name="my.worker")
    p.start()
    print(p.call_method("self", "ping"))


"""

import logging
from logging import Logger
import gc
import sys
import signal
import pprint
from multiprocessing import Process
from queue import Empty
from threading import current_thread, main_thread
from typing import Any, Optional


DEFAULT_LOG_LEVEL = logging.INFO  # The default log levels if nothing is provided

"""
The log levels in decreasing value of verbosity.
"""
ORDERED_LEVELS = [
    logging.DEBUG,
    logging.INFO,
    logging.WARNING,
    logging.ERROR,
    logging.CRITICAL,
]


def configured_log(
    log_name: Optional[str] = None, log_level: Optional[int] = None
) -> logging.Logger:
    """
    Configures and returns a logger with a specific name and level.

    Filters out POST and GET requests using PostGetFilter, and sets up
    a consistent formatter. Useful for structured logs across processes.

    Example:
        log = configured_log("myapp", logging.DEBUG)
        log.info("Hello from logger")

        I got all of this from the web. Technical boilerplate.
    One ecomplexity: the log_level of a log is per-process
    the handlers are tricky.
    """
    MY_LEVEL = 15
    logging.addLevelName(MY_LEVEL, "CONTEXT")

    def context(self, message, *args, **kwargs):
        if self.isEnabledFor(MY_LEVEL):
            self._log(MY_LEVEL, message, args, **kwargs)

    logging.Logger.context = context

    if log_level is None:
        log_level = DEFAULT_LOG_LEVEL

    Loggable.silence_werkzeug()

    log = logging.getLogger(log_name)

    if log_level is None:
        log_level = DEFAULT_LOG_LEVEL

    log.setLevel(log_level)
    log.propagate = False

    # Clear existing handlers
    while log.handlers:
        log.removeHandler(log.handlers[0])

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s [PID:%(process)d] %(levelname)s - %(message)s",
        "%H:%M:%S",
    )
    handler.setFormatter(formatter)

    filter_ = PostGetFilter()
    log.addFilter(filter_)
    handler.addFilter(filter_)  # <- this is what was missing

    log.addHandler(handler)

    return log


class Loggable:
    """
    Base class to add logging capabilities to any object.

    Loggable allows the creation and handling of a named log using the OS
    facility. We give a name ("probe" or "probe.io", etc...) and a log_level

        logging.DEBUG,   # Everyting
        logging.INFO,
        logging.WARNING,
        logging.ERROR,
        logging.CRITICAL # Only critical errors

    Loggable is general and can be assigned as a parent for any class: we want
    to be useful to process, threads, and any other class. It is essentially
    a protocol.

    Can be used as a base class to support structured logging with consistent formatting.

    Example:
        class MyWorker(Loggable):
            def __init__(self):
                super().__init__(log_name="my.worker")
                self.log.info("Worker started")


    Many functions are static or externally defined to be easily globally accessible.
    """

    def __init__(
        self,
        log_name: Optional[str] = None,
        log_level: Optional[int] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.log_name = log_name
        if log_level is None:
            log_level = (
                DEFAULT_LOG_LEVEL  # If you don't set a default, you get *my* default.
            )
        self.log_level = log_level

    @classmethod
    def show_loggers(cls) -> None:
        """Prints all active loggers and their handler count."""
        loggers = [obj for obj in gc.get_objects() if isinstance(obj, Logger)]
        for logger in sorted(loggers, key=lambda l: l.name):
            level = logging.getLevelName(logger.level)
            print(f"{logger.name} | Level: {level} | Handlers: {len(logger.handlers)}")

    @classmethod
    def silence_werkzeug(cls) -> None:
        """
        Disables werkzeug (Flask) logging noise using PostGetFilter.

        "werkzeug" is the log name of the urllib3, which will fill the screen
         with log calls if we don't silence it We silence it.
        """
        werkzeug_logger = logging.getLogger("werkzeug")
        filter_ = PostGetFilter()
        werkzeug_logger.addFilter(filter_)
        for h in werkzeug_logger.handlers:
            h.addFilter(filter_)

    @property
    def log(self) -> logging.Logger:
        """
        Returns the configured logger for this object at the default log_level
        """
        return self.configured_log()

    def configured_log(self, log_level: Optional[int] = None) -> logging.Logger:
        """
        Returns the logger associated with this object.

        Args:
            log_level (int): Optional logging level override.

        Returns:
            logging.Logger
        """
        if log_level is None:
            log_level = self.log_level
        return configured_log(self.log_name, log_level=log_level)

    def pretty_format(self, value: Any) -> str:
        """
        Returns a nicely formatted string (often used with dictionary)
        """
        return pprint.pformat(value, indent=4)


class LoggableProcess(Loggable, Process):
    """
    Add logging for subprocesses.

    Must use Loggable as the first base class to ensure proper MRO.

    ** Important** Loggable must be first in the parent list! This affects
       Method Resolution Order and fails to call all __init__'s.

    Loggable is general and can be assigned as a parent for any class: we want
    to be useful to process, threads, and any other class.

    It is not an error to have the same base class (Process) in two of the
    parents: (CallableProcess and TerminableProcess) the Method Resolution
    Order (MRO) of super().__init__(*args, **kwargs) will call the class
    __init__ only once.

    Example:
        class MyProc(LoggableProcess):
            def run(self):
                while True:
                    self.log.info("Some information")

    """

    def __init__(
        self, log_name: Optional[str] = None, *args: Any, **kwargs: Any
    ) -> None:
        super().__init__(log_name=log_name, *args, **kwargs)

    def install_signal_handlers(self) -> None:
        """
        Install a handler for USR1, which allows to change the log level
        dynamiicaly from the terminal
        """

        def next_log_level(signum, frame):  # pylint: disable=unused-argument
            """
            Returns the next higher logging level.
            If already at the highest level, returns the same level.

            called from the terminal with `kill -USR1 pid`
            """
            try:
                current = ORDERED_LEVELS.index(self.log_level)
                self.log_level = ORDERED_LEVELS[(current + 1) % len(ORDERED_LEVELS)]
                print(f"Log level of {self.name} increased to : {self.log_level}")
            except ValueError:
                pass

        if current_thread() is not main_thread():
            self.log.warning(
                "Signal handlers must be registered in the main thread. "
                "SIGUSR1 will not be handled."
            )
        else:
            # raises a ValueError if called not on main thread
            _ = signal.signal(signal.SIGUSR1, next_log_level)

    def deinstall_signal_handlers(self):
        pass  # SIGUSR1 is not handled by default


class PostGetFilter(logging.Filter):  # pylint: disable=too-few-public-methods
    """Filter that suppresses log messages containing 'POST' or 'GET'."""

    def filter(self, record: logging.LogRecord) -> bool:
        if "POST" in str(record.getMessage()):
            return False
        if "GET" in str(record.getMessage()):
            return False

        return True


class ViscosityFilter(PostGetFilter):  # pylint: disable=too-few-public-methods
    """Alias for PostGetFilter, specific to Viscosity use case."""
