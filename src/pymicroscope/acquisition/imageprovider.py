from abc import ABC, abstractmethod
import time
import math
from typing import Protocol, Optional, Union, Type, Any, Callable, Tuple
from multiprocessing import RLock, shared_memory
import numpy as np
import base64

from Pyro5.api import expose, Daemon, locate_ns, Proxy, URI

#from pymicroscope.utils.pyroprocess import PyroProcess
#from pymicroscope.utils.terminable import run_loop
#from pymicroscope.utils.unifiedprocess import UnifiedProcess
from pymicroscope.utils.pyroprocess import PyroProcess
from pymicroscope.utils.terminable import run_loop, TerminableProcess
from pymicroscope.utils.unifiedprocess import UnifiedProcess

from PIL import Image as PILImage

class ImageProviderClient:
    """
    Protocol for receiving images from an ImageProvider.
    """

    def __init__(self, callback=None, *args, **kwargs) -> None:
        """
        Initialize the image provider client

        """
        super().__init__(*args, **kwargs)
        self.callback = callback
        self.images = []

    def new_image_captured(self, image: np.ndarray) -> None:
        """
        Called when a new image is captured.

        Args:
            image (np.ndarray): Captured image data.
        """

        if self.callback is not None:
            self.callback(image)
        else:
            self.images.append(image)
            self.images = self.images[-10:]


class ImageProvider(ABC):
    """
    Abstract base class defining the interface for image providers.

    Provides a configurable image capture process with client support.
    """

    def __init__(
        self, properties: Optional[dict[str, Any]] = None, *args: Any, **kwargs: Any
    ) -> None:
        """
        Initialize the image provider with optional client and properties.

        Args:
            client: Object implementing ImageProviderClient.
            properties: Dictionary of configuration settings.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(log_name="imageprovider", *args, **kwargs)
        self.properties: dict[str, Any] = {
            "size": (480, 640),
            "frame_rate": 30,
            "channels": 3,
        }
        if properties:
            self.properties.update(properties)

        self.is_running: bool = False
        self._start_time: Optional[float] = None
        self._last_image: Optional[float] = None
        self.last_image_package: Optional[dict[str, Any]] = None

        self._clients: list[ImageProviderClient] = []

    @property
    def clients(self) -> list[ImageProviderClient]:
        """Return the current client, if any."""
        return self._clients

    def add_client(self, obj: ImageProviderClient) -> None:
        """Set the client that will receive captured images."""
        self._clients.append(obj)

    def remove_client(self, obj: ImageProviderClient) -> None:
        """Set the client that will receive captured images."""
        self._clients.remove(obj)

    @property
    def size(self) -> Tuple[int, int]:
        """Return the current image size (height, width)."""
        return self.properties["size"]

    def set_size(self, value: Tuple[int, int]) -> None:
        """Set the image size (height, width)."""
        self.properties["size"] = value

    @property
    def frame_rate(self) -> float:
        """Return the frame rate in Hz."""
        return self.properties["frame_rate"]

    def set_frame_rate(self, value: float) -> None:
        """Set the frame rate in Hz."""
        self.properties["frame_rate"] = value

    @property
    def channels(self) -> int:
        """Return the number of image channels (e.g., 3 for RGB)."""
        return self.properties["channels"]

    def set_channels(self, value: int) -> None:
        """Set the number of image channels."""
        self.properties["channels"] = value

    def get_last_image(self) -> np.array:
        data = self.last_image_package["data"]
        dtype = self.last_image_package["dtype"]
        shape = self.last_image_package["shape"]
        return np.frombuffer(data, dtype=dtype).reshape(shape)

    @staticmethod
    def image_from_package(package: dict[str, Any]) -> Any:
        data = base64.b64decode(package["data"])
        dtype = package["dtype"]
        shape = package["shape"]
        return np.frombuffer(data, dtype=dtype).reshape(shape)

    @staticmethod
    def image_to_package(image):
        return {
            "data": base64.b64encode(image.tobytes()).decode("ascii"),
            "shape": image.shape,
            "dtype": str(image.dtype),
        }

    def get_last_packaged_image(self) -> dict[str, Any]:
        return self.last_image_package

    def capture_packaged_image(self) -> dict[str, Any]:
        """
        Capture an image and package it with metadata for transmission.

        Returns:
            A dictionary with 'data', 'shape', and 'dtype' keys.
        """
        image_array = self.capture_image()
        self.last_image_package = ImageProvider.image_to_package(image_array)

        return self.last_image_package

    @abstractmethod
    def capture_image(self) -> np.ndarray:
        """
        Capture an image and return it as a NumPy array.

        Must be implemented by subclasses.
        """
        pass

    def start_capture(self) -> None:
        """Mark the beginning of an image capture session."""
        self.is_running = True
        self._start_time = time.time()

    def stop_capture(self) -> None:
        """Stop the image capture session."""
        self.is_running = False
        self._start_time = None

    def set_configuration(self, properties: dict[str, Any]) -> None:
        """
        Update provider configuration.

        Args:
            properties: Dictionary of property updates.
        """
        self.properties.update(properties)

    def get_configuration(self) -> dict[str, Any]:
        """
        Get current provider configuration.

        Returns:
            Dictionary of configuration values.
        """
        return self.properties

    def run(self) -> None:
        """
        Main capture loop for local use (no Pyro registration).

        Subclasses may override this.
        """
        with self.syncing_context() as must_terminate_now:
            self.start_capture()

            while not must_terminate_now:
                try:
                    self.handle_remote_call_events()
                    self.handle_pyro_events(daemon)

                    img_tuple = self.capture_packaged_image()
                    for client in self.clients:
                        client.new_image_captured(img_tuple)
                except Exception as err:
                    self.log.error(f"Error in ImageProvider run loop : {err}")
            self.stop_capture()


@expose
class RemoteImageProviderClient(PyroProcess, ImageProviderClient):
    """
    Protocol for receiving images from an ImageProvider.
    """

    def __init__(self, callback=None, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the image provider client

        """
        super().__init__(*args, **kwargs)
        self.callback = callback
        self.images = []

    def new_image_captured(self, image: np.ndarray) -> None:
        """
        Called when a new image is captured.

        Args:
            image (np.ndarray): Captured image data.
        """

        if self.callback is not None:
            self.callback(image)
        else:
            self.images.append(image)
            self.images = self.images[-10:]


