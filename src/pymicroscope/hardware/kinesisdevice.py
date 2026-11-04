from hardwarelibrary.physicaldevice import PhysicalDevice
from hardwarelibrary.motion.linearmotiondevice import LinearMotionDevice

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
        except Exception:
            return

    def doInitializeDevice(self):
        available_devices = kinesis.KinesisDevice.list_devices()
        available_serial_numbers = [ device[0] for device in available_devices]
        
        if self.serialNumber not in available_serial_numbers:
            raise RuntimeError("Kinesis Device with serial number {0} not found.".format(self.serialNumber))

        # Connect the right Kinesis Motor, open the port, set the channel and the reference position
        self.thorlabs_device = kinesis.KinesisMotor(conn=self.serialNumber)
        self.thorlabs_device.open()
        self.thorlabs_device.set_supported_channels(channels=self.channel)
        self.thorlabs_device.set_position_reference()  # set the initial point

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
        self.thorlabs_device.wait_move()

    def doMoveBy(self, displacement):
        self.thorlabs_device.move_by(distance=displacement[0])
        self.thorlabs_device.wait_move()

    def doHome(self):
        self.thorlabs_device.home(sync=True, force=True)
