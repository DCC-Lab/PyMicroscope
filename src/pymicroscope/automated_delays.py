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

class KinesisDevice(LinearMotionDevice):
    #SERIAL_NUMBER = "83849018"

    def __init__(self, serialNumber: str = None, channel: int = 1):
        super().__init__(serialNumber=serialNumber, idVendor=self.classIdVendor, idProduct=self.classIdProduct)
        self.port = None
        self.channel =channel
        self.encoder_steps = 34304

        # All values are in native units (i.e. microsteps)
        self.xMinLimit = 0
        self.xMaxLimit = 857599

    def __del__(self):
        try:
            self.port.close()
        except:
            # ignore if already closed
            return

    def doInitializeDevice(self):
        portPath = kinesis.KinesisDevice.list_devices()
        if portPath is None:
            raise PhysicalDevice.UnableToInitialize("No Thorlabs Device connected")
        if portPath[0] != "83------":
            raise PhysicalDevice.UnableToInitialize("No motor device found")
        
        self.port = kinesis.KinesisMotor(conn=self.serialNumber)
        self.port.open()
        self.port.set_supported_channels(channels= self.channel)
        self.port.set_position_reference() #set the initilal point

        if self.port is None:
            raise PhysicalDevice.UnableToInitialize("Cannot allocate port {0}".format(self.portPath))

    def doShutdownDevice(self):
        self.port.close()
        self.port = None

    def sendCommandBytes(self, commandBytes):
        if self.port is None:
            self.initializeDevice()
        
        time.sleep(0.1)
        self.port.send_comm(messageID=commandBytes)

    def sendCommandBytesData(self, commandBytes, data):
        if self.port is None:
            self.initializeDevice()
        
        time.sleep(0.1)
        self.port.send_comm_data(messageID=commandBytes, data=data)

    def readReply(self, size, format) -> tuple:
        pass

    def positionInMicrosteps(self) -> int:  # for compatibility
        return self.doGetPosition()/self.encoder_steps

    def doGetPosition(self) -> int:
        return self.port.get_position()

    def doMoveTo(self, position):
        '''Move to a position in microsteps'''
        encoder_position = self.encoder_steps*position
        self.port.move_to(position=encoder_position)
        if self.port.is_moving() is False:
            raise Exception("unable to move the device.")
        else:
            self.port.wait_move()

    def doMoveBy(self, displacement):
        encoder_displacement = self.encoder_steps*displacement
        self.port.move_by(position=encoder_displacement)
        if self.port.is_moving() is False:
                raise Exception("unable to move the device.")
        else:
            self.port.wait_move()

    def doHome(self):
        self.port.home()
        if self.port.is_homing() is False:
            raise Exception("unable to move the device to home.")
        else:
            self.port.wait_for_home()

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



