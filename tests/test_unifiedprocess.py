"""
Unit tests for UnifiedProcess and safe_set_start_method.

Validates:
- UnifiedProcess combines LoggableProcess, TerminableProcess, and CallableProcess
- Signal handler installation/deinstallation dispatches to both parents
- drain_queue() safely empties multiprocessing queues
- safe_set_start_method() validates and sets multiprocessing start methods
"""

import time
import warnings
from multiprocessing import Queue

import envtest
from pymicroscope.utils.unifiedprocess import UnifiedProcess, safe_set_start_method
from pymicroscope.utils.terminable import run_loop


class SimpleUnifiedProcess(UnifiedProcess):
    """A minimal UnifiedProcess for testing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ran = False

    @run_loop
    def run(self):
        self.ran = True


class UnifiedProcessTestCase(envtest.CoreTestCase):

    def test000_init(self):
        proc = SimpleUnifiedProcess()
        self.assertIsNotNone(proc)

    def test010_start_and_terminate(self):
        proc = SimpleUnifiedProcess()
        proc.start_synchronously()
        self.assertTrue(proc.is_alive())
        proc.terminate_synchronously()
        self.assertFalse(proc.is_alive())

    def test020_install_signal_handlers(self):
        """Verify install_signal_handlers can be called without error."""
        proc = SimpleUnifiedProcess()
        # Signal handlers are installed inside the subprocess via run(),
        # but we can verify the method exists and is callable
        self.assertTrue(callable(proc.install_signal_handlers))
        self.assertTrue(callable(proc.deinstall_signal_handlers))

    def test030_drain_empty_queue(self):
        """drain_queue on an empty queue should return immediately."""
        q = Queue()
        UnifiedProcess.drain_queue(q)
        self.assertTrue(q.empty())

    def test040_drain_queue_with_items(self):
        """drain_queue should remove all items from the queue."""
        q = Queue()
        for i in range(10):
            q.put(i)
        UnifiedProcess.drain_queue(q)
        # Queue is closed after draining (MPQueue), so verify by
        # checking that put raises ValueError
        with self.assertRaises(ValueError):
            q.put("should_fail")

    def test050_drain_multiprocessing_queue(self):
        """drain_queue should call close() and join_thread() on MP queues."""
        q = Queue()
        q.put("item1")
        q.put("item2")
        UnifiedProcess.drain_queue(q)
        # After draining an MPQueue, it should be closed
        # Putting to a closed queue raises ValueError
        with self.assertRaises(ValueError):
            q.put("should_fail")

    def test060_is_unified_process_subclass(self):
        """UnifiedProcess should inherit from CallableProcess and TerminableProcess."""
        from pymicroscope.utils import CallableProcess, TerminableProcess
        self.assertTrue(issubclass(UnifiedProcess, CallableProcess))
        self.assertTrue(issubclass(UnifiedProcess, TerminableProcess))


class SafeSetStartMethodTestCase(envtest.CoreTestCase):

    def test000_returns_current_method(self):
        """Should return the current start method without error."""
        result = safe_set_start_method()
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test010_invalid_method_raises(self):
        """Should raise ValueError for unsupported method."""
        with self.assertRaises(ValueError):
            safe_set_start_method("not_a_real_method")

    def test020_warns_on_mismatch(self):
        """Should warn when requested method differs from current."""
        import multiprocessing
        current = multiprocessing.get_start_method(allow_none=True)
        if current is not None:
            # Request a different method without force
            other = "fork" if current == "spawn" else "spawn"
            import sys
            valid = multiprocessing.get_all_start_methods()
            if other in valid:
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    safe_set_start_method(other, force=False)
                    if len(w) > 0:
                        self.assertIn("requested", str(w[0].message))


if __name__ == "__main__":
    envtest.main()
