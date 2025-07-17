import time
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Optional
import platform
import os

from mytk.notificationcenter import Notification, NotificationCenter
import numpy as np

from hardwarelibrary.motion import LinearMotionDevice

class Action:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def perform(self, results=None):
        start_time = time.time()

        results = self.do_perform(results)
        if results is None:
            results = {}

        results["start_time"] = start_time
        results["duration"] = time.time() - start_time
        results["action"] = self
        return results

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
    def __init__(self, n_images, queue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.n_images = n_images
        self.queue = queue

    def do_perform(self, results=None) -> dict[str, Any] | None:
        index = 0
        img_arrays = []

        queue = results.get("save_queue")
        if queue is None:
            raise RuntimeError("No save queue available")

        while index < self.n_images:
            img_array = queue.get()
            img_arrays.append(img_array)
            index = index + 1

        return {"captured_frames": img_arrays}


class ActionMean(Action):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def do_perform(self, results=None) -> dict[str, Any] | None:
        img_arrays = results.get("captured_frames")

        stacked = np.stack(img_arrays).astype(np.float64)
        mean_img = np.mean(stacked, axis=0)

        return {"processed_frames": mean_img}


class ActionSave(Action):
    def __init__(self, filepath: Path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filepath = filepath

    def do_perform(self, results=None) -> dict[str, Any] | None:
        pil_image = PILImage.fromarray(mean_img.astype(np.uint8), mode="RGB")
        params["i"] = "avg"
        filepath = self.root_dir / Path(self.template.format(**params))
        pil_image.save(filepath)


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

    def add_step(self, experiment_step):
        self.steps.append(experiment_step)

    def add_single_action_step(self, action: Action):
        self.add_step(ExperimentStep(perform=[action]))

    def add_many_single_action_steps(self, actions: list[Action]):
        for action in actions:
            self.add_single_action_step(action=action)

    def perform(self) -> Any | None:
        experiment_results = {}
        for i, step in enumerate(self.steps):
            results = step.perform()
            experiment_results[f"step-{i}"] = results

        return experiment_results
