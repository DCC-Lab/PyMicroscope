from pymicroscope.utils.pyroprocess import PyroProcess

from pymicroscope.acquisition.imageprovider import (
    ImageProvider,
    ImageProviderClient,
    DebugImageProvider,
    show_provider,
)

imageprovider = None

pyro_objects = PyroProcess.available_objects()
for name, uri in pyro_objects.items():
    if "imageprovider" in name:
        provider = PyroProcess.by_uri(uri)


while True:
    img_pack = provider.get_last_packaged_image()
    array = ImageProvider.image_from_package(img_pack)
    print(array)
