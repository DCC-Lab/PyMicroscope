from enum import Enum

"""
Notification enums used throughout the application to signal major events 
related to image capture and experiment workflows. These constants are 
typically used for publishing/subscribing to events within the application.
"""

class MicroscopeAppNotification(Enum):
    """
    Enumerates notifications emitted by the microscope application during
    image acquisition and saving processes. These can be used to trigger
    UI updates, logging, or downstream processing.

    Attributes:
        new_image_received: A new image has been captured and received. user_info: 'img_array' has image
        will_start_capture: Capture is about to begin.
        did_start_capture: Capture has started.
        will_stop_capture: Capture is about to stop.
        did_stop_capture: Capture has stopped.
        did_start_saving: Saving process has started.
        did_save: An image has been saved. user_info: 'img_array' has image and 'filepath'
        action_progress: progrss of a given action user_info : 'action', 'progress', 'n_steps', 'step', 'description'
    """
    new_image_received = "new_image_received" 
    will_start_capture = "will_start_capture"
    did_start_capture = "did_start_capture"
    will_stop_capture = "will_stop_capture"
    did_stop_capture = "did_stop_capture"
    did_start_saving = "did_start_saving"
    did_save = "did_save"
    action_progress = "action_progress"
    available_providers_changed = "available_providers_changed"