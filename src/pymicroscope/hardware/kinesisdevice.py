from hardwarelibrary.physicaldevice import *
from hardwarelibrary.motion.linearmotiondevice import *
from hardwarelibrary.communication.communicationport import *
from hardwarelibrary.communication.usbport import USBPort
from hardwarelibrary.communication.serialport import SerialPort
from hardwarelibrary.communication.commands import DataCommand
from hardwarelibrary.communication.debugport import DebugPort

import time
from struct import *

from pyftdi.ftdi import Ftdi #FIXME: should not be here.
from mytk import *
from pylablib.devices.Thorlabs import kinesis

class KinesisDevice(LinearMotionDevice):
    #SERIAL_NUMBER = "83849018"

    def __init__(self, serialNumber: str = None, channel: int = 1):
        super().__init__(serialNumber=serialNumber, idVendor=self.classIdVendor, idProduct=self.classIdProduct)
        self.thorlabs_device = None
        self.channel =channel
        self.nativeStepsPerMicrons = 128


        # All values are in native units (i.e. microsteps)
        self.xMinLimit = 0
        self.xMaxLimit = 857599
        
    def __del__(self):
        try:
            self.thorlabs_device.close()
        except:
            return

    def doInitializeDevice(self):
        available_devices = kinesis.KinesisDevice.list_devices()
        available_serial_numbers = [ device[0] for device in available_devices]
        
        if self.serialNumber not in available_serial_numbers:
            raise RuntimeError("Kinesis Device with serial number {0} not found.".format(self.serialNumber))

        '''Connect the right Kinesis Motor, open the port, set the channel and the reference position'''
        self.thorlabs_device = kinesis.KinesisMotor(conn=self.serialNumber)
        if self.thorlabs_device is None:
            raise PhysicalDevice.UnableToInitialize("Cannot allocate port {0}".format(self.thorlabs_device))
        else:
            self.thorlabs_device.open()
            self.thorlabs_device.set_supported_channels(channels= self.channel)
            self.thorlabs_device.set_position_reference() #set the initilal point

    def doShutdownDevice(self):
        self.thorlabs_device.close()
        self.thorlabs_device = None
    
    def position(self) -> int:  # for 1D compatibility
        position_tuple = super().position()
        return position_tuple[0]

    def doGetPosition(self) -> tuple:
        return (self.thorlabs_device.get_position(),)

    def doMoveTo(self, position):
        self.thorlabs_device.move_to(position=position[0])
        if self.thorlabs_device.is_moving() is False:
            raise Exception("unable to move the device.")
        else:
            self.thorlabs_device.wait_move()

    def doMoveBy(self, displacement):
        self.thorlabs_device.move_by(distance=displacement[0])
        if self.thorlabs_device.is_moving() is False:
                raise Exception("unable to move the device.")
        else:
            self.thorlabs_device.wait_move()

    def doHome(self):
        self.thorlabs_device.move_to(position=0)
        if self.thorlabs_device.is_moving() is False:
            raise Exception("unable to move the device to home.")
        else:
            self.thorlabs_device.wait_for_stop()
