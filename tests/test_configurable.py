import time
import multiprocessing as mp
from multiprocessing.managers import DictProxy

import envtest

from pymicroscope.utils.configurable import (
    ProcessSafeConfigurable,
    ProcessSafeConfigurableNumericProperty,
)


class SimpleConfigurable(ProcessSafeConfigurable):
    width = ProcessSafeConfigurableNumericProperty(default_value=640, value_type=int)
    height = ProcessSafeConfigurableNumericProperty(
        default_value=480, min_value=1, max_value=2000, value_type=int
    )


class Worker(mp.Process, ProcessSafeConfigurable):
    """Mimics ImageProvider: a long-running Process whose configuration
    must stay mutable from the parent after the child has already started.
    """

    width = ProcessSafeConfigurableNumericProperty(default_value=640, value_type=int)

    def __init__(self, result_queue):
        mp.Process.__init__(self)
        ProcessSafeConfigurable.__init__(self)
        self.result_queue = result_queue

    def run(self):
        for _ in range(10):
            self.result_queue.put(self.width)
            time.sleep(0.05)


class ProcessSafeConfigurableTestCase(envtest.CoreTestCase):
    def test000_defaults_populate_configuration(self) -> None:
        obj = SimpleConfigurable()
        self.assertEqual(obj.width, 640)
        self.assertEqual(obj.height, 480)
        self.assertEqual(obj.configuration["width"], 640)
        self.assertEqual(obj.configuration["height"], 480)

    def test010_set_via_attribute_updates_configuration_dict(self) -> None:
        obj = SimpleConfigurable()
        obj.width = 222
        self.assertEqual(obj.width, 222)
        self.assertEqual(obj.configuration["width"], 222)

    def test020_sanitize_clamps_out_of_range_values(self) -> None:
        """mytk's ConfigurableNumericProperty.sanitize() still runs: our
        descriptor only changes where the value is stored, not validation."""
        obj = SimpleConfigurable()
        obj.height = 999999
        self.assertEqual(obj.height, 2000)

    def test030_update_values_applies_multiple_properties(self) -> None:
        obj = SimpleConfigurable()
        obj.update_values({"width": 111, "height": 222})
        self.assertEqual(obj.width, 111)
        self.assertEqual(obj.height, 222)

    def test040_set_configuration_is_an_alias_for_update_values(self) -> None:
        obj = SimpleConfigurable()
        obj.set_configuration({"width": 333})
        self.assertEqual(obj.width, 333)

    def test050_configuration_is_backed_by_a_manager_dict(self) -> None:
        """The whole point of this module: configuration must be a real
        multiprocessing proxy, not a plain per-instance dict."""
        obj = SimpleConfigurable()
        self.assertIsInstance(obj.configuration, DictProxy)

    def test060_cross_process_update_is_visible_to_a_running_child(self) -> None:
        """A value set from the parent AFTER the child process has started
        must be visible to that child on its next read. Verified to fail
        with mytk's own Configurable (plain __dict__ storage) before this
        module existed."""
        q = mp.Queue()
        w = Worker(q)
        w.start()
        try:
            time.sleep(0.15)
            w.width = 222
            time.sleep(0.3)
        finally:
            w.terminate()
            w.join()

        seen = []
        while not q.empty():
            seen.append(q.get())

        self.assertIn(640, seen, "child never saw the initial default")
        self.assertIn(222, seen, "child never saw the parent's update")


if __name__ == "__main__":
    envtest.main()
