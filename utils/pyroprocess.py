import sys
import subprocess
import time
import socket
import select

from Pyro5.api import expose, Daemon, locate_ns, Proxy
from Pyro5.errors import NamingError
import psutil

from src.utils import UnifiedProcess


class PyroProcess(UnifiedProcess):
    """
    Class for Python Remote Object (Pyro).

    Use distant objects as if you had the instance with you.

    Pyro objects advertise themselves on a nameserver, you
    can then get a proxy of that object and call methods on it.

    To easily access objects across processes and machines, a nameserver
    is needed. All interacting Pyro objects must share the same nameserver.

    """

    nameserver_proc = None
    nameserver_host = "0.0.0.0"
    nameserver_port = 9090

    def __init__(self, pyro_name, *args, **kwargs):
        """
        Creates a Pyro object with pyro_name, which will
        be registered when the process starts
        """
        super().__init__(*args, **kwargs)
        self.pyro_name = pyro_name

    @expose
    def echo(self, value):
        """
        A simple test method that returns the value it was sent
        """
        return value

    def handle_pyro_events(self, daemon):
        s, _, _ = select.select(daemon.sockets, [], [], 0.001)  # 1ms timeout
        if s:
            daemon.events(s)

    def run(self) -> None:
        """
        The run method for this Pyro object still supports CallableProcess
        """
        with Daemon(host=self.get_local_ip()) as daemon:
            with self.syncing_context() as must_terminate_now:
                uri = daemon.register(self)

                self.locate_ns().register(self.pyro_name, uri)

                while not must_terminate_now:
                    self.handle_pyro_events(daemon)
                    self.handle_remote_call_events()

                self.locate_ns().remove(self.pyro_name)

    @staticmethod
    def available_objects():
        """
        Get the name server instance

        """
        return PyroProcess.locate_ns().list()

    @staticmethod
    def locate_ns(timeout=5):
        """
        Get the name server instance, we try a few times in case
        the nameserver is busy, which appears to happen

        """
        start_time = time.time()

        while time.time() < start_time + timeout:
            try:
                return locate_ns()
            except NamingError as err:
                time.sleep(0.1)

        return None

    @classmethod
    def start_nameserver(cls, host="0.0.0.0", port=9090):
        """
        Start a new subprocess with the name server on the present machine

        """
        cls.stop_nameserver()

        cls.nameserver_proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "Pyro5.nameserver",
                f"--host={host}",
                f"--port={port}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    @classmethod
    def stop_nameserver(cls):
        """
        Stop the nameserver subprocess

        """
        if cls.nameserver_proc is not None:
            cls.nameserver_proc.terminate()
            cls.nameserver_proc.wait()
            cls.nameserver_proc = None

    @staticmethod
    def get_local_ip():
        # This doesn't actually connect, just gets the routing info
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))  # Google's public DNS, used just for routing
            ip = s.getsockname()[0]
        finally:
            s.close()
        return ip

    @staticmethod
    def get_all_ip_addresses(include_v6=False):
        addresses = set()
        for interface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET:  # IPv4
                    addresses.add(addr.address)
                elif addr.family == socket.AF_INET6 and include_v6:
                    addresses.add(
                        addr.address.split("%")[0]
                    )  # remove scope ID if present
        return addresses

    @classmethod
    def by_name(cls, name):
        ns = PyroProcess.locate_ns()
        try:
            uri = ns.lookup(name)
            return Proxy(uri)
        except:
            return None


if __name__ == "__main__":
    PyroProcess("test-object-main").start()
    time.sleep(100)
