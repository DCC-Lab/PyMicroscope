import time
import math
from typing import Protocol, Optional, Union, Type, Any, Callable, Tuple, Generic, TypeVar

import numpy as np
from multiprocessing import Queue, Value
from dataclasses import dataclass

from mytk import Dialog
from pymicroscope.utils.terminable import run_loop, TerminableProcess
from pymicroscope.utils.configurable import Configurable, ConfigurableProperty
from pymicroscope.vmsconfigdialog import VMSConfigDialog

class Controllable:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize(self):
        pass
    
    def shutdown(self):
        pass
        
    def start(self):
        pass

    def stop(self):
        pass
    
        
class ImageProvider(TerminableProcess, Configurable):
    """
    Abstract base class defining the interface for image providers.

    Provides a configurable image capture process with client support.
    """

    def __init__(
        self, queue:Optional[Queue] = None, *args: Any, **kwargs: Any
    ) -> None:
        """
        Initialize the image provider with optional client and properties.

        Note: Process() is not cooperative and the MRO is incorrect.
        I need to call the __init__() manuallty and remove the spurios arguments
        
        Args:
            client: Object implementing ImageProviderClient.
            properties: Dictionary of configuration settings.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        
        prop_width = ConfigurableProperty(
            name="width",
            default_value=640,
        )
        prop_height = ConfigurableProperty(
            name="height",
            default_value=480,
        )

        prop_frame_rate = ConfigurableProperty(
            name="frame_rate",
            default_value=30,
        )

        properties_description = kwargs.pop("properties_description", [])
        properties_description.extend([prop_width, prop_height,prop_frame_rate])
        
        configuration = {"frame_rate":30, "channels":3, "size":(480, 640)}
        configuration.update(kwargs.pop("configuration", {}))
        
        Configurable.__init__(self, properties_description=properties_description, configuration=configuration)
        
        TerminableProcess.__init__(self, *args, **kwargs)

        self._is_running = Value('b', False)
        self._last_image = None
        self.image_queue = queue
    
    @property
    def is_running(self):
        with self._is_running.get_lock():
            return self._is_running.value != 0

    @is_running.setter
    def is_running(self, value):
        with self._is_running.get_lock():
            if value != 0:
                self._is_running.value = True
            else:
                self._is_running.value = False
    
    @property
    def width(self) -> int:
        return self.configuration["width"]

    def set_width(self, value: int) -> None:
        self.configuration["width"] = value

    @property
    def height(self) -> int:
        return self.configuration["height"]

    def set_height(self, value: int) -> None:
        self.configuration["height"] = value

    @property
    def frame_rate(self) -> float:
        """Return the frame rate in Hz."""
        return self.configuration["frame_rate"]

    def set_frame_rate(self, value: float) -> None:
        """Set the frame rate in Hz."""
        self.configuration["frame_rate"] = value

    @property
    def channels(self) -> int:
        """Return the number of image channels (e.g., 3 for RGB)."""
        return self.configuration["channels"]

    def set_channels(self, value: int) -> None:
        """Set the number of image channels."""
        self.configuration["channels"] = value

    def capture_image(self) -> np.ndarray:
        """
        Capture an image and return it as a NumPy array.

        Must be implemented by subclasses.
        """
        pass

    def start_capture(self, configuration) -> None:
        """Mark the beginning of an image capture session."""
        with self._is_running.get_lock():
            self._is_running.value = 1
        
        self.configuration.update(configuration)

    def stop_capture(self) -> None:
        """Stop the image capture session."""
        with self._is_running.get_lock():
            self._is_running.value = 0

    def set_configuration(self, properties: dict[str, Any]) -> None:
        """
        Update provider configuration.

        Args:
            properties: Dictionary of property updates.
        """
        self.configuration.update(properties)

    def get_configuration(self) -> dict[str, Any]:
        """
        Get current provider configuration.

        Returns:
            Dictionary of configuration values.
        """
        return self.configuration

    def run(self) -> None:
        """
        Main capture loop for local use (no Pyro registration).

        Subclasses may override this.
        """
        with self.syncing_context() as must_terminate_now:
            while not must_terminate_now:
                try:
                    with self._is_running.get_lock():
                        if self._is_running.value:
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
        super().__init__(*args, **kwargs)
                
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
        img = self.generate_color_bars(self.height, self.width)

        frame_duration = 1 / self.frame_rate

        while (
            self._last_image is not None
            and time.time() < self._last_image + frame_duration
        ):
            time.sleep(0.001)
        self._last_image = time.time()
        
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
    print(ImageProvider.__mro__)
    ImageProvider(properties_description=[])
    # import logging

    # # provider = DebugImageProvider(
    # #     log_level=logging.DEBUG, pyro_name="ca.dccmlab.imageprovider.debug"
    # # )
    # provider = DebugImageProvider(
    #     log_level=logging.DEBUG, queue=Queue()
    # )
    # provider.start_synchronously()
    # provider.join()
