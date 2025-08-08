import unittest
from mytk import *
from pylablib.devices import Thorlabs
from pylablib.devices.Thorlabs import kinesis
import numpy as np
import serial
from serial.tools import list_ports

SERIAL_NUMBER = "83849018"
class TestDelais(unittest.TestCase):
    def setUp(self):
        #self.port = kinesis.KinesisDevice(conn=SERIAL_NUMBER)
        self.port = kinesis.KinesisMotor(conn=SERIAL_NUMBER)
        
    def tearDown(self):
        self.port.close()
        
    @unittest.SkipTest
    def test001_list_kinesis_device(self):
        list = kinesis.list_kinesis_devices()[0]
        print(list)
        print(list[0])
        information = kinesis.BasicKinesisDevice(list[0])
        print(information)

    @unittest.SkipTest
    def test002_get_information(self):
        print(self.port)
        self.assertTrue(self.port)
        #self.port._home()
        print(self.port.get_position(channel=[1]))
        #print(self.port._get_position())
        #self.port._move_by()
        #print(self.port._get_position())
        #setting = self.port.get_settings() #ensemble des paramètre setté pour les longueurs d'onde
        #print(setting)
        info = self.port.get_full_info()
        print(info)
        home_param = self.port.get_homing_parameters(channel=[1])
        #home_param = self.port._get_homing_parameters()
        print(home_param)
        limit_param = self.port.get_limit_switch_parameters()
        #limit_param = self.port._get_limit_switch_parameters()
        print(limit_param)

        #veloc_param = self.port._get_velocity_parameters(channel=[1])
        veloc_param = self.port.get_velocity_parameters(channel=[1])
        print(veloc_param)

        #jog_param = self.port._get_jog_parameters(channel=[1])
        jog_param = self.port.get_jog_parameters(channel=[1])
        print(jog_param)

        #movebeat_param = self.port._get_gen_move_parameters(channel=[1])
        movebeat_param = self.port.get_gen_move_parameters(channel=[1])
        print(movebeat_param)

    @unittest.SkipTest
    def test003_send_comm(self):
        #self.port.set_device_variable(key="associate_variable", value=3000) #pas réussi
        self.port.send_comm_data(messageID=0x0448, data="4000", source=0x02) #bouge d'une distance de.. vers l'avant ps: pas de négatif!!
        #self.port.send_comm_data(messageID=0x0453, data="2000") # va à la position nommé
        print(self.port._get_position(channel=[1]))
        #pas de stop point au jogging/ bien setter les paramètres initiales comme le point 0
       #pour une valeur data = 2000 la position est de 12333


    @unittest.SkipTest
    def test004_move_the_delais(self):
        position1 = self.port._get_position(channel=[1])
        print(position1)
        self.port._move_to(position=10, channel=[1])
        position2 = self.port._get_position(channel=[1])
        print(position2)
        self.port._move_to(position=10000, channel=[1])
        position3 = self.port._get_position(channel=[1])
        print(position3)
        #conclusion: les commande vont plus vite que le déplacement du délais. Il faut dont utiliser send_commande pour pouvoir faire un wait_move ou autre

    @unittest.SkipTest
    def test005_home_movement(self):
        self.port.home()
        home_position = self.port.get_position(channel=[1])
        #self.port.wait_for_home(channel=[1])
        print(home_position)

    @unittest.SkipTest
    def test006_complet_preparation_mouvement(self):
        self.port.move_to(position=900000, channel=[1], scale=True)
        #self.port.move_by(distance=-100, channel=[1]) # les moins pour reculer
        does_move = self.port.is_moving(channel=[1])
        self.assertTrue(does_move)
        self.port.wait_move(channel=[1])
        print(self.port.get_position(channel=[1]))

    #@unittest.SkipTest
    def test007_fixe_position(self):
        print(self.port.get_position(channel=[1]))

    @unittest.SkipTest #pas nécessaire ne fonctionne pas
    def test008_setup_point_initial(self):
        self.port.set_position_reference()

    #max distance [857599]mm
    


if __name__ == "__main__":
    unittest.main()