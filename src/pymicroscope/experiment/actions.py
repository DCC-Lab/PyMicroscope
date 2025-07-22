from __future__ import annotations

import time
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Optional
import platform
import os
from multiprocessing import Queue
from mytk.notificationcenter import Notification, NotificationCenter
import numpy as np
from threading import Thread
from hardwarelibrary.motion import LinearMotionDevice
from PIL import Image as PILImage
from datetime import datetime

class Action:
    def __init__(self, source=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source = source
        self.output = None
        
    def perform(self, results=None):
        start_time = time.time()

        action_results = None

        action_results = self.do_perform(results)
        if action_results is None:
            action_results = {}

        action_results["start_time"] = start_time
        action_results["duration"] = time.time() - start_time
        action_results["action"] = self
        return action_results

    def do_perform(self, results=None) -> dict[str, Any] | None:
        raise RuntimeError(
            "You must implement the do_perform method in your class"
        )

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
            "new_value": self.value
        }    

class ActionWait(Action):
    def __init__(self, delay, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.delay = delay

    def do_perform(self, results=None) -> dict[str, Any] | None:
        time.sleep(self.delay)


class ActionBell(Action):
    def __init__(self, *args, **kwargs):
        super().__init__( *args, **kwargs)

    def do_perform(self, results=None) -> dict[str, Any] | None:
        if platform.system() == "Darwin":
            process = subprocess.Popen(["afplay", "/System/Library/Sounds/Glass.aiff"])
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
        print({"position": self.position})



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


class ActionCapture(Action):
    def __init__(self, n_images, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.n_images = n_images
        self.queue = Queue(maxsize=n_images)

    def do_perform(self, results=None) -> dict[str, Any] | None:
        index = 0
        img_arrays = []

        if self.queue is None:
            self.queue = results.get("save_queue")
            
        if self.queue is None:
            raise RuntimeError("No save queue available")

        while index < self.n_images:
            img_array = self.queue.get()
            img_arrays.append(img_array)
            index = index + 1

        self.queue.close()
        self.queue.join_thread()
        
        self.output = img_arrays
        return {"captured_frames": img_arrays}


class ActionMean(Action):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def do_perform(self, results=None) -> dict[str, Any] | None:
        img_arrays = self.source.output

        stacked = np.stack(img_arrays).astype(np.float64)
        mean_img = np.mean(stacked, axis=0)

        self.output = mean_img

        return {"processed_frames": mean_img}


class ActionSave(Action):
    def __init__(self, root_dir=None, template=None, *args, **kwargs):
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
        params = {"date":date_str, "time":time_str}

        params['i'] = "avg"                     
        filepath = self.root_dir / Path(self.template.format(**params))
        pil_image.save(filepath)

        self.output = filepath

class ActionClear(Action):
    def __init__(self, filepath: Path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filepath = filepath
        for file in self.filepath:
            self.filepath[file] = None


