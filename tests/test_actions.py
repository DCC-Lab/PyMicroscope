import envtest  # setup environment for testing
from pymicroscope.experiment.actions import *
from pymicroscope.experiment.experiments import Experiment, ExperimentStep
import json


class TestDevice:
    def moveInMicronsTo(self, position):
        pass

    def moveInMicronsBy(self, distance):
        pass


class ActionTestCase(
    envtest.CoreTestCase
):  # pylint: disable=too-many-public-methods
    def test000_init(self):
        self.assertIsNotNone(Experiment())

    def test010_action_move(self):
        action = ActionMove(
            position=(0, 0, 0), linear_motion_device=TestDevice()
        )
        self.assertIsNotNone(action)

        with self.assertRaises(TypeError):
            ActionMove(position=(0, 0, 0))

    def test020_action_move(self):
        action = ActionMove(
            position=(0, 0, 0), linear_motion_device=TestDevice()
        )
        action.perform([{"Test": True}])

    def test030_action_move_results(self):
        action = ActionMove(
            position=(0, 0, 0), linear_motion_device=TestDevice()
        )
        _ = action.perform({"Test": True})

    def test040_exp_add_actions(self):
        exp = Experiment()
        exp.add_single_action_step(ActionWait(0.05))
        exp.add_single_action_step(ActionWait(0.05))
        exp.perform()

    def test040_exp_add_actions(self):
        exp = Experiment()
        exp.add_single_action_step(ActionWait(0.05))
        exp.add_single_action_step(ActionWait(0.05))
        exp.perform()

    def test050_exp_add_many_actions(self):
        exp = Experiment()
        exp.add_many_single_action_steps(
            [ActionWait(0.02), ActionBell(), ActionWait(0.02)]
        )
        print(exp.perform())

    def test060_exp_add_step(self):
        exp = Experiment()
        exp.add_step(
            ExperimentStep(
                prepare=[ActionWait(0.02), ActionBell(), ActionWait(0.02)],
                perform=[ActionWait(0.02), ActionBell(), ActionWait(0.02)],
                finalize=[ActionWait(0.02), ActionBell(), ActionWait(0.02)],
            )
        )
        exp.add_step(
            ExperimentStep(
                prepare=[ActionWait(0.02), ActionBell(), ActionWait(0.02)],
                perform=[ActionWait(0.02), ActionBell(), ActionWait(0.02)],
                finalize=[ActionWait(0.02), ActionBell(), ActionWait(0.02)],
            )
        )

        results = exp.perform()
        # print(json.dumps(results, indent=4, sort_keys=True))


if __name__ == "__main__":
    envtest.main()
