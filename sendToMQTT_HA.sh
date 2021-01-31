#!/bin/bash

#This script is provided by Chiunownow https://github.com/Chiunownow
#Thank you very much for providing this script
#This script is 

#use e.g with that script: MySensor.sh 
#!/bin/bash
#DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
#$DIR/LYWSD03MMC.py -d <device> -b 1000 -r --debounce --skipidentical 50 --name MySensor --callback sendToMQTT

mosquitto_pub -h mqtt.host  -p 1883 -t "homeassistant/sensor/$2_temp/config" -u mqtt.username -P mqtt.passwd -i "mibridge" -m '{"device_class": "temperature", "name": "'$2'_temp", "unique_id": "lywsd03mmc_'$2'_temp", "device": { "name":"lywsd03mmc_'$2'", "identifiers": "lywsd03mmc_'$2'", "model": "LYWSD03MMC", "manufacturer": "Xiaomi"}, "state_topic": "homeassistant/sensor/'$2'/state", "unit_of_measurement": "°C", "value_template": "{{ value_json.temperature}}","platform": "mqtt" }'
mosquitto_pub -h mqtt.host  -p 1883 -t "homeassistant/sensor/$2_humi/config" -u mqtt.username -P mqtt.passwd -i "mibridge" -m '{"device_class": "humidity", "name": "'$2'_humi", "unique_id": "lywsd03mmc_'$2'_humi", "device": { "name":"lywsd03mmc_'$2'", "identifiers": "lywsd03mmc_'$2'", "model": "LYWSD03MMC", "manufacturer": "Xiaomi"}, "state_topic": "homeassistant/sensor/'$2'/state", "unit_of_measurement": "%", "value_template": "{{ value_json.humidity}}","platform": "mqtt" }'
mosquitto_pub -h mqtt.host  -p 1883 -t "homeassistant/sensor/$2_battlevel/config" -u mqtt.username -P mqtt.passwd -i "mibridge" -m '{"device_class": "battery", "name": "'$2'_batt", "unique_id": "lywsd03mmc_'$2'_batt", "device": { "name":"lywsd03mmc_'$2'", "identifiers": "lywsd03mmc_'$2'", "model": "LYWSD03MMC", "manufacturer": "Xiaomi"}, "state_topic": "homeassistant/sensor/'$2'/state", "unit_of_measurement": "%", "value_template": "{{ value_json.batterylevel}}","platform": "mqtt" }'
mosquitto_pub -h mqtt.host  -p 1883 -t "homeassistant/sensor/$2_battvolt/config" -u mqtt.username -P mqtt.passwd -i "mibridge" -m '{"device_class": "voltage", "name": "'$2'_volt", "unique_id": "lywsd03mmc_'$2'_volt", "device": { "name":"lywsd03mmc_'$2'", "identifiers": "lywsd03mmc_'$2'", "model": "LYWSD03MMC", "manufacturer": "Xiaomi"}, "state_topic": "homeassistant/sensor/'$2'/state", "unit_of_measurement": "v", "value_template": "{{ value_json.batteryvoltage}}","platform": "mqtt" }'
mosquitto_pub -h mqtt.host  -p 1883 -t "homeassistant/sensor/$2/state" -u mqtt.username -P mqtt.passwd -i "mibridge" -m '{ "temperature": '$3', "humidity": '$4', "batteryvoltage" : '$5', "batterylevel": '$6' }'

