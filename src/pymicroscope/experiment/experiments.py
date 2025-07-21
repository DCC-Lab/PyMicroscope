from __future__ import annotations

import time
from typing import Any
from multiprocessing import Queue
from threading import Thread
from pymicroscope.experiment.actions import Action

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
        self._thread = None
        
    def finalize(self):
        if self._thread is not None:
            self._thread.join()
        
    def add_step(self, experiment_step):
        self.steps.append(experiment_step)

    def add_single_action_step(self, action: Action):
        self.add_step(ExperimentStep(perform=[action]))

    def add_many_single_action_steps(self, actions: list[Action]):
        for action in actions:
            self.add_single_action_step(action=action)

    def perform(self) -> Any | None:
        experiment_results = {}
        start_time = time.time()
        
        for i, step in enumerate(self.steps):
            results = step.perform()
            experiment_results[f"step-{i}"] = results

        experiment_results['duration'] = time.time() - start_time

        return experiment_results

    def perform_in_background_thread(self):
        self._thread = Thread(target=self.perform)
        self._thread.start()

    @classmethod
    def from_actions(cls, actions)  -> Experiment:
        exp = Experiment()
        exp.add_step(ExperimentStep(perform=actions))
        return exp
        