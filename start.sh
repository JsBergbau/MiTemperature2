#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd $DIR

#uncomment following line to use in python virtual environment
#source bin/activate

./LYWSD03MMC.py --passive --watchdogtimer 5 #--mqttconfigfile mqtt.conf


