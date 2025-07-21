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

    def test035_perform_actions_without_argument(self):
        for SomeAction in Action.__subclasses__():
            try:
                SomeAction().perform()
            except TypeError as err:
                print(f"{SomeAction} needs arguments: {err}")
            
    def test040_change_property(self):
        class TestObject:
            def __init__(self, value):            
                self.value = value
        
        obj = TestObject(value=1)
        self.assertEqual(obj.value, 1)
        ActionChangeProperty(obj, 'value', 2).perform()
        self.assertEqual(obj.value, 2)

    def test050_wait(self):
        start_time = time.time()
        ActionWait(delay=1).perform()
        self.assertAlmostEqual(time.time() - start_time, 1, 1)

    def test060_bell(self):
        ActionBell().perform()        

    def test070_capture(self):
        n_images = 10
        capture = ActionCapture(n_images=n_images)
        queue = capture.queue
        for _ in range(n_images):
            queue.put(np.zeros(shape=(100,100,3), dtype=np.uint8))
            
        capture.perform()
        self.assertIsNotNone(capture.output)
        self.assertEqual(len(capture.output), n_images)

    def test070_mean(self):
        class SourceAction(Action):
            def __init__(self, n_images, *args, **kwargs):
                super().__init__(*args, **kwargs)
                
                self.output = []
                for _ in range(n_images):
                    self.output.append(np.zeros(shape=(100,100,3), dtype=np.uint8))
        n_images = 10
        source=SourceAction(n_images=n_images)
        mean = ActionMean(source=source)
        self.assertIsNone(mean.output)
        mean.perform()
        self.assertIsNotNone(mean.output)

    def test080_save(self):
        class SourceAction(Action):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                
                self.output = np.zeros(shape=(100,100,3), dtype=np.uint8)

        filepath = Path("/tmp/Image.tiff")
        if filepath.exists():
            os.unlink(filepath)
        self.assertFalse(filepath.exists())        

        source = SourceAction()
        save = ActionSave(source=source, root_dir="/tmp", template="Image.tiff")
        save.perform()
        self.assertTrue(filepath.exists())        
        os.unlink(filepath)

    def test090_save_in_background(self):
        class SourceAction(Action):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                
                self.output = np.zeros(shape=(100,100,3), dtype=np.uint8)

        filepath = Path("/tmp/Image.tiff")
        if filepath.exists():
            os.unlink(filepath)
        self.assertFalse(filepath.exists())        

        source = SourceAction()
        save = ActionSave(source=source, root_dir="/tmp", template="Image.tiff")
        
        save.perform_in_background()
        time.sleep(1)
        save.wait_for_completion()
        
        self.assertTrue(filepath.exists())        
        os.unlink(filepath)

    def test100_function_call(self):
        def function(a,b):
            return a*b
        action = ActionFunctionCall(function=function, fct_args=(2,3))
        results = action.perform()
        self.assertEqual(results['result'], 6)

        action = ActionFunctionCall(function=function, fct_kwargs={"a":2,"b":3})
        results = action.perform()
        self.assertEqual(results['result'], 6)
        
class ExperimentTestCase(
    envtest.CoreTestCase
):  # pylint: disable=too-many-public-methods
    def test000_init(self):
        self.assertIsNotNone(Experiment())

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

    def test110_exp_from_function_calls(self):
        def function(a,b):
            return a*b

        exp = Experiment.from_many_function_calls(function=function, fct_kwargs=[{"a":2,"b":3}, {"a":3,"b":4},{"a":5,"b":6}])
        results = exp.perform()
        print(results)

if __name__ == "__main__":
    envtest.main()
