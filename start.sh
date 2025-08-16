#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd $DIR

#uncomment following line to use in python virtual environment
source bin/activate

./MiTemperature2.py --watchdogtimer 5 #--mqttconfigfile mqtt.conf

