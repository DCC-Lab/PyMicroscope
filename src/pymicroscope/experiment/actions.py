from mytk import App

class Action:
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
    
    def perform(self):
        raise RuntimeError("You must implement the perform method in your class")
    

class ActionMove(Action):
    def __init__(self, position, linear_motion_device, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.position = position
        self.device = linear_motion_device
        
    def perform(self):
        self.device.moveTo(self.position)            

class ExperimentalActionManager:
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.actions = []

    def add_action(self, action):
        self.actions.append(action)
    
    def add_actions(self, actions):
        self.actions.extend(actions)
    
    def perform_all_actions(self):
        for action in self.actions:
            action.perform()
            App.app.save()
        
        self.actions = []