@expose
class RemoteImageProvider(ImageProvider, PyroProcess):
    """
    Image provider that exposes its interface over Pyro5.
    """

    def __init__(self, pyro_name: Optional[str], *args: Any, **kwargs: Any) -> None:
        """
        Initialize and register a remote image provider.

        Args:
            pyro_name: Name used to register with Pyro name server.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(pyro_name=pyro_name, *args, **kwargs)
        self.lock = RLock()

    def client_to_proxy(self, obj_or_name) -> Optional[ImageProviderClient]:
        """
        Dynamically resolve client from name or URI if needed.

        Returns:
            The client object or proxy, if available.
        """
        with self.lock:
            if isinstance(obj_or_name, URI):
                return PyroProcess.by_uri(obj_or_name)
            elif isinstance(obj_or_name, str):
                return PyroProcess.by_name(obj_or_name)

            return obj_or_name

    def add_client(self, obj_or_name: Union[ImageProviderClient, str, URI]) -> None:
        """
        Add client as an object, Pyro name, or URI.  If it is a name or a URI
        we defer until the runloop to actually instantiate the object (i.e. it needs
        to be instantiated on the right thread)

        Args:
            obj_or_name: Can be a client object, a Pyro name, or a Pyro URI.
        """
        with self.lock:
            super().add_client(obj_or_name)

    def set_frame_rate(self, value: float) -> None:
        """
        Set the frame rate of the image provider.

        Args:
            value: Frame rate in Hz.
        """
        super().set_frame_rate(value)

    def run(self) -> None:
        """
        Main run loop with Pyro daemon registration and event handling.
        """
        with Daemon(host=self.get_local_ip()) as daemon:
            with self.syncing_context() as must_terminate_now:
                uri = daemon.register(self)
                ns = self.locate_ns()
                if ns is not None:
                    ns.register(self.pyro_name, uri)

                self.start_capture()

                while not must_terminate_now:
                    self.handle_remote_call_events()
                    self.handle_pyro_events(daemon)

                    img_tuple = self.capture_packaged_image()
                    with self.lock:
                        for client in self.clients:
                            proxy = self.client_to_proxy(client)
                            proxy.new_image_captured(img_tuple)

                self.stop_capture()

                ns = self.locate_ns()
                if ns is not None:
                    ns.remove(self.pyro_name)

    def get_last_packaged_image(self) -> dict[str, Any]:
        return super().get_last_packaged_image()


class DebugRemoteImageProvider(RemoteImageProvider):
    """
    An image provider that generates synthetic 8-bit images for testing.
    """

    def capture_image(self) -> np.ndarray:
        """
        Generate an 8-bit random image of shape (size[0], size[1], channels),
        simulating frame rate delay between frames.

        Returns:
            np.ndarray: Random image as a uint8 array.

        Example:
            >>> img = provider.capture_image()
            >>> img.shape
            (256, 256, 3)
        """

        img = self.generate_random_noise(self.size[0], self.size[1], self.channels)

        frame_duration = 1 / self.frame_rate

        while (
            self._last_image is not None
            and time.time() < self._last_image + frame_duration
        ):
            time.sleep(0.001)

        self._last_image = time.time()
        self.log.debug("Image captured at %f", time.time() - self._start_time)
        return img

    @staticmethod
    def generate_random_noise(height, width, channels):
        return np.random.randint(0, 256, (height, width, channels), dtype=np.uint8)

    @staticmethod
    def generate_moving_bars(height=240, width=320, step=1):
        """Return a larger RGB pattern that can be scrolled horizontally."""
        bar_colors = np.array(
            [
                [255, 0, 0],  # Red
                [0, 255, 0],  # Green
                [0, 0, 255],  # Blue
                [255, 255, 0],  # Yellow
                [0, 255, 255],  # Cyan
                [255, 0, 255],  # Magenta
                [255, 255, 255],  # White
                [0, 0, 0],  # Black
            ],
            dtype=np.uint8,
        )

        bar_width = width // 4
        pattern_width = width * 2
        pattern = np.zeros((height, pattern_width, 3), dtype=np.uint8)

        for i in range(pattern_width // bar_width):
            color = bar_colors[i % len(bar_colors)]
            fractional, integer = math.modf(time.time())
            if integer % 2 == 0:
                i += fractional
            else:
                i -= fractional - 1
            pattern[:, int(i * bar_width) : int((i + 1) * bar_width), :] = color

        return pattern

    @staticmethod
    def generate_color_bars(height, width):
        # Define the 7 SMPTE color bars in RGB
        colors = [
            [192, 192, 192],  # White
            [192, 192, 0],  # Yellow
            [0, 192, 192],  # Cyan
            [0, 192, 0],  # Green
            [192, 0, 192],  # Magenta
            [192, 0, 0],  # Red
            [0, 0, 192],  # Blue
        ]
        colors = np.array(colors, dtype=np.uint8)

        # Compute width of each bar
        bar_width = width // len(colors)

        # Initialize image
        img = np.zeros((height, width, 3), dtype=np.uint8)

        # Fill bars
        for i, color in enumerate(colors):
            img[:, i * bar_width : (i + 1) * bar_width, :] = color

        return img


class DebugImageProvider(ImageProvider, TerminableProcess):
    """
    An image provider that generates synthetic 8-bit images for testing.
    """
    def __init__(self, queue, *args, **kwargs):
        super().__init__(name="DebugImageProvider", *args, **kwargs)
        self.image_queue = queue
        
    def run(self) -> None:
        """
        Main capture loop for local use (no Pyro registration).

        Subclasses may override this.
        """
        with self.syncing_context() as must_terminate_now:
            self.start_capture()

            while not must_terminate_now:
                try:
                    img_array = self.capture_image()
                    self.image_queue.put(img_array)
                except Exception as err:
                    self.log.error(f"Error in ImageProvider run loop : {err}")

            self.stop_capture()

    def capture_image(self) -> np.ndarray:
        """
        Generate an 8-bit random image of shape (size[0], size[1], channels),
        simulating frame rate delay between frames.

        Returns:
            np.ndarray: Random image as a uint8 array.

        Example:
            >>> img = provider.capture_image()
            >>> img.shape
            (256, 256, 3)
        """
        img = self.generate_color_bars(self.size[0], self.size[1])

        frame_duration = 1 / self.frame_rate

        while (
            self._last_image is not None
            and time.time() < self._last_image + frame_duration
        ):
            time.sleep(0.001)

        self._last_image = time.time()
        self.log.debug("Image captured at %f", time.time() - self._start_time)
        return img

    @staticmethod
    def generate_random_noise(height, width, channels):
        return np.random.randint(0, 256, (height, width, channels), dtype=np.uint8)

    @staticmethod
    def generate_moving_bars(height=240, width=320, step=1):
        """Return a larger RGB pattern that can be scrolled horizontally."""
        bar_colors = np.array(
            [
                [255, 0, 0],  # Red
                [0, 255, 0],  # Green
                [0, 0, 255],  # Blue
                [255, 255, 0],  # Yellow
                [0, 255, 255],  # Cyan
                [255, 0, 255],  # Magenta
                [255, 255, 255],  # White
                [0, 0, 0],  # Black
            ],
            dtype=np.uint8,
        )

        bar_width = width // 4
        pattern_width = width * 2
        pattern = np.zeros((height, pattern_width, 3), dtype=np.uint8)

        for i in range(pattern_width // bar_width):
            color = bar_colors[i % len(bar_colors)]
            fractional, integer = math.modf(time.time())
            if integer % 2 == 0:
                i += fractional
            else:
                i -= fractional - 1
            pattern[:, int(i * bar_width) : int((i + 1) * bar_width), :] = color

        return pattern

    @staticmethod
    def generate_color_bars(height, width):
        # Define the 7 SMPTE color bars in RGB
        colors = [
            [192, 192, 192],  # White
            [192, 192, 0],  # Yellow
            [0, 192, 192],  # Cyan
            [0, 192, 0],  # Green
            [192, 0, 192],  # Magenta
            [192, 0, 0],  # Red
            [0, 0, 192],  # Blue
        ]
        colors = np.array(colors, dtype=np.uint8)

        # Compute width of each bar
        bar_width = width // len(colors)

        # Initialize image
        img = np.zeros((height, width, 3), dtype=np.uint8)

        # Fill bars
        fractional, integer = math.modf(time.time())
        for i, color in enumerate(colors):
            img[:, i * bar_width : (i + 1) * bar_width, :] = color*fractional

        return img
        
        
    
if __name__ == "__main__":
    import logging

    # provider = DebugImageProvider(
    #     log_level=logging.DEBUG, pyro_name="ca.dccmlab.imageprovider.debug"
    # )
    provider = DebugImageProvider(
        log_level=logging.DEBUG
    )
    provider.start_synchronously()
    provider.join()
