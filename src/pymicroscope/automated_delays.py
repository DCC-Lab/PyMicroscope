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
        #self.encoder_steps = 34304
        #self.nativeStepsPerMicrons = 34304
        self.nativeStepsPerMicrons = 128


        # All values are in native units (i.e. microsteps)
        self.xMinLimit = 0
        self.xMaxLimit = 857599

        portPath = [(None, )] # if connected at a window pc, you can change the portPath
        #portPath = kinesis.KinesisDevice.list_devices()
        for port in portPath:
            if port[0] is None:
                PhysicalDevice.UnableToInitialize("No Thorlabs Device connected")
                pass
            if port[0] != serialNumber:
                PhysicalDevice.UnableToInitialize("Not the same serialNumber connected")
                pass
            else:
                self.initializeDevice()

    def __del__(self):
        try:
            self.port.close()
        except:
            # ignore if already closed
            return

    def doInitializeDevice(self):
        '''Connect the right Kinesis Motor, open the port, set the channel and the reference position'''
        self.port = kinesis.KinesisMotor(conn=self.serialNumber)
        if self.port is None:
            raise PhysicalDevice.UnableToInitialize("Cannot allocate port {0}".format(self.port))
        else:
            self.port.open()
            self.port.set_supported_channels(channels= self.channel)
            self.port.set_position_reference() #set the initilal point

    def doShutdownDevice(self):
        self.port.close()
        self.port = None

    def sendCommandBytes(self, commandBytes):
        """ The function to write a command to the endpoint. It will initialize the device 
        if it is not alread initialized. On failure, it will warn and shutdown."""
        if self.port is None:
            self.initializeDevice()
        
        time.sleep(0.1)
        self.port.send_comm(messageID=commandBytes)

    def sendCommandBytesData(self, commandBytes, data):
        """ The function to write a command with data value associated to the endpoint. It will initialize the device 
        if it is not alread initialized. On failure, it will warn and shutdown."""
        if self.port is None:
            self.initializeDevice()
        
        time.sleep(0.1)
        self.port.send_comm_data(messageID=commandBytes, data=data)

    def readReply(self, size, format) -> tuple:
        '''No reply fonction needing the size and format. Can be self.port.recv_comm(expected_id) with a expected_id, but this fonction is not necessare in our case.'''
        pass
    
    def positionInMicrosteps(self) -> int:  # for compatibility
        return self.doGetPosition() #/self.encoder_steps

    def doGetPosition(self) -> int:
        return self.port.get_position()

    def doMoveTo(self, position):
        '''Move to a position in microsteps'''
        #encoder_position = self.encoder_steps*position
        self.port.move_to(position=position[0])
        if self.port.is_moving() is False:
            raise Exception("unable to move the device.")
        else:
            self.port.wait_move()

    def doMoveBy(self, displacement):
        '''Move by a position in microsteps'''
        #encoder_displacement = self.encoder_steps*displacement
        self.port.move_by(distance=displacement[0])
        if self.port.is_moving() is False:
                raise Exception("unable to move the device.")
        else:
            self.port.wait_move()

    def doHome(self):
        '''Go to the initial position'''
        self.port.move_to(position=0)
        if self.port.is_moving() is False:
            raise Exception("unable to move the device to home.")
        else:
            self.port.wait_for_stop()

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

