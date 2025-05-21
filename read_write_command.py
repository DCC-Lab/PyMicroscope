""" Port USB """

import serial
import time

# Attendre un peu pour que le dispositif envoie des données
time.sleep(2)

info = serial.Serial('/dev/cu.wlan-debug', timeout=4)

byte = info.read()  # Lire un byte

if byte:  # Vérifier si un byte a été lu
     print(byte)  # Afficher le byte lu
else:
    print("Aucune donnée reçue.")

#line = info.read()
#print(line)

info.close()