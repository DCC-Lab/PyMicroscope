from abc import ABC, abstractmethod
import time

import numpy as np

from Pyro5.api import expose, Daemon, locate_ns, Proxy

from pymicroscope.utils.pyroprocess import PyroProcess
from pymicroscope.utils.terminable import run_loop


@expose
class ImageProvider(ABC, PyroProcess):
    """
    Abstract base class defining the interface for image providers.
    Subclasses must implement `capture_image`.
    """

    def __init__(self, pyro_name=None, delegate=None, properties=None, *args, **kwargs):
        super().__init__(pyro_name=pyro_name, *args, **kwargs)
        self._delegate_by_name = None

        self.properties = {"size": (480, 640), "frame_rate": 10, "channels": 3}
        if properties is not None:
            self.properties.update(properties)

        self.is_running = False
        self._start_time = None
        self._last_image = None

    @property
    def delegate_by_name(self):
        return self._delegate_by_name

    @delegate_by_name.setter
    def delegate_by_name(self, name):
        self._delegate_by_name = name

    @property
    def size(self) -> tuple:
        return self.properties["size"]

    def set_size(self, value) -> None:
        self.properties["size"] = value

    @property
    def frame_rate(self) -> float:
        return self.properties["frame_rate"]

    def set_frame_rate(self, value) -> float:
        self.properties["frame_rate"] = value

    @property
    def channels(self) -> int:
        return self.properties["channels"]

    def set_channels(self, value) -> None:
        self.properties["channels"] = value

    def capture_packaged_image(self):
        image_array = self.capture_image()
        return {
            "data": image_array.tobytes(),
            "shape": image_array.shape,
            "dtype": str(image_array.dtype),
        }

    @abstractmethod
    def capture_image(self) -> np.ndarray:
        """Capture an image and return it as a NumPy array."""
        pass

    def start_capture(self) -> None:
        self.is_running = True
        self._start_time = time.time()

    def stop_capture(self) -> None:
        self.is_running = False
        self._start_time = None

    def set_configuration(self, properties) -> None:
        self.properties.update(properties)

    def get_configuration(self) -> dict:
        return self.properties

    def run(self):
        with Daemon(host=self.get_local_ip()) as daemon:
            with self.syncing_context() as must_terminate_now:
                uri = daemon.register(self)
                self.locate_ns().register(self.pyro_name, uri)

                self.start_capture()

                while not must_terminate_now:
                    self.handle_remote_call_events()
                    self.handle_pyro_events(daemon)

                    img_tuple = self.capture_packaged_image()
                    if self.delegate_by_name is not None:
                        delegate = PyroProcess.by_name(self.delegate_by_name)

                        delegate.new_image_captured(img_tuple)

                self.stop_capture()

                self.locate_ns().remove(self.pyro_name)
