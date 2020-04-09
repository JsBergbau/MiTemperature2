#!/bin/bash

#This script is provided by Chiunownow https://github.com/Chiunownow
#Thank you very much for providing this script
#This script is 

#use e.g with that script: MySensor.sh 
#!/bin/bash
#DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
#$DIR/LYWSD03MMC.py -d <device> -b 1000 -r --debounce --skipidentical 50 --name MySensor --callback sendToMQTT

mosquitto_pub -h mqtt.host -t "MiTemperature2/$2/temp" -u mqtt.username -P mqtt.passwd -i "mibridge" -m "$3"
mosquitto_pub -h mqtt.host -t "MiTemperature2/$2/humidity" -u mqtt.username -P mqtt.passwd -i "mibridge" -m "$4"
mosquitto_pub -h mqtt.host -t "MiTemperature2/$2/batteryvoltage" -u mqtt.username -P mqtt.passwd -i "mibridge" -m "$5"
mosquitto_pub -h mqtt.host -t "MiTemperature2/$2/batterylevel" -u mqtt.username -P mqtt.passwd -i "mibridge" -m "$6"
