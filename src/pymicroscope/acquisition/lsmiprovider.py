import numpy as np
from typing import Any, Optional

from pymicroscope.acquisition.imageprovider import ImageProvider

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
    
    
class Configurable:
    def __init__(self, properties, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.properties = properties
        self.dialog = None
        
    def configuration_dialog(self):
        return self.dialog
    
    def set_configuration(self, properties):
        self.properties = properties
        
    def get_configuration(self):
        return self.properties
        
    
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
        
        