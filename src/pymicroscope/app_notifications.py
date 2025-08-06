from enum import Enum

class MicroscopeAppNotification(Enum):
    new_image_received = "new_image_received"
    will_start_capture = "will_start_capture"
    did_start_capture = "did_start_capture"
    will_stop_capture = "will_stop_capture"
    did_stop_capture = "did_stop_capture"
    did_start_saving = "did_start_saving"
    did_save = "did_save"
