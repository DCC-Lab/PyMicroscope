from mytk import *
import math
from typing import Tuple, Optional
from hardwarelibrary.motion import SutterDevice


class SutterConfigDialog():
    def __init__(self):
        
        self.sutter_device = SutterDevice(serialNumber="debug")
        #self.sutter_device = SutterDevice()

        try:
            self.sutter_device.doInitializeDevice()
        except Exception as err:
            pass  # sutter_device.is_accessible == False

        if self.sutter_device is not None:  # we don't konw now
            Dialog.showerror(
                title="sutter controller is not connected or found",
                message="Check that the controller is connected to the computer",
            )
            self.position = self.sutter_device.doGetPosition()
            self.initial_x_value = self.position[0]
            self.initial_y_value = self.position[1]
            self.initial_z_value = self.position[2]
        else:
            self.initial_x_value = 0
            self.initial_y_value = 0
            self.initial_z_value = 0

        #valeur a accrocher
        self.z_image_number = 1
        self.microstep_pixel = int(0.16565)
        self.z_range = 1     

        self.parameters: dict[str, Optional[Tuple[int, int, int]]] = {
            "Upper left corner": None,
            "Upper right corner": None,
            "Lower left corner": None,
            "Lower right corner": None,
        }

        self.can_start_map = False

    def saving_position(self, corner):
        if self.sutter_device is not None:
            self.parameters[corner] = self.position
        else:
            raise ValueError("No position found")
    
    def clear(self):
        for p in self.parameters:
                self.parameters[p] = None

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
            x_pixels_value_per_image = int(1000)
            y_pixels_value_per_image = int(500)
            
            x_microstep_value_per_image = (
                x_pixels_value_per_image * self.microstep_pixel
            )
            y_microstep_value_per_image = (
                y_pixels_value_per_image * self.microstep_pixel
            )
            self.sutter_device.doMoveTo(self.parameters["Upper left corner"])
            self.sutter_device.doMoveBy(
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

            for z in range(self.z_image_number*self.z_range*self.microstep_pixel):
                self.sutter_device.doMoveBy((0, 0, 1))
                for y in range(number_of_y_pictures):
                    self.sutter_device.doMoveBy(
                        (
                            -x_microstep_value_per_image * number_of_x_pictures,
                            -y_microstep_value_per_image
                            + 0.1 * y_microstep_value_per_image,
                            0,
                        )
                    )  # for the moment, need a dy movement
                    """Take a picture"""
                    """Save"""
                    #microscope = MicroscopeApp()
                    #microscope.save()

                    for x in range(number_of_x_pictures):
                        self.sutter_device.doMoveBy(
                            (
                                x_microstep_value_per_image
                                - 0.1 * x_microstep_value_per_image,
                                0,
                                0,
                            )
                        )  # for the moment, need a dx movement
                        """Take a picture"""
                        """Save"""
                        #microscope.save()

        
        else:
            print("some parameter are None")
