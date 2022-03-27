# Callback - sendToZabbix.sh 

## Configuration
Script uses default values if no configuration file was found.
Options:

| Option | Default | Comments  |
|---|---|---|
| ZBX_ADDRESS | localhost | Zabbix Server/Proxy IP/FQDN |
| ZBX_PORT | 10051 | Zabbix Server/Proxy Port |
| TLS_CONNECT |  | TLS Settings - currently only **psk** supported<br />if this option exists, all other PSK Options also needed |
| TLS_PSK_IDENTITY |  | PSK identity name which is used in Zabbix |
| TLS_PSK_FILE |  | Path to PSK key file<br />The file may only contain the psk secret/password. See *zabbix_sender --help*  |

### Example sendToZabbix.conf

	ZBX_ADDRESS=zbx.domain.tld
	ZBX_PORT=10051
	TLS_CONNECT=psk
	TLS_PSK_IDENTITY=MiTemperature2
	TLS_PSK_FILE=sendToZabbix.psk

## Zabbix Template
sendToZabbix.sh uses the sensor name as host name in Zabbix. If there is no devicelistfile defined the MAC address is used as host name. But Zabbix don't allow ':' in host names. So the script strip them out.
Sensor Name "aa:bb:cc:dd:ee:ff" is changed to "**aabbccddeeff**". 

[YAML Export of Template](sendToZabbix.template.yaml)

### Items

* Sensor - Battery - Level
* Sensor - Battery - Voltage
* Sensor - Humidity
* Sensor - Temperature

### Triggers

* based on Item values
 * Battery level < {$BATTERY_LEVEL_MIN}%
* based on nodata()
  * Missing data - battery level
  * Missing data - battery voltage
  * Missing data - humidity
  * Missing data - temperature

#### Macros are defined on template level
* {$BATTERY_LEVEL_MIN} - 20
* {$NODATA_DELAY} - 900
  * context sensitive macros possible like 
    * {$NODATA_DELAY:battery_level}
    * {$NODATA_DELAY:battery_voltage}
    * {$NODATA_DELAY:humidity}
    * {$NODATA_DELAY:temperature}

### Graphs

* Temperature & Humidity
  * Temperature as Line with axis on the left
  * Humidity as filled region with axis on the right
