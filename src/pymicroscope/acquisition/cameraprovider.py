import cv2
import numpy as np
from typing import Any, Optional
import time

from pymicroscope.acquisition.imageprovider import ImageProvider
from pymicroscope.utils.configurable import Configurable, ConfigurableProperty


class OpenCVImageProvider(ImageProvider):
    """
    Image provider using OpenCV to capture frames from a camera.
    """

    _available_devices = None
    
    def __init__(
        self,
        camera_index: int = 0,
        *args: Any,
        **kwargs: Any,
    ) -> None:

        prop_index = ConfigurableProperty("camera_index",0)
        
        properties_description = kwargs.get('properties_description',[])
        properties_description.append(prop_index)
        kwargs['properties_description'] = properties_description
        
        configuration = kwargs.get('configuration',{})
        configuration.update({"camera_index":camera_index})
        kwargs['configuration'] = configuration

        super().__init__(*args, **kwargs)
    
        
    @classmethod
    def available_devices(cls):
        if cls._available_devices is None:
            cls._available_devices = []
            try:
                index = 0
                while True:
                    cap = cv2.VideoCapture(index)
                    if not cap.read()[0]:
                        break
                    else:
                        cls._available_devices.append(index)
                    cap.release()
                    index += 1
            except Exception as err:
                print(err)

        return cls._available_devices

    def capture_image(self) -> np.ndarray:
        if not self.cap or not self.cap.isOpened():
            raise RuntimeError("Camera is not open. Call start_capture() first.")

        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError("Failed to capture image from camera.")

        # Convert to RGB if needed
        if self.channels == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        elif self.channels == 1:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frame = np.expand_dims(frame, axis=2)

        # Resize to requested size (height, width) if different from camera native
        target_size = (self.height, self.width)
        if frame.shape[0] != target_size[0] or frame.shape[1] != target_size[1]:
            frame = cv2.resize(frame, (target_size[1], target_size[0]))

        return frame
    
    def run(self):
        self.cap = cv2.VideoCapture(self.configuration['camera_index'])

        # Wait until camera is ready
        timeout = 5  # seconds
        start_time = time.time()

        while True:
            ret, frame = self.cap.read()
            if ret:
                break
            if time.time() - start_time > timeout:
                raise TimeoutError("Camera not ready after waiting {} seconds".format(timeout))
            time.sleep(0.1)  # avoid tight loop
        super().run()