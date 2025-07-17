import time
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Optional

from mytk import App

from hardwarelibrary.motion import LinearMotionDevice


class Action:
    def __init__(self, inputs:dict[str, Any], *args, **kwargs):
        self.inputs:dict[str, Any] = inputs
        self.outputs:dict[str, Any] = None

    def perform(self):
        raise RuntimeError("You must implement the perform method in your class")

@dataclass
class ExperimentStep:
    prepare_actions:list[Action] = None
    perform_actions:list[Action] = None
    finalize_actions:list[Action] = None
    
    def perform(self):
        if self.prepare_actions is not None:
            result = None
            for action in self.prepare_actions:
                result = action.perform(inputs=result)

        if self.perform_actions is not None:
            result = None
            for action in self.perform_actions:
                result = action.perform(result=result)
                
        if self.finalize_actions is not None:
            result = None
            for action in self.finalize_actions:
                result = action.perform(result=result)

            

class ActionWait(Action):
    def __init__(self, delay, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.delay = delay
        
    def perform(self) -> Any | None:
        time.sleep(self.delay)
    
        
class ActionMove(Action):
    def __init__(self, position:list[int], linear_motion_device:LinearMotionDevice, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.position:list[int] = position
        self.device:LinearMotionDevice = linear_motion_device
        
    def perform(self) -> Any | None:
        self.device.moveInMicronsTo(self.position)

class ActionCapture(Action):
    def __init__(self, n_images, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.n_images = n_images
        self.images = []
    
class ActionSave(Action):
    def __init__(self, filepath:Path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filepath = filepath
        
        
class ExperimentManager:
    def __init__(self, *args, **kwargs):
        self.steps:list[ExperimentStep] = []

    def add_action(self, action:Action):
        self.steps.append( ExperimentStep(perform_actions=[Action]))
    
    def add_actions(self, actions:list[Action]):
        for action in actions:
            self.add_action(action=action)
    
    def perform_all_actions(self) -> Any | None:
        for step in self.steps:
            if step.prepare is not None:
                for action in step.prepare:
                    action.pe
            
            App.app.save()
        
        self.actions = []