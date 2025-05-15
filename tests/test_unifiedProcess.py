import unittest
from multiprocessing import Queue
from queue import Empty, Full
from typing import Any, Optional
import time
import numpy as np
import logging
import envtest
from src.utils import UnifiedProcess
import sys

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override


class MockMainProcess(UnifiedProcess):
    def __init__(
        self, sleep_time: float = 0.2, *args: tuple[Any, ...], **kwargs: dict[str, Any]
    ):
        super().__init__(*args, **kwargs)
        self.queue = Queue(maxsize=3)
        self.sub_process = MockSubProcess(
            sleep_time=sleep_time, count=10, log_level=envtest.TEST_LOG_LEVEL
        )

    @override
    def run(self):
        with self.syncing_context() as must_terminate_now:
            try:
                counter = 0
                while not must_terminate_now:
                    try:
                        _ = self.sub_process.queue.get(timeout=1)
                        self.log.debug(f"Main process received image {counter}")
                        self.queue.put(1, block=False)
                        counter += 1
                        # time.sleep(0.1)
                    except Empty:
                        pass
                    except Full:
                        self.log.debug("Main process queue is full, discarding image")
            except Exception as err:  # pylint: disable=broad-exception-caught
                self.log.error("Unknown exception in MockMainProcess.run() : %s", err)
            finally:
                self.log.debug("MockMainProcess terminated")
                # self.sub_process.terminate_synchronously()

            self.log.debug("MockMainProcess ended")

    @override
    def start_synchronously(self):
        super().start_synchronously()
        self.sub_process.start_synchronously()

    @override
    def terminate_synchronously(self):
        self.sub_process.terminate_synchronously()
        super().terminate_synchronously()


class MockSubProcess(UnifiedProcess):
    def __init__(
        self,
        sleep_time: float = 0.2,
        count: int = 5,
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ):
        super().__init__(*args, **kwargs)
        self.queue = Queue(maxsize=3)
        self.count = count
        self.sleep_time = sleep_time

    def run(self):
        with self.syncing_context() as must_terminate_now:
            try:
                image = np.random.randint(0, 255, (1000, 1000, 1000), dtype=np.uint8)
                counter = 0
                while not must_terminate_now and counter < self.count:
                    try:
                        time.sleep(self.sleep_time)  # simulate camera capture time
                        self.new_images_captured(image)
                        self.log.debug(f"Sub process image {counter} sent")
                        counter += 1
                    except Full:
                        # Discard this image, continue loop
                        self.log.warning("Sub process queue is full, discarding image")
                        pass
            except Exception as err:  # pylint: disable=broad-exception-caught
                self.log.error("Unknown exception in SubProcess.run() : %s", err)
            finally:
                self.log.debug("Sub process terminated")

            self.log.debug("Sub process ended")

    def new_images_captured(self, image: np.ndarray) -> None:
        if image.shape != (1000, 1000, 1000):
            raise ValueError("Image shape is not correct")

        self.queue.put(image, block=True, timeout=0.1)


class TestUnifiedProcess(envtest.CoreTestCase):
    def setUp(self):
        super().setUp()
        self.main_process: Optional[MockMainProcess] = None
        self.sub_process: Optional[MockSubProcess] = None

    def tearDown(self):
        if self.main_process is not None and self.main_process.is_alive():
            self.main_process.terminate_synchronously()
        if self.sub_process is not None and self.sub_process.is_alive():
            self.sub_process.terminate_synchronously()

        super().tearDown()

    def test_start_stop_mock_process(self):
        self.main_process = MockMainProcess(log_level=envtest.TEST_LOG_LEVEL)
        self.main_process.start_synchronously()
        self.assertTrue(self.main_process.is_alive())
        time.sleep(5)
        self.main_process.terminate_synchronously()
        self.assertFalse(self.main_process.is_alive())

    def test_number_of_bursts_various_sleep_times(self):
        """Test burst collection for various sub process sleep_time values."""
        import time

        sleep_times = [0.01, 0.1, 0.2, 0.5, 1.0]
        for sleep_time in sleep_times:
            with self.subTest(sleep_time=sleep_time):
                self.main_process = MockMainProcess(
                    log_level=envtest.TEST_LOG_LEVEL, sleep_time=sleep_time
                )
                self.main_process.start_synchronously()
                self.assertTrue(self.main_process.is_alive())
                TIMEOUT = max(6, 2 + 5 * sleep_time)
                start_time = time.monotonic()
                count = 0
                while count < 5:
                    if time.monotonic() - start_time > TIMEOUT:
                        self.main_process.terminate_synchronously()
                        self.fail(
                            f"Timeout: Only {count} bursts received after {TIMEOUT} seconds with sleep_time={sleep_time}."
                        )
                    try:
                        _ = self.main_process.queue.get(timeout=1)
                        count += 1
                    except Empty:
                        pass
                self.assertEqual(
                    count, 5, f"Did not receive 5 bursts for sleep_time={sleep_time}"
                )
                self.main_process.terminate_synchronously()
                self.assertFalse(self.main_process.is_alive())


if __name__ == "__main__":
    # unittest.main(defaultTest=[
    #     # 'TestUnifiedProcess.test_start_stop_mock_process',
    #     'TestUnifiedProcess.test_number_of_bursts_various_sleep_times',
    #     ])

    unittest.main()
