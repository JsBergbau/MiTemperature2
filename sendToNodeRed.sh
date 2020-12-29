#!/bin/bash

#use e.g with that script: MySensor.sh 
#!/bin/bash
#DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
#$DIR/LYWSD03MMC.py --atc --watchdogtimer 5 --callback sendToNodeRed.sh

if [[ "$1" == *"rssi"* ]]
then
	curl -s -i -XPOST http://192.168.178.21:1880/MiTemperature2Input -H "Content-Type: application/json" --data "{\"sensor\": \"$2\", \"temperature\" : $3 , \"humidity\" : $4 , \"voltage\" :$5, \"rssi\" : $6, \"timestamp\": $7 }"
else
	curl -s -i -XPOST http://192.168.178.21:1880/MiTemperature2Input -H "Content-Type: application/json" --data "{\"sensor\": \"$2\", \"temperature\" : $3 , \"humidity\" : $4 , \"voltage\" :$5, \"timestamp\": $6 }"
fi
