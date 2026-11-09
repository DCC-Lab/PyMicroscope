import numpy as np
from typing import Any, Optional

from pymicroscope.acquisition.imageprovider import ImageProvider, Controllable
from pymicroscope.utils.configurable import ProcessSafeConfigurable

class ScanGeneratorService(ProcessSafeConfigurable):
    pass

class ImageAcquisitionService(ProcessSafeConfigurable):
    pass

class LSMImageProvider(ImageProvider):
    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.scan_generator = ScanGeneratorService()
        self.image_acquisition_service = ImageAcquisitionService()
        
        