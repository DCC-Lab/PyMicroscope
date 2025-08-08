from mytk import *
import math
from typing import Tuple, Optional
from typing import Any

class MapController(Bindable):
    def __init__(self, device, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device = device

        # z_image_number = 1
        # microstep_pixel = 0.16565
        # z_range = 1

        self.parameters: dict[str, Optional[Tuple[int, int, int]]] = {
            "Upper left corner": None,
            "Upper right corner": None,
            "Lower left corner": None,
            "Lower right corner": None,
        }

    def create_positions_for_map(self, z_image_number: int = 1, microstep_pixel: float = 0.16565, z_range: int = 1) -> list[Tuple[int, int, int]]:
        ## Faire le calcul pour vrai avec corner1m cprner2 corner3 corbner4...
        # Utiliser self.parameters and self.z_imageNUmber, self.micvrostep......
        positions_list = []

        corner1 = self.parameters["Upper left corner"]
        corner2 = self.parameters["Upper right corner"]
        corner3 = self.parameters["Lower left corner"]
        corner4 = self.parameters["Lower right corner"]
        #print(corner1, corner2, corner3, corner4)

        x_image_dimension = 1000*microstep_pixel
        y_image_dimension = 500*microstep_pixel
        z_image_dimension = z_range*microstep_pixel

        if all(x != (0.0, 0.0, 0.0) for x in self.parameters.values()): 
            number_of_x_image = math.ceil((corner2[0] - corner1[0]) / (0.9*x_image_dimension))
            number_of_y_image = math.ceil((corner2[1] - corner4[1])/ (0.9*y_image_dimension))
        else:
             number_of_x_image = 1
             number_of_y_image = 1


        for z in range(z_image_number):
                z_position = z*z_image_dimension
                for y in range(number_of_y_image):
                    y_position = y*y_image_dimension*0.9
                    for x in range(number_of_x_image):
                        x_position = x*x_image_dimension*0.9
                        positions_list.append((x_position, y_position, z_position))

        
        # return positions_list
        
        return [(10, 0, 0), (100, 0, 0), (0, 100, 0), (100, 100, 0)]

    # def ajuste_map_imaging(self):
    #     if all(x is not None for x in self.parameters.values()):
    #         upper_left_corner = self.parameters["Upper left corner"]
    #         upper_right_corner = self.parameters["Upper right corner"]
    #         lower_left_corner = self.parameters["Lower left corner"]
    #         lower_right_corner = self.parameters["Lower right corner"]

    #         # ajuste image for making a square
    #         if upper_left_corner[1] > upper_right_corner[1]:
    #             ajusted_position = (
    #                 upper_left_corner[0],
    #                 upper_right_corner[1],
    #                 upper_left_corner[2],
    #             )
    #             self.parameters["Upper left corner"] = ajusted_position

    #         if upper_left_corner[1] < upper_right_corner[1]:
    #             ajusted_position = (
    #                 upper_right_corner[0],
    #                 upper_left_corner[1],
    #                 upper_right_corner[2],
    #             )
    #             self.parameters["Upper right corner"] = ajusted_position

    #         if upper_right_corner[0] > lower_right_corner[0]:
    #             ajusted_position = (
    #                 lower_right_corner[0],
    #                 upper_right_corner[1],
    #                 upper_right_corner[2],
    #             )
    #             self.parameters["Upper right corner"] = ajusted_position

    #         if upper_right_corner[0] < lower_right_corner[0]:
    #             ajusted_position = (
    #                 upper_right_corner[0],
    #                 lower_right_corner[1],
    #                 lower_right_corner[2],
    #             )
    #             self.parameters["Lower right corner"] = ajusted_position

    #         if lower_left_corner[1] > lower_right_corner[1]:
    #             ajusted_position = (
    #                 lower_left_corner[0],
    #                 lower_right_corner[1],
    #                 lower_left_corner[2],
    #             )
    #             self.parameters["Lower left corner"] = ajusted_position

    #         if lower_left_corner[1] < lower_right_corner[1]:
    #             ajusted_position = (
    #                 lower_right_corner[0],
    #                 lower_left_corner[1],
    #                 lower_right_corner[2],
    #             )
    #             self.parameters["Lower right corner"] = ajusted_position

    #         if upper_left_corner[0] > lower_left_corner[0]:
    #             ajusted_position = (
    #                 upper_left_corner[0],
    #                 lower_left_corner[1],
    #                 lower_left_corner[2],
    #             )
    #             self.parameters["Lower left corner"] = ajusted_position

    #         if upper_left_corner[0] < lower_left_corner[0]:
    #             ajusted_position = (
    #                 lower_left_corner[0],
    #                 upper_left_corner[1],
    #                 upper_left_corner[2],
    #             )
    #             self.parameters["Upper left corner"] = ajusted_position

    #         for parameter, z in self.parameters:
    #             z_values_comparaison = z[2]

    #             if len(set(z_values_comparaison)) != 1:
    #                 ajusted_position = (
    #                     z[0],
    #                     z[1],
    #                     max(z_values_comparaison),
    #                 )
    #                 self.parameters[parameter] = ajusted_position

    #     else:
    #         raise ValueError("Some initial parameters are missing")