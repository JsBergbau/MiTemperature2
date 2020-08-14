#!/bin/bash

#This script is provided by Chiunownow https://github.com/Chiunownow
#Thank you very much for providing this script
#This script is 

#use e.g with that script: MySensor.sh 
#!/bin/bash
#DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
#$DIR/LYWSD03MMC.py -d <device> -b 1000 -r --debounce --skipidentical 50 --name MySensor --callback sendToMQTT

#echo "sendToMQTT: $1 sensor: $2 temp: $3 hum: $4 batt volt: $5 battery level: $6"

mosquitto_pub -h mqtt.host -t "MiTemperature2/$2/temp" -u mqtt.username -P mqtt.passwd -m "{\"temperature\": \"$3\", \"humidity\": \"$4\", \"batt\": \"$6\"}"
