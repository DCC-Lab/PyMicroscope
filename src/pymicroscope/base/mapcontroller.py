import math
from typing import Tuple, Optional

from mytk import Bindable


class MapController(Bindable):
    """Controls tiled image acquisition over a sample area.

    Manages four corner positions that define the sample region, and generates
    a grid of (x, y, z) capture positions with configurable overlap for
    stitched imaging and Z-stack acquisition.

    Coordinates are in microsteps. Use microstep_pixel to convert between
    pixel dimensions and physical stage positions.

    Args:
        device: The motion device used for positioning (e.g., SutterDevice).
    """

    def __init__(self, device, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device = device

        self.z_image_number = 1
        self.microstep_pixel = 0.16565
        self.z_range = 1
        self.x_dimension = 1000
        self.y_dimension = 500
        self.overlap_fraction = 0.1

        self.parameters: dict[str, Optional[Tuple[float, float, float]]] = {
            "Upper left corner": None,
            "Upper right corner": None,
            "Lower left corner": None,
            "Lower right corner": None,
        }

    @property
    def corners_are_set(self) -> bool:
        """True if all four corner positions have been defined."""
        return all(v is not None for v in self.parameters.values())

    def create_positions_for_map(self) -> list[Tuple[float, float, float]]:
        """Generate a list of (x, y, z) capture positions covering the sample area.

        If all four corners are set, the grid spans the region defined by the
        corners with overlap between adjacent tiles. Otherwise, a single
        position at the origin is returned.

        The overlap between adjacent images is controlled by overlap_fraction
        (default 0.1 = 10% overlap).

        Returns:
            List of (x, y, z) tuples in microstep coordinates.

        Raises:
            ValueError: If microstep_pixel is zero or negative.
        """
        if self.microstep_pixel <= 0:
            raise ValueError(f"microstep_pixel must be positive, got {self.microstep_pixel}")

        positions_list = []
        step_factor = 1.0 - self.overlap_fraction

        x_image_dimension = self.x_dimension * self.microstep_pixel
        y_image_dimension = self.y_dimension * self.microstep_pixel
        z_image_dimension = self.z_range * self.microstep_pixel

        if self.corners_are_set:
            upper_left = self.parameters["Upper left corner"]
            upper_right = self.parameters["Upper right corner"]
            lower_right = self.parameters["Lower right corner"]

            x_span = upper_right[0] - upper_left[0]
            y_span = upper_right[1] - lower_right[1]

            number_of_x_images = max(1, math.ceil(x_span / (step_factor * x_image_dimension)))
            number_of_y_images = max(1, math.ceil(y_span / (step_factor * y_image_dimension)))
        else:
            number_of_x_images = 1
            number_of_y_images = 1

        for z in range(self.z_image_number):
            z_position = z * z_image_dimension
            for y in range(number_of_y_images):
                y_position = y * y_image_dimension * step_factor
                for x in range(number_of_x_images):
                    x_position = x * x_image_dimension * step_factor
                    positions_list.append((x_position, y_position, z_position))

        return positions_list
