""" Port USB """

import serial
import time

# Attendre un peu pour que le dispositif envoie des données
time.sleep(2)

info = serial.Serial('/dev/cu.wlan-debug', 9600, timeout=4) # /dev/cu.Bluetooth-Incoming-Port ou /dev/cu.wlan-debug

# Initialiser un tableau de bytes pour stocker les données
data = bytearray()
# Lire des données jusqu'à ce qu'une nouvelle ligne soit rencontrée
while True:
    byte = info.read()  # Lire un byte
    if byte:  # Vérifier si un byte a été lu
        data += byte  # Ajouter le byte au tableau de données
        if byte == b'\n':  # Vérifier si le byte est une nouvelle ligne
            break  # Sortir de la boucle si une nouvelle ligne est rencontrée
    else:
        print("Aucune donnée reçue.")
        break  # Sortir de la boucle si aucune donnée n'est reçue

# Convertir les données en chaîne de caractères
string = data.decode('utf-8')  # Utiliser decode() pour convertir en chaîne
print(string)  # Afficher la chaîne'''

info.close()

#sauver dans terminale: ls /dev/cu.* 