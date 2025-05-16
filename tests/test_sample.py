from typing import Optional, Tuple, Any

import envtest  # setup environment for testing
from pymicroscope.sample import Sample


class SampleTestCase(envtest.CoreTestCase):
    def test000_init_provider(self) -> None:
        """
        Can I create Sample()
        """
        self.assertIsNotNone(Sample())

    def test010_sample_initialize(self):
        sample = Sample()
        sample.initialize()

    def test020_get_position(self):
        sample = Sample()
        position = sample.get_position()
        self.assertIsNotNone(position)
        self.assertTrue(isinstance(position, tuple))


if __name__ == "__main__":
    envtest.main()
