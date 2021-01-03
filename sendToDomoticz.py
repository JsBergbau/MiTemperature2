#!/usr/bin/python3

import os
import re
import requests
import time
import sys

domoticzserver = "192.168.1.36"
idx_temp = "52"
#idx_temp = sys.argv[2] #uncomment this line for ATC Mode. You have to configure the sensorname to your domoticz idx, for details please see https://github.com/JsBergbau/MiTemperature2/issues/59

val_temp = sys.argv[3]  # change to sys.argv[5] for calibrated
val_hum = sys.argv[4]
val_bat = sys.argv[6]

val_comfort = "0"
if float(val_hum) < 40:
    val_comfort = "2"
elif float(val_hum) <= 70:
    val_comfort = "1"
elif float(val_hum) > 70:
    val_comfort = "3"

res = requests.get(
    "http://"
    + domoticzserver
    + "/json.htm?type=command&param=udevice&idx="
    + idx_temp
    + "&nvalue=0&svalue="
    + val_temp
    + ";"
    + val_hum
    + ";"
    + val_comfort
    + "&battery="
    + val_bat
)

