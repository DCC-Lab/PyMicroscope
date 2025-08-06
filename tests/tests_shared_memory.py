import unittest
import time
import numpy as np
from multiprocessing import RLock, shared_memory, Process


class TestController(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.lock = RLock()

    def tearDown(self):
        super().tearDown()

    def test000_create(self):
        shm_name = "image-shared-memory"
        shm = shared_memory.SharedMemory(
            create=True, size=10_000_000, name=shm_name
        )
        self.assertIsNotNone(shm)
        shm.unlink()

    def test010_process(self):
        lock = RLock()

        proc1 = Process(target=self.process1, args=(lock,))
        proc1.start()
        time.sleep(0.5)
        proc2 = Process(target=self.process2, args=(lock,))
        proc2.start()
        proc1.join()
        proc2.join()

    @staticmethod
    def process1(lock):
        start_time = time.time()

        shm_name = "image-shared-memory"
        shm = shared_memory.SharedMemory(
            create=True, size=10_000, name=shm_name
        )
        array = np.ndarray((10, 10), dtype=np.uint8, buffer=shm.buf)
        while time.time() - start_time < 5:
            noise = np.random.randint(0, 256, (10, 10), dtype=np.uint8)
            with lock:
                array[:] = noise

        shm.unlink()

    @staticmethod
    def process2(lock):
        shm_name = "image-shared-memory"
        shm = shared_memory.SharedMemory(name=shm_name)
        array = np.ndarray((10, 10), dtype=np.uint8, buffer=shm.buf)
        start_time = time.time()
        while time.time() - start_time < 4.5:
            with lock:
                print(array[0])


if __name__ == "__main__":
    unittest.main()
