from struct import *
from mytk import *


#for eventully automated
class DelaysController(Bindable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.port = None
        self.a_value = -0.302
        self.b_value = 285

    def linear_relation_delays_and_wavelength(self, wavelength_value):
        '''By the value setting at the interface, the linear relation delays and wavelength fonction return the delay position at a certain wavelenght'''
        delay_position = (self.a_value)*wavelength_value + self.b_value
        return delay_position

