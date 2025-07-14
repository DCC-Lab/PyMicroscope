from mytk import *
import math


class SutterConfigDialog():
    def __init__(self, sutter_config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sutter_config = sutter_config
        self.sutter_device = self.sutter_config.sutter_device
        self.parameters = self.sutter_config.parameters
        self.z_image_number = self.sutter_config.z_image_number
        self.user_clicked_save = self.sutter_config.user_clicked_save

    def ajuste_map_imaging(self):
        if all(x is not None for x in self.parameters.values()):
            upper_left_corner = self.parameters["Upper left corner"]
            upper_right_corner = self.parameters["Upper right corner"]
            lower_left_corner = self.parameters["Lower left corner"]
            lower_right_corner = self.parameters["Lower right corner"]

            # ajuste image for making a square
            if upper_left_corner[1] > upper_right_corner[1]:
                ajusted_position = (
                    upper_left_corner[0],
                    upper_right_corner[1],
                    upper_left_corner[2],
                )
                self.parameters["Upper left corner"] = ajusted_position

            if upper_left_corner[1] < upper_right_corner[1]:
                ajusted_position = (
                    upper_right_corner[0],
                    upper_left_corner[1],
                    upper_right_corner[2],
                )
                self.parameters["Upper right corner"] = ajusted_position

            if upper_right_corner[0] > lower_right_corner[0]:
                ajusted_position = (
                    lower_right_corner[0],
                    upper_right_corner[1],
                    upper_right_corner[2],
                )
                self.parameters["Upper right corner"] = ajusted_position

            if upper_right_corner[0] < lower_right_corner[0]:
                ajusted_position = (
                    upper_right_corner[0],
                    lower_right_corner[1],
                    lower_right_corner[2],
                )
                self.parameters["Lower right corner"] = ajusted_position

            if lower_left_corner[1] > lower_right_corner[1]:
                ajusted_position = (
                    lower_left_corner[0],
                    lower_right_corner[1],
                    lower_left_corner[2],
                )
                self.parameters["Lower left corner"] = ajusted_position

            if lower_left_corner[1] < lower_right_corner[1]:
                ajusted_position = (
                    lower_right_corner[0],
                    lower_left_corner[1],
                    lower_right_corner[2],
                )
                self.parameters["Lower right corner"] = ajusted_position

            if upper_left_corner[0] > lower_left_corner[0]:
                ajusted_position = (
                    upper_left_corner[0],
                    lower_left_corner[1],
                    lower_left_corner[2],
                )
                self.parameters["Lower left corner"] = ajusted_position

            if upper_left_corner[0] < lower_left_corner[0]:
                ajusted_position = (
                    lower_left_corner[0],
                    upper_left_corner[1],
                    upper_left_corner[2],
                )
                self.parameters["Upper left corner"] = ajusted_position

            for parameter, z in self.parameters:
                z_values_comparaison = z[2]

                if len(set(z_values_comparaison)) != 1:
                    ajusted_position = (
                        z[0],
                        z[1],
                        max(z_values_comparaison),
                    )
                    self.parameters[parameter] = ajusted_position

        else:
            raise ValueError("Some initial parameters are missing")

            
    def aquisition_image(self):
        if all(x is not None for x in self.parameters.values()):
            self.ajuste_map_imaging()
            x_pixels_value_per_image = int(1000)
            y_pixels_value_per_image = int(500)
            microstep_pixel = int(0.16565)  # for a zoom 2x
            x_microstep_value_per_image = (
                x_pixels_value_per_image * microstep_pixel
            )
            y_microstep_value_per_image = (
                y_pixels_value_per_image * microstep_pixel
            )
            self.sutter_device.moveTo(self.parameters["Upper left corner"])
            self.sutter_device.moveBy(
                (
                    x_microstep_value_per_image * number_of_x_pictures,
                    y_microstep_value_per_image,
                    -1,
                )
            )
            # the initial value need to be upper because we start with a domoveby in the for boucle

            upper_left_corner = self.parameters["Upper left corner"]
            upper_right_corner = self.parameters["Upper right corner"]
            lower_right_corner = self.parameters["Lower right corner"]

            # a 10% ajustement between each image to match them
            number_of_x_pictures = math.ceil(
                (upper_right_corner[0] - upper_left_corner[0])
                / (
                    x_microstep_value_per_image
                    - 0.1 * x_microstep_value_per_image
                )
            )
            number_of_y_pictures = math.ceil(
                (upper_right_corner[1] - lower_right_corner[1])
                / (
                    y_microstep_value_per_image
                    - 0.1 * y_microstep_value_per_image
                )
            )

            for z in range(self.z_image_number):
                self.sutter_device.moveBy((0, 0, 1))
                for y in range(number_of_y_pictures):
                    self.sutter_device.moveBy(
                        (
                            -x_microstep_value_per_image * number_of_x_pictures,
                            -y_microstep_value_per_image
                            + 0.1 * y_microstep_value_per_image,
                            0,
                        )
                    )  # for the moment, need a dy movement
                    """Take a picture"""
                    """Save"""
                    self.user_clicked_save()

                    for x in range(number_of_x_pictures):
                        self.sutter_device.moveBy(
                            (
                                x_microstep_value_per_image
                                - 0.1 * x_microstep_value_per_image,
                                0,
                                0,
                            )
                        )  # for the moment, need a dx movement
                        """Take a picture"""
                        """Save"""
                        self.user_clicked_save()

        
        else:
            print("some parameter are None")
