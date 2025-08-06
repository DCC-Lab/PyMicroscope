from __future__ import annotations
import weakref

import time
import os
import subprocess
from pathlib import Path
from typing import Any
import platform
from enum import Enum
from mytk.notificationcenter import Notification, NotificationCenter
import os
from contextlib import suppress
from multiprocessing import Queue
import numpy as np
from hardwarelibrary.motion import LinearMotionDevice
from PIL import Image as PILImage
from datetime import datetime
from threading import Thread
from mytk.notificationcenter import NotificationCenter
from pymicroscope.app_notifications import MicroscopeAppNotification


class Action:
    def __init__(self, source=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source = source
        self.output = None
        self.thread = None
        self.action_results = None

    def perform(self, results=None):
        start_time = time.time()

        action_results = self.do_perform(results)
        if action_results is None:
            action_results = {}

        action_results["start_time"] = start_time
        action_results["duration"] = time.time() - start_time

        self.action_results = action_results
        return self.action_results

    def do_perform(self, results=None) -> dict[str, Any] | None:
        raise RuntimeError(
            "You must implement the do_perform method in your class"
        )

    def cleanup(self):
        pass

    def perform_in_background(self, results=None):
        self.thread = Thread(target=self.perform, args=(results,))
        self.thread.start()

    def wait_for_completion(self):
        if self.thread is not None:
            self.thread.join()


class ActionChangeProperty(Action):
    def __init__(self, target, property_name, value, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target = target
        self.property_name = property_name
        self.value = value

    def do_perform(self, results=None) -> dict[str, Any] | None:
        old_value = getattr(self.target, self.property_name, None)
        setattr(self.target, self.property_name, self.value)

        return {
            "target": self.target,
            "property": self.property_name,
            "old_value": old_value,
            "new_value": self.value,
        }


class ActionWait(Action):
    def __init__(self, delay, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.delay = delay

    def do_perform(self, results=None) -> dict[str, Any] | None:
        time.sleep(self.delay)


class ActionSound(Action):
    class MacOSSound(str, Enum):
        BLOW = "Blow"
        BOTTLE = "Bottle"
        FROG = "Frog"
        FUNK = "Funk"
        GLASS = "Glass"
        HERO = "Hero"
        MORSE = "Morse"
        PING = "Ping"
        POP = "Pop"
        PURR = "Purr"
        SOSUMI = "Sosumi"
        SUBMARINE = "Submarine"
        TAP = "Tink"

    def __init__(
        self, sound_name: MacOSSound = MacOSSound.FROG, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.sound_file = f"/System/Library/Sounds/{sound_name.value}.aiff"
        if not os.path.exists(self.sound_file):
            self.sound_file = f"/System/Library/Sounds/Frog.aiff"

    def do_perform(self, results=None) -> dict[str, Any] | None:
        if platform.system() == "Darwin":
            process = subprocess.Popen(["afplay", self.sound_file])
        else:
            print("\a")


class ActionMove(Action):
    def __init__(
        self,
        position: tuple[int],
        linear_motion_device: LinearMotionDevice,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.position: tuple[int] = position
        self.device: LinearMotionDevice = linear_motion_device

    def do_perform(self, results=None) -> None:
        self.device.moveInMicronsTo(self.position)


class ActionMoveBy(Action):
    def __init__(
        self,
        d_position: list[int],
        linear_motion_device: LinearMotionDevice,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.d_position: list[int] = d_position
        self.device: LinearMotionDevice = linear_motion_device

    def do_perform(self, results=None) -> dict[str, Any] | None:
        self.device.moveInMicronsBy(self.d_position)
        return {"displacement": self.d_position}


class ActionFunctionCall(Action):
    def __init__(
        self, function, fct_args=None, fct_kwargs=None, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.function = function
        if fct_args is None:
            fct_args = ()
        self.fct_args = fct_args

        if fct_kwargs is None:
            fct_kwargs = {}
        self.fct_kwargs = fct_kwargs

    def do_perform(self, results=None) -> dict[str, Any] | None:
        self.action_results = self.function(*self.fct_args, **self.fct_kwargs)
        return {"result": self.action_results}


class ActionAccumulate(Action):
    def __init__(self, n_images, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.n_images = n_images
        self.queue = Queue(maxsize=n_images)

    def handle_new_image(self, notification):
        img_array = notification.user_info["img_array"]
        if img_array is not None:
            with suppress(ValueError):
                self.queue.put(img_array)

    def do_perform(self, results=None) -> dict[str, Any] | None:
        index = 0
        img_arrays = []

        NotificationCenter().add_observer(
            self,
            method=self.handle_new_image,
            notification_name=MicroscopeAppNotification.new_image_received,
        )

        if self.queue is None:
            self.queue = results.get("save_queue")

        if self.queue is None:
            raise RuntimeError("No save queue available")

        while len(img_arrays) < self.n_images:
            img_array = self.queue.get()
            img_arrays.append(img_array)
            index = index + 1

        NotificationCenter().remove_observer(
            self, notification_name=MicroscopeAppNotification.new_image_received
        )

        self.queue.close()
        self.queue.join_thread()

        self.output = img_arrays
        return {"captured_frames": img_arrays}


class ActionMean(Action):
    def __init__(self, source, *args, **kwargs):
        kwargs["source"] = source
        super().__init__(*args, **kwargs)

    def do_perform(self, results=None) -> dict[str, Any] | None:
        img_arrays = self.source.output

        stacked = np.stack(img_arrays).astype(np.float64)
        mean_img = np.mean(stacked, axis=0)

        self.output = mean_img

        return {"processed_frames": mean_img}


class ActionProviderRun(Action):
    def __init__(self, app, start, *args, **kwargs):
        self.app_ref = weakref.ref(app)
        self.start = start

    def do_perform(self, results=None) -> dict[str, Any] | None:
        if self.start:
            self.app_ref().start_capture()
        else:
            self.app_ref().stop_capture()

        return {}


class ActionPostNotification(Action):
    def __init__(
        self,
        notification_name,
        notifying_object=None,
        user_info=None,
        *args,
        **kwargs,
    ):
        self.name = notification_name
        self.object = notifying_object
        self.user_info = user_info

    def do_perform(self, results=None) -> dict[str, Any] | None:
        NotificationCenter().post_notification(
            self.name, self.object, self.user_info
        )

        return {}


class ActionSave(Action):
    def __init__(self, source, root_dir=None, template=None, *args, **kwargs):
        kwargs["source"] = source
        super().__init__(*args, **kwargs)
        self.root_dir = root_dir
        if self.root_dir is None:
            self.root_dir = Path("/tmp").expanduser()

        self.template = template
        if template is None:
            self.template = "Image-{date}-{time}-{i:03d}.tif"

    def do_perform(self, results=None) -> dict[str, Any] | None:
        img_array = self.source.output

        pil_image = PILImage.fromarray(img_array.astype(np.uint8), mode="RGB")

        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M%S")
        params = {"date": date_str, "time": time_str}

        params["i"] = "avg"
        filepath = self.root_dir / Path(self.template.format(**params))
        pil_image.save(filepath)

        NotificationCenter().post_notification(MicroscopeAppNotification.did_save, notifying_object=self, user_info={'filepath':filepath, 'img_array':img_array})

        self.output = filepath


class ActionClear(Action):
    def __init__(self, filepath: Path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filepath = filepath
        for file in self.filepath:
            self.filepath[file] = None
