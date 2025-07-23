import time
import logging
from typing import Optional, Tuple, Any
import base64

import numpy as np
import cv2

import envtest  # setup environment for testing
from pymicroscope.acquisition.imageprovider import ImageProvider
from pymicroscope.acquisition.cameraprovider import OpenCVImageProvider


class ImageProviderTestCase(envtest.CoreTestCase):
    """
    Unit tests for the image provider system including client registration,
    process lifecycle, and Pyro name resolution.
    """

    def test000_init_provider(self) -> None:
        """
        Verify that the abstract ImageProvider cannot be instantiated directly.
        """
        self.assertIsNotNone(OpenCVImageProvider())

    def test010_init_debugprovider(self) -> None:
        """
        Verify that the DebugRemoteImageProvider can be instantiated.
        """
        available_devices = []
        index = 0
        while True:
            cap = cv2.VideoCapture(index)                                
            if cap.isOpened():
                available_devices.append(index)
                cap.release()
                index += 1
            else:
                break

        print(available_devices)
        self.assertTrue(len(available_devices) > 0)
        
        
    # def test020_init_running_debug_provider(self) -> None:
    #     """
    #     Start and stop the debug provider to verify lifecycle.
    #     """
    #     prov = OpenCVImageProvider()
    #     prov.start_synchronously()
    #     time.sleep(0.1)
    #     prov.terminate_synchronously()


if __name__ == "__main__":
    envtest.main()
