"""
Unit tests for MapController.

Validates:
- Default initialization and properties
- Corner position management
- Grid position generation with and without corners
- Overlap fraction behavior
- Z-stack position generation
- Validation of microstep_pixel
"""

import envtest
from pymicroscope.base.mapcontroller import MapController


class MockDevice:
    """Minimal stand-in for a motion device."""
    pass


class MapControllerTestCase(envtest.CoreTestCase):

    def setUp(self):
        super().setUp()
        self.controller = MapController(device=MockDevice())

    def test000_init(self):
        self.assertIsNotNone(self.controller)
        self.assertIsNotNone(self.controller.device)

    def test010_default_values(self):
        self.assertEqual(self.controller.z_image_number, 1)
        self.assertAlmostEqual(self.controller.microstep_pixel, 0.16565)
        self.assertEqual(self.controller.z_range, 1)
        self.assertEqual(self.controller.x_dimension, 1000)
        self.assertEqual(self.controller.y_dimension, 500)
        self.assertAlmostEqual(self.controller.overlap_fraction, 0.1)

    def test020_corners_not_set_by_default(self):
        self.assertFalse(self.controller.corners_are_set)
        for corner in self.controller.parameters.values():
            self.assertIsNone(corner)

    def test030_corners_are_set_when_all_defined(self):
        self.controller.parameters["Upper left corner"] = (0, 0, 0)
        self.controller.parameters["Upper right corner"] = (100, 0, 0)
        self.controller.parameters["Lower left corner"] = (0, 100, 0)
        self.controller.parameters["Lower right corner"] = (100, 100, 0)
        self.assertTrue(self.controller.corners_are_set)

    def test040_corners_not_set_if_partial(self):
        self.controller.parameters["Upper left corner"] = (0, 0, 0)
        self.controller.parameters["Upper right corner"] = (100, 0, 0)
        self.assertFalse(self.controller.corners_are_set)

    def test050_single_position_without_corners(self):
        positions = self.controller.create_positions_for_map()
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0], (0, 0, 0))

    def test060_grid_positions_with_corners(self):
        self.controller.parameters["Upper left corner"] = (0.0, 200.0, 0.0)
        self.controller.parameters["Upper right corner"] = (500.0, 200.0, 0.0)
        self.controller.parameters["Lower left corner"] = (0.0, 0.0, 0.0)
        self.controller.parameters["Lower right corner"] = (500.0, 0.0, 0.0)

        positions = self.controller.create_positions_for_map()
        self.assertTrue(len(positions) > 1)

        # All positions should have 3 coordinates
        for pos in positions:
            self.assertEqual(len(pos), 3)

    def test070_z_stack_positions(self):
        self.controller.z_image_number = 3
        positions = self.controller.create_positions_for_map()
        self.assertEqual(len(positions), 3)

        # Z values should increase
        z_values = [p[2] for p in positions]
        self.assertEqual(z_values[0], 0)
        self.assertTrue(z_values[1] > z_values[0])
        self.assertTrue(z_values[2] > z_values[1])

    def test080_overlap_fraction_affects_spacing(self):
        self.controller.parameters["Upper left corner"] = (0.0, 100.0, 0.0)
        self.controller.parameters["Upper right corner"] = (500.0, 100.0, 0.0)
        self.controller.parameters["Lower left corner"] = (0.0, 0.0, 0.0)
        self.controller.parameters["Lower right corner"] = (500.0, 0.0, 0.0)

        self.controller.overlap_fraction = 0.1
        positions_10pct = self.controller.create_positions_for_map()

        self.controller.overlap_fraction = 0.5
        positions_50pct = self.controller.create_positions_for_map()

        # More overlap = more images needed to cover the same area
        self.assertTrue(len(positions_50pct) >= len(positions_10pct))

    def test090_zero_microstep_pixel_raises(self):
        self.controller.microstep_pixel = 0
        with self.assertRaises(ValueError):
            self.controller.create_positions_for_map()

    def test100_negative_microstep_pixel_raises(self):
        self.controller.microstep_pixel = -1.0
        with self.assertRaises(ValueError):
            self.controller.create_positions_for_map()

    def test110_positions_start_at_origin(self):
        """First position in any grid should be at the origin."""
        self.controller.parameters["Upper left corner"] = (0.0, 100.0, 0.0)
        self.controller.parameters["Upper right corner"] = (500.0, 100.0, 0.0)
        self.controller.parameters["Lower left corner"] = (0.0, 0.0, 0.0)
        self.controller.parameters["Lower right corner"] = (500.0, 0.0, 0.0)

        positions = self.controller.create_positions_for_map()
        self.assertEqual(positions[0], (0, 0, 0))


if __name__ == "__main__":
    envtest.main()
