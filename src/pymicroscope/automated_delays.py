from hardwarelibrary.physicaldevice import *
from hardwarelibrary.motion.linearmotiondevice import *
from hardwarelibrary.communication.communicationport import *
from hardwarelibrary.communication.usbport import USBPort
from hardwarelibrary.communication.serialport import SerialPort
from hardwarelibrary.communication.commands import DataCommand
from hardwarelibrary.communication.debugport import DebugPort

import re
import time
from struct import *

from pyftdi.ftdi import Ftdi #FIXME: should not be here.
from mytk import *
from pylablib.devices.Thorlabs import kinesis
import numpy as np

class KinesisDevice(LinearMotionDevice):
    classIdVendor = 4930
    classIdProduct = 1

    def __init__(self, serialNumber: str = None):
        super().__init__(serialNumber=serialNumber, idVendor=self.classIdVendor, idProduct=self.classIdProduct)
        self.port = None
        self.nativeStepsPerMicrons = 16

        # All values are in native units (i.e. microsteps)
        self.xMinLimit = 0
        self.yMinLimit = 0
        self.zMinLimit = 0
        self.xMaxLimit = 25000*16
        self.yMaxLimit = 25000*16
        self.zMaxLimit = 25000*16

    def __del__(self):
        try:
            self.port.close()
        except:
            # ignore if already closed
            return

    def doInitializeDevice(self): 
        pass

    def doShutdownDevice(self):
        pass

    def sendCommandBytes(self, commandBytes):
        pass

    def readReply(self, size, format) -> tuple:
        pass

    def positionInMicrosteps(self) -> (int, int, int):  # for compatibility
        return self.doGetPosition()

    def doGetPosition(self) -> (int, int, int):
        
       
        return (x, y, z)

    def doMoveTo(self, position):
        pass

    def doMoveBy(self, displacement):
        pass

    def doHome(self):
        pass

#for eventully automated
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



