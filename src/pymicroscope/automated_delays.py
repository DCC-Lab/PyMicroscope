from mytk import *
from pylablib.devices.Thorlabs import kinesis
import numpy as np

class DelaysController():
    def __init__(self, device, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #initiation with thorlabs kinesis
        self.port = None

        #shut down

    def linear_relation_delays_and_wavelength(self, wavelength_value):
        delay_position = 285 + (-0.302)*wavelength_value     #for the moment
        return delay_position

    def intensity_comparaison(self):
        intensity_value = []
        max_intensity = 0
        intensity_value.append(self.pass'''valeur d'intensité en temps réel''')
        if self.'''intensity_value''' > intensity_value[-1]:
            max_intensity = intensity_value

        if max_intensity - self.'''intensity_value''' = '''écart max à déterminer''':
            self.port.stop
            self.port.'''retour en arrière'''



