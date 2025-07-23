import time
import logging
from typing import Optional, Tuple, Any
import base64

import numpy as np

import envtest  # setup environment for testing
from pymicroscope.utils.pyroprocess import PyroProcess
from pymicroscope.acquisition.imageprovider import (
    ImageProvider
)

if __name__ == "__main__":
    envtest.main()
