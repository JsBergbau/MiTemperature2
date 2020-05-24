#!/usr/local/bin/python3.7m

import os
import re
import requests
import time
import sys

veraip = "192.168.1.39"
port = 3480
temperaturedeviceid = 769
humiditydeviceid = 772

# Quick and dirty script to send data to vera sensors
# sensorname=$2 temperature=$3,humidity=$4,calibratedHumidity=$5,batterylevel=$6 $7

temperature = sys.argv[3]  # change to sys.argv[5] for calibrated
humidity = sys.argv[4]
batterylevel = sys.argv[6]

# send temperature value
res = requests.get(
    "http://"
    + veraip
    + ":"
    + str(port)
    + "/data_request?id=variableset&DeviceNum="
    + str(temperaturedeviceid)
    + "&serviceId=urn:upnp-org:serviceId:TemperatureSensor1&Variable=CurrentTemperature&Value="
    + str(temperature)
)

# send timestamp
res = requests.get(
    "http://"
    + veraip
    + ":"
    + str(port)
    + "/data_request?id=variableset&DeviceNum="
    + str(temperaturedeviceid)
    + "&serviceId=urn:micasaverde-com:serviceId:HaDevice1&Variable=LastUpdate&Value="
    + str(int(time.time()))
)

# send humidity value
res = requests.get(
    "http://"
    + veraip
    + ":"
    + str(port)
    + "/data_request?id=variableset&DeviceNum="
    + str(humiditydeviceid)
    + "&serviceId=urn:micasaverde-com:serviceId:HumiditySensor1&Variable=CurrentLevel&Value="
    + str(humidity)
)

# change update timestamp
res = requests.get(
    "http://"
    + veraip
    + ":"
    + str(port)
    + "/data_request?id=variableset&DeviceNum="
    + str(humiditydeviceid)
    + "&serviceId=urn:micasaverde-com:serviceId:HaDevice1&Variable=LastUpdate&Value="
    + str(int(time.time()))
)

# send batterylevel to temp and humidity virtual sensors
res = requests.get(
    "http://"
    + veraip
    + ":"
    + str(port)
    + "/data_request?id=variableset&DeviceNum="
    + str(temperaturedeviceid)
    + "&serviceId=urn:micasaverde-com:serviceId:HaDevice1&Variable=BatteryLevel&Value="
    + str(batterylevel)
)
res = requests.get(
    "http://"
    + veraip
    + ":"
    + str(port)
    + "/data_request?id=variableset&DeviceNum="
    + str(humiditydeviceid)
    + "&serviceId=urn:micasaverde-com:serviceId:HaDevice1&Variable=BatteryLevel&Value="
    + str(batterylevel)
)
