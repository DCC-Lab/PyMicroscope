from abc import ABC, abstractmethod
import time
from typing import Protocol, Optional, Union, Type, Any, Callable, Tuple

import numpy as np

from Pyro5.api import expose, Daemon, locate_ns, Proxy, URI

from pymicroscope.utils.pyroprocess import PyroProcess
from pymicroscope.utils.terminable import run_loop


class ImageProviderDelegate(Protocol):
    """
    Protocol for receiving images from an ImageProvider.
    """

    def new_image_captured(self, image: np.ndarray) -> None:
        """
        Called when a new image is captured.

        Args:
            image (np.ndarray): Captured image data.
        """
        ...


class ImageProvider(ABC):
    """
    Abstract base class defining the interface for image providers.

    Provides a configurable image capture process with delegate support.
    """

    def __init__(
        self,
        delegate: Optional[ImageProviderDelegate] = None,
        properties: Optional[dict[str, Any]] = None,
        *args: Any,
        **kwargs: Any
    ) -> None:
        """
        Initialize the image provider with optional delegate and properties.

        Args:
            delegate: Object implementing ImageProviderDelegate.
            properties: Dictionary of configuration settings.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.properties: dict[str, Any] = {
            "size": (480, 640),
            "frame_rate": 10,
            "channels": 3,
        }
        if properties:
            self.properties.update(properties)

        self.is_running: bool = False
        self._start_time: Optional[float] = None
        self._last_image: Optional[float] = None
        self._delegate: Optional[ImageProviderDelegate] = delegate

    @property
    def delegate(self) -> Optional[ImageProviderDelegate]:
        """Return the current delegate, if any."""
        return self._delegate

    def set_delegate(self, obj: ImageProviderDelegate) -> None:
        """Set the delegate that will receive captured images."""
        self._delegate = obj

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

    def capture_packaged_image(self) -> dict[str, Any]:
        """
        Capture an image and package it with metadata for transmission.

        Returns:
            A dictionary with 'data', 'shape', and 'dtype' keys.
        """
        image_array = self.capture_image()
        return {
            "data": image_array.tobytes(),
            "shape": image_array.shape,
            "dtype": str(image_array.dtype),
        }

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
                self.handle_remote_call_events()
                self.handle_pyro_events(daemon)

                img_tuple = self.capture_packaged_image()
                if self.delegate is not None:
                    self.delegate.new_image_captured(img_tuple)

            self.stop_capture()


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
        self._delegate_by_name: Optional[Union[str, URI]] = None

    @property
    def delegate(self) -> Optional[ImageProviderDelegate]:
        """
        Dynamically resolve delegate from name or URI if needed.

        Returns:
            The delegate object or proxy, if available.
        """
        if self._delegate_by_name is not None and self._delegate is None:
            if isinstance(self._delegate_by_name, URI):
                return PyroProcess.by_uri(self._delegate_by_name)
            elif isinstance(self._delegate_by_name, str):
                return PyroProcess.by_name(self._delegate_by_name)
        return self._delegate

    def set_delegate(self, obj_or_name: Union[ImageProviderDelegate, str, URI]) -> None:
        """
        Set the delegate as an object, Pyro name, or URI.  If it is a name or a URI
        we defer until the runloop to actually instantiate the object (i.e. it needs
        to be instantiated on the right thread)

        Args:
            obj_or_name: Can be a delegate object, a Pyro name, or a Pyro URI.
        """
        if isinstance(obj_or_name, (str, URI)):
            self._delegate_by_name = obj_or_name
            self._delegate = None
        else:
            super().set_delegate(obj_or_name)

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
                self.locate_ns().register(self.pyro_name, uri)

                self.start_capture()

                while not must_terminate_now:
                    self.handle_remote_call_events()
                    self.handle_pyro_events(daemon)

                    img_tuple = self.capture_packaged_image()
                    if self.delegate is not None:
                        self.delegate.new_image_captured(img_tuple)

                self.stop_capture()
                self.locate_ns().remove(self.pyro_name)


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
        img = np.random.randint(
            0, 256, (self.size[0], self.size[1], self.channels), dtype=np.uint8
        )

        frame_duration = 1 / self.frame_rate

        while (
            self._last_image is not None
            and time.time() < self._last_image + frame_duration
        ):
            time.sleep(0.001)

        self._last_image = time.time()
        self.log.debug("Image captured at %f", time.time() - self._start_time)
        return img


if __name__ == "__main__":
    provider = DebugRemoteImageProvider("ca.dccmlab.imageprovider.debug")
    provider.start()
    provider.join()
