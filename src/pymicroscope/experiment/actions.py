from __future__ import annotations

import time
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output = None
        
    def perform(self, results=None):
        start_time = time.time()

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


class ActionWait(Action):
    def __init__(self, delay, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.delay = delay

    def do_perform(self, results=None) -> dict[str, Any] | None:
        time.sleep(self.delay)


class ActionBell(Action):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def do_perform(self, results=None) -> dict[str, Any] | None:
        if platform.system() == "Darwin":
            os.system("afplay /System/Library/Sounds/Glass.aiff")
        else:
            print("\a")


class ActionMove(Action):
    def __init__(
        self,
        position: list[int],
        linear_motion_device: LinearMotionDevice,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.position: list[int] = position
        self.device: LinearMotionDevice = linear_motion_device

    def do_perform(self, results=None) -> dict[str, Any] | None:
        self.device.moveInMicronsTo(self.position)
        return {"position": self.position}


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
    def __init__(self, source, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source = source
        
    def do_perform(self, results=None) -> dict[str, Any] | None:
        img_arrays = self.source.output

        stacked = np.stack(img_arrays).astype(np.float64)
        mean_img = np.mean(stacked, axis=0)

        self.output = mean_img

        return {"processed_frames": mean_img}


class ActionSave(Action):
    def __init__(self, source, root_dir=None, template=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root_dir = root_dir
        if self.root_dir is None:
            self.root_dir = Path("/tmp").expanduser()
        
        self.template = template
        if template is None:
            self.template = "Image-{date}-{time}-{i:03d}.tif"
        self.source = source


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


class ExperimentStep:
    def __init__(
        self,
        prepare: list[Action] = None,
        perform: list[Action] = None,
        finalize: list[Action] = None,
        *args,
        **kwargs,
    ):
        self.prepare_actions: list[Action] = prepare
        self.perform_actions: list[Action] = perform
        self.finalize_actions: list[Action] = finalize
        self.results = {}

    def perform(self, results=None):
        if self.prepare_actions is not None:
            for i, action in enumerate(self.prepare_actions):
                result = action.perform(results=self.results)
                if result is not None:
                    self.results[f"prepare-{i}"] = result

        if self.perform_actions is not None:
            for i, action in enumerate(self.perform_actions):
                result = action.perform(results=self.results)
                if result is not None:
                    self.results[f"perform-{i}"] = result

        if self.finalize_actions is not None:
            for i, action in enumerate(self.finalize_actions):
                result = action.perform(results=self.results)
                if result is not None:
                    self.results[f"finalize-{i}"] = result

        return self.results


class Experiment:        
    def __init__(self, *args, **kwargs):
        self.results = {}
        self.steps: list[ExperimentStep] = []
        self.thread = None
        
    def add_step(self, experiment_step):
        self.steps.append(experiment_step)

    def add_single_action_step(self, action: Action):
        self.add_step(ExperimentStep(perform=[action]))

    def add_many_single_action_steps(self, actions: list[Action]):
        for action in actions:
            self.add_single_action_step(action=action)

    def perform(self) -> Any | None:
        print("Starting experiment")
        experiment_results = {}
        for i, step in enumerate(self.steps):
            results = step.perform()
            experiment_results[f"step-{i}"] = results

        print("Experiment done")

        return experiment_results

    def perform_in_background_thread(self):
        self.thread = Thread(target=self.perform)
        self.thread.start()

    @classmethod
    def from_actions(cls, actions)  -> Experiment:
        exp = Experiment()
        exp.add_step(ExperimentStep(perform=actions))
        return exp
        