class ImageProviderClient:
    """
    Protocol for receiving images from an ImageProvider.
    """

    def __init__(self, callback=None, *args, **kwargs) -> None:
        """
        Initialize the image provider client

        """
        super().__init__(*args, **kwargs)
        self.callback = callback
        self.images = []

    def new_image_captured(self, image: np.ndarray) -> None:
        """
        Called when a new image is captured.

        Args:
            image (np.ndarray): Captured image data.
        """

        if self.callback is not None:
            self.callback(image)
        else:
            self.images.append(image)
            self.images = self.images[-10:]


@expose
class RemoteImageProviderClient(PyroProcess, ImageProviderClient):
    """
    Protocol for receiving images from an ImageProvider.
    """

    def __init__(self, callback=None, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the image provider client

        """
        super().__init__(*args, **kwargs)
        self.callback = callback
        self.images = []

    def new_image_captured(self, image: np.ndarray) -> None:
        """
        Called when a new image is captured.

        Args:
            image (np.ndarray): Captured image data.
        """

        if self.callback is not None:
            self.callback(image)
        else:
            self.images.append(image)
            self.images = self.images[-10:]


@expose
class RemoteImageProvider(ImageProvider, PyroProcess):
    """
    Image provider that exposes its interface over Pyro5.
    """

    def __init__(self, pyro_name: Optional[str], *args: Any, **kwargs: Any) -> None:
        """
        Initialize and register a remote image provider.

        Args:
            pyro_name: Name used to register with Pyro name server.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(pyro_name=pyro_name, *args, **kwargs)
        self.lock = RLock()

    def client_to_proxy(self, obj_or_name) -> Optional[ImageProviderClient]:
        """
        Dynamically resolve client from name or URI if needed.

        Returns:
            The client object or proxy, if available.
        """
        with self.lock:
            if isinstance(obj_or_name, URI):
                return PyroProcess.by_uri(obj_or_name)
            elif isinstance(obj_or_name, str):
                return PyroProcess.by_name(obj_or_name)

            return obj_or_name

    def add_client(self, obj_or_name: Union[ImageProviderClient, str, URI]) -> None:
        """
        Add client as an object, Pyro name, or URI.  If it is a name or a URI
        we defer until the runloop to actually instantiate the object (i.e. it needs
        to be instantiated on the right thread)

        Args:
            obj_or_name: Can be a client object, a Pyro name, or a Pyro URI.
        """
        with self.lock:
            super().add_client(obj_or_name)

    def set_frame_rate(self, value: float) -> None:
        """
        Set the frame rate of the image provider.

        Args:
            value: Frame rate in Hz.
        """
        super().set_frame_rate(value)

    def run(self) -> None:
        """
        Main run loop with Pyro daemon registration and event handling.
        """
        with Daemon(host=self.get_local_ip()) as daemon:
            with self.syncing_context() as must_terminate_now:
                uri = daemon.register(self)
                ns = self.locate_ns()
                if ns is not None:
                    ns.register(self.pyro_name, uri)

                self.start_capture()

                while not must_terminate_now:
                    self.handle_remote_call_events()
                    self.handle_pyro_events(daemon)

                    img_tuple = self.capture_packaged_image()
                    with self.lock:
                        for client in self.clients:
                            proxy = self.client_to_proxy(client)
                            proxy.new_image_captured(img_tuple)

                self.stop_capture()

                ns = self.locate_ns()
                if ns is not None:
                    ns.remove(self.pyro_name)

    def get_last_packaged_image(self) -> dict[str, Any]:
        return super().get_last_packaged_image()


class DebugRemoteImageProvider(RemoteImageProvider):
    """
    An image provider that generates synthetic 8-bit images for testing.
    """

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

        img = self.generate_random_noise(self.size[0], self.size[1], self.channels)

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
        for i, color in enumerate(colors):
            img[:, i * bar_width : (i + 1) * bar_width, :] = color

        return img


    @staticmethod
    def image_from_package(package: dict[str, Any]) -> Any:
        data = base64.b64decode(package["data"])
        dtype = package["dtype"]
        shape = package["shape"]
        return np.frombuffer(data, dtype=dtype).reshape(shape)

    @staticmethod
    def image_to_package(image):
        return {
            "data": base64.b64encode(image.tobytes()).decode("ascii"),
            "shape": image.shape,
            "dtype": str(image.dtype),
        }

    def get_last_packaged_image(self) -> dict[str, Any]:
        return self.last_image_package

    def capture_packaged_image(self) -> dict[str, Any]:
        """
        Capture an image and package it with metadata for transmission.

        Returns:
            A dictionary with 'data', 'shape', and 'dtype' keys.
        """
        image_array = self.capture_image()
        self.last_image_package = ImageProvider.image_to_package(image_array)

        return self.last_image_package
