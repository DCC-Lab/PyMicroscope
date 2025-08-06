import numpy as np
from typing import Any, Optional

from pymicroscope.acquisition.imageprovider import ImageProvider, Controllable, Configurable
    
class ScanGeneratorService(Configurable):
    pass

class ImageAcquisitionService(Configurable):
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
        
        