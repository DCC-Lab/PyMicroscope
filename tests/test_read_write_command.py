""" Port USB """
import unittest
import serial
from serial.tools import list_ports

import time

port_path = '/dev/cu.wlan-debug'

class TestReadWrite(unittest.TestCase):
    def test000_init(self):
        self.assertTrue(True)

    def test005_list_ports(self):

        ports_list = serial.tools.list_ports.comports()
        self.assertIsNotNone(ports_list)

        ftdi_ports = []
        for port_info in ports_list:
            if port_info.vid == 1027:
                ftdi_ports.append(port_info)

        self.assertTrue(len(ftdi_ports) != 0)



        # print(f"FTDI Device:{port_info.device} vid:{port_info.vid} pid:{port_info.pid}")

    @unittest.SkipTest
    def test010_create_serial_port(self):
        port = serial.Serial(port_path, baudrate=19200, timeout=3, )
        self.assertIsNotNone(port)


if __name__ == "__main__":
    unittest.main()

# # Attendre un peu pour que le dispositif envoie des données
# time.sleep(2)

# info = serial.Serial('/dev/cu.wlan-debug', baudrate=19200, timeout=3, ) # /dev/cu.Bluetooth-Incoming-Port ou /dev/cu.wlan-debug

# # Initialiser un tableau de bytes pour stocker les données
# data = bytearray()
# # Lire des données jusqu'à ce qu'une nouvelle ligne soit rencontrée
# while True:
#     byte = info.read()  # Lire un byte
#     if byte:  # Vérifier si un byte a été lu
#         data += byte  # Ajouter le byte au tableau de données
#         if byte == b'\n':  # Vérifier si le byte est une nouvelle ligne
#             break  # Sortir de la boucle si une nouvelle ligne est rencontrée
#     else:
#         print("Aucune donnée reçue.")
#         break  # Sortir de la boucle si aucune donnée n'est reçue

# # Convertir les données en chaîne de caractères
# string = data.decode('utf-8')  # Utiliser decode() pour convertir en chaîne
# print(string)  # Afficher la chaîne'''

# info.close()

# #sauver dans terminale: ls /dev/cu.* 


