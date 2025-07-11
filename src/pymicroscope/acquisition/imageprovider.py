from abc import ABC, abstractmethod
import time
import math
from typing import Protocol, Optional, Union, Type, Any, Callable, Tuple
from multiprocessing import RLock, shared_memory
import numpy as np
import base64
from multiprocessing import Queue
from Pyro5.api import expose, Daemon, locate_ns, Proxy, URI

from pymicroscope.utils.pyroprocess import PyroProcess
from pymicroscope.utils.terminable import run_loop, TerminableProcess
from pymicroscope.utils.unifiedprocess import UnifiedProcess

from PIL import Image as PILImage



class ImageProvider(TerminableProcess):
    """
    Abstract base class defining the interface for image providers.

    Provides a configurable image capture process with client support.
    """

    def __init__(
        self, properties: Optional[dict[str, Any]] = None, queue:Optional[Queue] = None, *args: Any, **kwargs: Any
    ) -> None:
        """
        Initialize the image provider with optional client and properties.

        Args:
            client: Object implementing ImageProviderClient.
            properties: Dictionary of configuration settings.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(*args, **kwargs)
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
        
        self.image_queue = queue
        
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
                    img_array = self.capture_image()
                    self.image_queue.put(img_array)
                except Exception as err:
                    self.log.error(f"Error in ImageProvider run loop : {err}")
            self.stop_capture()

class DebugImageProvider(ImageProvider):
    """
    An image provider that generates synthetic 8-bit images for testing.
    """
    def __init__(self, size=None, *args, **kwargs):
        super().__init__(name="DebugImageProvider", *args, **kwargs)
        if size is not None:
            self.properties['size'] = (size[0], size[1])
        
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
        log_level=logging.DEBUG, queue=Queue()
    )
    provider.start_synchronously()
    provider.join()
