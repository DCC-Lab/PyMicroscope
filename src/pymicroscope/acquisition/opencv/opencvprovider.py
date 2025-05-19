import importlib
import signal
import cv2


class OpenCVImageProvider(ImageProvider):
    def __init__(self, device=0, zoom_level=3, auto_start=True):
        super().__init__()

        self.device = device
        self.image = None
        self.capture = None
        self.videowriter = None

        self.abort = False
        self.auto_start = auto_start

    def signal_handler(self, sig, frame):
        print(f"Handling signal {sig} ({signal.Signals(sig).name}).")
        if sig == signal.SIGINT:
            if self.is_running:
                self.abort = True
            else:
                self.previous_handler(sig, frame)

    @classmethod
    def available_devices(cls):
        available_devices = []
        try:
            index = 0
            while True:
                cap = self.cv2.VideoCapture(index)
                if not cap.read()[0]:
                    break
                else:
                    available_devices.append(index)
                cap.release()
                index += 1
        except Exception as err:
            pass

        return available_devices

    @property
    def is_running(self):
        return self.capture is not None

    def start_capturing(self):
        if not self.is_running:
            try:
                self.capture = self.cv2.VideoCapture(self.device)
                if self.capture.isOpened():
                    self.update_display()
            except Exception as err:
                print(err)
                self.capture = None

    def stop_capturing(self):
        if self.is_running:
            if self.next_scheduled_update is not None:
                App.app.root.after_cancel(self.next_scheduled_update)
            self.capture.release()
            self.capture = None

    def prop_ids(self):
        capture = self.capture
        print(
            "CV_CAP_PROP_FRAME_WIDTH: '{}'".format(
                capture.get(self.cv2.CAP_PROP_FRAME_WIDTH)
            )
        )
        print(
            "CV_CAP_PROP_FRAME_HEIGHT : '{}'".format(
                capture.get(self.cv2.CAP_PROP_FRAME_HEIGHT)
            )
        )
        print("CAP_PROP_FPS : '{}'".format(capture.get(self.cv2.CAP_PROP_FPS)))
        print(
            "CAP_PROP_POS_MSEC : '{}'".format(capture.get(self.cv2.CAP_PROP_POS_MSEC))
        )
        print(
            "CAP_PROP_FRAME_COUNT  : '{}'".format(
                capture.get(self.cv2.CAP_PROP_FRAME_COUNT)
            )
        )
        print(
            "CAP_PROP_BRIGHTNESS : '{}'".format(
                capture.get(self.cv2.CAP_PROP_BRIGHTNESS)
            )
        )
        print(
            "CAP_PROP_CONTRAST : '{}'".format(capture.get(self.cv2.CAP_PROP_CONTRAST))
        )
        print(
            "CAP_PROP_SATURATION : '{}'".format(
                capture.get(self.cv2.CAP_PROP_SATURATION)
            )
        )
        print("CAP_PROP_HUE : '{}'".format(capture.get(self.cv2.CAP_PROP_HUE)))
        print("CAP_PROP_GAIN  : '{}'".format(capture.get(self.cv2.CAP_PROP_GAIN)))
        print(
            "CAP_PROP_CONVERT_RGB : '{}'".format(
                capture.get(self.cv2.CAP_PROP_CONVERT_RGB)
            )
        )

    def get_prop_id(self, prop_id):
        """
        Important prop_id:
        CAP_PROP_POS_MSEC Current position of the video file in milliseconds or video capture timestamp.
        CAP_PROP_POS_FRAMES 0-based index of the frame to be decoded/captured next.
        CAP_PROP_FRAME_WIDTH Width of the frames in the video stream.
        CAP_PROP_FRAME_HEIGHT Height of the frames in the video stream.
        CAP_PROP_FPS Frame rate.
        CAP_PROP_FOURCC 4-character code of codec.
        CAP_PROP_FORMAT Format of the Mat objects returned by retrieve() .
        CAP_PROP_MODE Backend-specific value indicating the current capture mode.
        CAP_PROP_CONVERT_RGB Boolean flags indicating whether images should be converted to RGB.
        """
        if self.capture is not None:
            return self.capture.get(prop_id)
        return None
