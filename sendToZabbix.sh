#!/bin/bash

# Zabbix Server or Proxy Address
zabbix_address=127.0.0.1
item_key=LYWSD03MMC.callback

host=$2
temp=$3
hum=$4
bat_vol=$5
bat_lvl=$6

echo $host $item_key "Temperature: $temp; Humidity: $hum; Battery voltage: $bat_vol V; Battery level: $bat_lvl" | zabbix_sender -z $zabbix_address -r -i -
