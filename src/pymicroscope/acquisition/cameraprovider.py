from pymicroscope.acquisition.imageprovider import ImageProvider


class CameraProvider(ImageProvider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
