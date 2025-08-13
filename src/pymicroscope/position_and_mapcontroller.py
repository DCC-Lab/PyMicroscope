from mytk import *
import math
from typing import Tuple, Optional
from typing import Any

class MapController(Bindable):
    '''Giving all the position to create a map of all the sample'''
    def __init__(self, device, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device = device

        self.z_image_number = 1
        self.microstep_pixel = 0.16565
        self.z_range = 1
        self.x_dimension = 1000
        self.y_dimension = 500

        self.parameters: dict[str, Optional[Tuple[int, int, int]]] = {
            "Upper left corner": None,
            "Upper right corner": None,
            "Lower left corner": None,
            "Lower right corner": None,
        }

    def create_positions_for_map(self):
        '''Giving all the deplacement position according to the x and y image dimension'''
        positions_list = []

        corner1 = self.parameters["Upper left corner"]
        corner2 = self.parameters["Upper right corner"]
        corner3 = self.parameters["Lower left corner"]
        corner4 = self.parameters["Lower right corner"]

        x_image_dimension = self.x_dimension*self.microstep_pixel
        y_image_dimension = self.y_dimension*self.microstep_pixel
        z_image_dimension = self.z_range*self.microstep_pixel

        if all(x != (0.0, 0.0, 0.0) for x in self.parameters.values()): 
            number_of_x_image = math.ceil((corner2[0] - corner1[0]) / (0.9*x_image_dimension))
            number_of_y_image = math.ceil((corner2[1] - corner4[1])/ (0.9*y_image_dimension))
        else:
             number_of_x_image = 1
             number_of_y_image = 1


        for z in range(self.z_image_number):
                z_position = z*z_image_dimension
                for y in range(number_of_y_image):
                    y_position = y*y_image_dimension*0.9
                    for x in range(number_of_x_image):
                        x_position = x*x_image_dimension*0.9
                        positions_list.append((x_position, y_position, z_position))

        
        return positions_list