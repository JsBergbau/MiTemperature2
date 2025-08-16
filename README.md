# Read data from Xiaomi Mijia LYWSD03MMC Bluetooth 4.2 Temperature Humidity sensor

With this script you can read out the data of your LYWSD03MMC (and some other) sensors, e.g. with Raspberry Pi. Note Raspbery Pi 4 has a very limited bluetooth range. Pi Zero W gives much longer range.


## Table of Contents

-   [Read data from Xiaomi Mijia LYWSD03MMC Bluetooth 4.2 Temperature Humidity sensor](#read-data-from-xiaomi-mijia-lywsd03mmc-bluetooth-42-temperature-humidity-sensor)
    -   [Table of Contents](#table-of-contents)
    -   [Supported sensors](#supported-sensors)
    -   [Prequisites / Requirements](#prequisites--requirements)
        -   [Requirements for reading sensors in passive
            mode](#requirements-for-reading-sensors-in-passive-mode)
    -   [Usage](#usage)
        -   [Passive Mode Usage](#passive-mode-usage)
    -   [Built in MQTT support](#built-in-mqtt-support)
    -   [Tips](#tips)
        -   [Minus degrees](#minus-degrees)
        -   [High battery usage (not applicable for recommended passive
            mode)](#high-battery-usage-not-applicable-for-recommended-passive-mode)
    -   [Sample output](#sample-output)
        -   [More info](#more-info)
        -   [Troubleshooting](#troubleshooting)
    -   [Calibration](#calibration)
        -   [Offset calibration](#offset-calibration)
        -   [Two point calibration](#two-point-calibration)
    -   [Docker usage](#docker-usage)
    -   [Callback for processing the
        data](#callback-for-processing-the-data)
    -   [Send metrics to Prometheus](#send-metrics-to-prometheus)
    -   [Node-RED flows](#node-red-flows)
    -   [Callback to Home-Assistant MQTT
        integration](#callback-to-home-assistant-mqtt-integration)
        -   [Home-Assistant device
            details:](#home-assistant-device-details)

## Important release information 6.0 and above

Passive mode is now standard, so commandline interface has changed. The new programm name is MiTemperature2.py
Old file LYWSD03MMC.py is still present, but not supported anymore.

requests module has been replaced by python-builtin urllib. This makes startup twice as fast on Raspberry PI Zero
There is a simple debugHTTPServer.py to see the HTTP-requests the httpcallback is sending.

## Supported sensors

This script was originally made to support LYWSD03MMC devices running Xiaomi firmware but support for other hardware and firmware was added later.

Passive mode (recommended) device support: LYWSD03MMC, MHO-C401, CGG1-M, CGGDK2, LYWSDCGQ

Normal (active connection) device support has been dropped since Version 6. You need now the pvvs Firmware. Get it here https://github.com/pvvx/ATC_MiThermometer

BTHome V2 pakets are since v6.0 also supported. When sensor sends packets in BT Home v2 Standard, there are different kinds of packets. One type containts Temperature and Humidity, the other only battery value. Temperature and battery packets are send more often. The missing values (temperature and humidity at battery packets and battery and voltage at temperature/humidity packages) are cached. Only when scripts starts and the cache is empty, the missing values are transmitted as 0. To prevent these packets beeing sent, use -bot switch (see below).

Qingping format advertisements are supported so it's possible this script also supports advertisements sent by other types of Qingping CGG* devices but this is not tested. CGG1-M (Mijia version) devices can also run custom ATC firmware by pvvx. Then they behave exactly the same as LYWSD03MMCs running custom firmware. Qingping sensors only send Qingping format advertisements when running the original Qingping firmware.

LYWSDCGQ format (the old round one with an aaa battery) is supported. The sensor can send four types of advertisements: 1) both temperature and humidity, 2) only temperature, 3) only humidity and 4) only battery. All of these are supported. The missing values are 0 for the callback, so this needs to be handled in the callback script implementation. There are roughly about 20 advertisements with both temperature and humidity per minute and about two single information advertisements per minute for each information, temperature, humidity and battery.

## Prequisites / Requirements

This is not needed if you are using the docker image. However this is often oudated See [Docker usage](#docker-usage)

You need Python3 3.7 or above, which should be easily feasible nowadays.

Using venv (recommended)
```sudo apt install python3-venv
mkdir MiTemperature2 && cd MiTemperature2
sudo apt-get install python3-bluez libbluetooth-dev
sudo setcap cap_net_raw,cap_net_admin+eip $(eval readlink -f `which python3`)
python3 -m venv --system-site-packages .
source bin/activate
pip install 'paho-mqtt<2.0.0' pycryptodomex
```

Instead of `pip` it may be `pip3`, depeding of your installation.

If you don't want to use systemwide package `python3-bluez` You can install it then with `pip3 install git+https://github.com/pybluez/pybluez.git#egg=pybluez` in your venv source https://stackoverflow.com/a/75820681

Bluetooth LE Scanning needs root. To run the script with normal user rights, please execute
```
sudo setcap cap_net_raw,cap_net_admin+eip $(eval readlink -f `which python3`)
```
When using python virtual environment do this in your venv.    
    
After a Python upgrade, you have to redo the above step.

## Usage

```
---------------------------------------------
MiTemperature2 / ATC Thermometer version 6.0
---------------------------------------------


Please read README.md in this folder. Latest version is available at https://github.com/JsBergbau/MiTemperature2#readme
This file explains very detailed about the usage and covers everything you need to know as user.


usage: MiTemperature2.py [-h] [--interface N] [--mqttconfigfile MQTTCONFIGFILE] [--round] [--callback CALLBACK] [--httpcallback HTTPCALLBACK]
                         [--skipidentical N] [--callback-interval CALLBACK_INTERVAL] [--influxdb N] [--battery ] [--rssi] [--watchdogtimer X]
                         [--devicelistfile DEVICELISTFILE] [--onlydevicelist] [--bthome-onlyfull-transmit]

optional arguments:
  -h, --help            show this help message and exit
  --interface N, -i N   Specifiy the interface number to use, e.g. 1 for hci1
  --mqttconfigfile MQTTCONFIGFILE, -mcf MQTTCONFIGFILE
                        specify a configurationfile for MQTT-Broker

Rounding and debouncing:
  --round, -r           Round temperature to one decimal place and humidity to whole numbers)

Callback related arguments:
  --callback CALLBACK, -call CALLBACK
                        Pass the path to a program/script that will be called on each new measurement
  --httpcallback HTTPCALLBACK, -http HTTPCALLBACK
                        Pass the URL to a program/script that will be called on each new measurement
  --skipidentical N, -skip N
                        N consecutive identical measurements won't be reported to callbackfunction
  --callback-interval CALLBACK_INTERVAL, -int CALLBACK_INTERVAL
                        Only invoke callbackfunction every N seconds, e.g. 600 = 10 minutes
  --influxdb N, -infl N
                        Optimize for writing data to influxdb,1 timestamp optimization, 2 integer optimization
  --battery [], -b []   Pass the battery level to callback
  --rssi, -rs           Report RSSI via callback

Additional options:
  --watchdogtimer X, -wdt X
                        Re-enable scanning after not receiving any BLE packet after X seconds
  --devicelistfile DEVICELISTFILE, -df DEVICELISTFILE
                        Specify a device list file giving further details to devices
  --onlydevicelist, -odl
                        Only read devices which are in the device list file
  --bthome-onlyfull-transmit, -bot
                        Begin transmit BTHome data only, when both packet types (battery and temperature) have been received

Please read README.md in this folder. Latest version is available at https://github.com/JsBergbau/MiTemperature2#readme This file explains very detailed
about the usage and covers everything you need to know as user.

```

Note: When using rounding option you could see 0.1 degrees more in the script output than shown on the display. Obviously the LYWSD03MMC just truncates the second decimal place.


With the `--interface` option you specify the number of the bluetooth adapter to use. So `--interface 1` for using hci1.

With `--influxdb 1` you can use a influxdb optimized output. In this mode a timestamp with the current data is sent every 10 seconds to influxdb. Or technically speaking, each received measurement is snapped to a grid of 10 seconds. Don't use this feature together with `--skipidentical` otherwise it won't help. To use RLE compression for timestamps influxdb requires all 1000 timestamps which are mostly in a block to have the same interval. Only one missing timestamp leads to s8b compression for timestamps. Since influxdb handles identical values very efficiently you save much more space by writing every 10 seconds instead of skipping identical values. Without RLE 1000 timestamps needed about 1129 Bytes of data in my measurement. With RLE its only 12 Byte. Of course there are now more measurements stored in influxdb, but still overall size in influxdb is still lower. Depends also environment, of course. With a very steady environment and very seldom writing identical valus then size in influxdb would be smaller not writing every 10 seconds, of course. Integer optimizsation `--influxdb 2`is not implemented yet. `--influx 2` would shape the values as described here as "Bonobo-Timeseries-Data-Compression" https://github.com/JsBergbau/Bonobo-Timeseries-Data-Compression

    
### Startup script start.sh
    
There is a startup script `start.sh`. You can configure your prefered options there. It is highly recommended using this, since, as planned, in 6.0 release MiTemperature2.py is now the main program.
    
### Passive Mode Usage

Since 6.0 this is the only supported mode.

Thanks to https://github.com/atc1441/ATC_MiThermometer and https://github.com/pvvx/ATC_MiThermometer there is an alternative firmware which sends out the measurements as Bluetooth Low Energy Advertisements. In this mode you don't have to connect to the sensor. This saves a lot of power, especially in cases where the signal strength is low, see https://github.com/JsBergbau/MiTemperature2/issues/32.
I've also noticed a higher range. In addition you can have multiple receivers, see Node-RED section https://github.com/JsBergbau/MiTemperature2#node-red-flows.

For longer batterylife and higher stability passive mode is recommended. In the flasher Webpage selecting only `Atc1441` as Advertising type is recommended. You can than increase the Advertising interval to save power for sensors with good reception. For sensors with weaker reception I would keep the default of 2500 ms. You could even increase it for sensors with very bad reception. 

Since version 4.0 custom format advertisements as introduced by pvvx are also supported. This type gives 2 decimal places for temperature and humidity. The reading of the flags field is currently not supported. If you need support, please open an issue.

Since version 5.0 Qingping format advertisements are supported. These are sent by various Qingping sensors when they are set to this specific mode of operation by adding the sensors to the Qingping+ app. After this they will start sending (unencrypted) Qingping advertisements. Some of these sensors can also be set to Mijia (or other) modes but support for this is untested. Qingping format advertisements do not include the voltage of the battery, the battery percentage includes one decimal and the humidity is an integer value without decimals. This is a bit different from other formats but still quite workable for keeping a history of measurements.

Since version 6.0 BTHome V2 pakets are also supported. For limitations of BTHome V2 format, see [Supported sensors].

In passive mode the script listens for BLE advertisements. So you need to start only one instance of this script and it reads out all your sensors. You can have multiple receivers and thus have a kind of cell network and your sensors are portable in a quite wide range. Use it optimally with influxdb and `--influxdb 1`. With this option timestamps are snapped to 10s and since influxdb only stores one value for one timestamp you won't have duplicate data in your database.

ATC firmware gives temperature only with one decimal place, so rounding and debouncing options are not available. This is no real disadavantage because accuracy is impaired because of a lacking capciator, see https://github.com/pvvx/ATC_MiThermometer/issues/11#issuecomment-766776468.

`--watchdogtimer X` sometimes your device leaves BLE scanning mode, then you won't receive any data anymore. To avoid this after X seconds without receiving any BLE packets (not only from ATC sensors) BLE scanning mode is re-enabled. If you have configured your sensor to advertise new data every 10 seconds, I recommend a setting of 5 seconds, so `--watchdogtimer 5`. On a Raspberry Pi Zero W polling 10 sensors (2 are currently unreachable) this re-enabling BLE scan can happen a few times per minute. When polling 8 reachable sensors it happens less frequent but still at least once or twice a minute. 

One note about new advertising data: The ATC firmware sends out the data about every 2.5 seconds. After 10 seconds (4 advertising periods) it advertises new data and to detect this, it increases the packet counter. Only the values of first packet of this series with the same packetcounter is displayed and reported by callback, since the data in one series is identical.

`--devicelistfile <filename>` Use this option to give your sensors a name/alias. This file can also be on a network drive. So you can keep it up to date on a single place for multiple receivers. Also in this file is space for calibration data and you can give each device it's own MQTT topic. Note: The file is only read once at script startup. If you make changes to the file, you need to restart the script for them to take effect.

Note: ATC/pvvx firmware shows other humidity values than the stock Xiaomi firmware, so you have to re-calibrate your sensors. ATC/pvvx seems to be much more accurate. I don't calibrate new sensors anymore. The temperature value is unchanged compared to the Xiaomi sensor firmware.

An example is given in the sensors.ini file in this repository. It is quite self explaining

```ini
[info]
info1=now all available options are listet. If offset1, offset2, calpoint1 and calpoint2 are given 2Point calibration is used instead of humidityOffset.
info2= Note options are case sensitive
;info4=Use semicolon to comment out lines
sensorname=Specify an easy readable name
humidityOffset=-5
offset1 = -10
offset2 = 10
calpoint1 = 33
calpoint2 = 75
topic=This sensor data will be published with this name when using integrated MQTT
;If no topic is given, then default topic from MQTT config is used
decryption = For encrypted sensor give the key preceded by k. It is advised to use an individual key for every sensor. Please also set a PIN to prevent adversary from connecting and reading key.
;example for key
;decryption = k9088F9B4F7EC3BB52378F8F31CB74073

;[A4:C1:38:DD:EE:FF]
; sensorname=Bathroom
; humidityOffset=-30
; offset1 = -10
; offset2 = -10
; calpoint1 = 33
; calpoint2 = 75
; topic = basement/Bathroom

[A4:C1:38:1F:4D:81]
sensorname=Living Room
offset1 = -2
offset2 = 2
calpoint1 = 33
calpoint2 = 75
topic=basement/Living_Room
decryption = k9088F9B4F7EC3BB52378F8F31CB74073
```

`--onlydevicelist` Use this option to read only the data from sensors which are in your device list. This is quite useful if you have some spare sensors and you don't want your database get flooded with this data.

`--rssi` Reports the RSSI via callback

`--battery` Reports the battery level via callback.

Hint for storing the data in influx: 
When you have configured an advertisement interval of 10 seconds: Ideally store one measurement every 25 seconds to use very efficient RLE compression for your measurements. With storing the data every 25s, almost every timestamp is stored. This leads to RLE compression of the timestamp thus saving a lot of space in influxdb. With an interval of 20 seconds in tests it occured quite often, that timestamp slots were not filled and thus no RLE compression can be used. 

Passive mode uses advertisement scanning for saving battery life of the sensors. Read more about this here https://github.com/JsBergbau/MiTemperature2/issues/41#issuecomment-735361200

#### Encrypted Passive Mode

Beginning with v4 of the script encrypted passive mode is supported. You have to use a devicelist file, option `--devicelistfile` and add an entry for every sensor and its key. 

To use this mode, copy or set a new 32 char hexadecimal key (see example ini, note the preceding `k` is only in ini file) by pressing "Show all mi keys" in Telink Flasher and in case of setting a new one pressing button "Set new Token & Bind keys". 
At "Advertising type" uncheck "AdFlags" and check "Encrypted beacon" for shortest encrypted packet length. When "Atc1441" is chosen, packet length is really minimal, however temperature is only reported in 0.5 °C steps. You can also choose "Custom" format, this will report 2 decimal places for temperature and humidity. When using `--round` option, temperature and humidity are rounded to one decimal place.

**Remember to set PinCode**. Without Pincode an adversary can connect and copy your encryption key. He can even lock you out by setting a pincode. If you like to disable Pincode again, enter `000000`, so 6 zeros in a row.

**No voltage output, only battery level**: Encrypted passive mode does not report any battery voltage, only battery level is transmitted. Thus voltage is always `0` in encrypted passive mode. When not using integrated MQTT, use `--battery` to report battery level via callback. 



## Built in MQTT support

Since Version 3 of MiTemperature2 there is built in support for MQTT. Especially if you receive a lot of sensors executing a callback for each measurement is quite expensive. For a raspberry Pi Zero W for example with a few sensors I have an average CPU usage of 35 %, after using built in MQTT support only about 10 % CPU is used on average and there are also other services running. Quite a lot performance measurements were made to keep CPU usage for MQTT transmit low. 

With callback every single message spawns a new process, a new TCP connection is established and then closed again. With integrated MQTT support one connection is opened at startup and then maintained all the time, saving a lot of CPU cycles and network overhead. 

A testscript was made and tested on a raspberry Pi4 booted with opion `force_turbo = 1`. With that option CPU runs always at 1500 MHz so measurements are easier to compare. Because `perf stat` wouldn't report the used CPU cycles measurement was taken via `time` command. 2000 generated values were sent and the time measured. With callback to Node-RED using curl time was about 77 seconds. Using mosquitto_pub and the same JSON string time was about 42. So mosquitto_pub and MQTT is a lot faster and efficient than using HTTP via curl. Then finally 2000 values were sent via integrated MQTT support. This took about 2 seconds whereas most of that time was required to import all libraries and so on. Transmitting 10.000 values via integrated MQTT only took about 4 seconds. So there is a massive performance plus with integrated MQTT.

Data is transmitted that way (but can be changed to subtopic mode, see below):
```json
{
  "temperature": 12.5,
  "humidity": 58,
  "voltage": 2.882,
  "calibratedHumidity": 57,
  "battery": 75,
  "timestamp": 1619805618,
  "sensor": "Living Room",
  "rssi": -88,
  "receiver": "raspberrypi"
}
```
or when you don't use a device list file then in sensorname there is the mac address of the sensor. For encrypted mode voltage is always 0, see above.

If you don't have provided any calibration data calibratedHumidity is the humidity value. So you can always use calibratedHumidity as the humidity value.

These JSON messages are all send via MQTT QOS 1. So if connection to your broker gets lost, data isn't lost. Because it contains the timestamp you won't lose one single value. Currently the implementation of the used library has a max message queue of 65555. So when having 10 thermometers and each transmitting every 10 seconds a new value this makes one message per second, so your broker can be unreachable for about 18 hours bevore you will lose messages. If you have a scenario where 65555 messages are too few and data could be lost, please open an issue and I'll try to find a solution. 

Important: To also not lose any message on the MQTT receiver, please also set QOS Level 1 and a client ID and disable clean-session flag. This way your MQTT broker stores all messages until your receiver is available again. Mosquitto stores default 1000 messages maximum per client with unlimited total size. You can change this via `max_queued_messages` see https://mosquitto.org/man/mosquitto-conf-5.html
In the Node-RED sample flow (see below) the settings are setup this way.

The example mqtt.conf file looks like

```ini
;For configuration options please see DEFAULT section below and https://github.com/JsBergbau/MiTemperature2/blob/master/README.md
[MQTT]
broker=127.0.0.1
port=1883
topic=ATCThermometer
;username=
;password=
receivername=
;subtopics=temperature,humidity

;Enable TLS / MQTTS
tls=0
;CA file
cacerts=isrgrootx1.pem
;Certificate file
certificate=
;Certificate key file
certificate_key=
;Enable TLS insecure mode
insecure=0

[DEFAULT]
;Do not change here, leave it as it is
broker=127.0.0.1
username=
password=
port=1883
topic=ATCThermometer
;lastwill message
lastwill=
;lastwill topic
lwt=
clientid=
;If not specified, hostname is used as receivername
receivername=
;enable subtopics like temperature and humidity, combine with comma without spaces so "temperature,humidity"
;to disable JSON output, add "nojson"
;subtopics=nojson,temperature,humidity will send temperature and humidity
subtopics=
```

broker, username, password and port are self-explaining. In addition TLS / MQTTS section should be easy to understand. Also lastwill and lastwill topic (lwt) can be easily understood.

Topic is the default topic under which data of all thermometers is published. You can override this per sensor, see above in the sensors.ini configuration. This default topic is the same as in the Node-RED flow example to receive all thermometers at one place.

If you need seperate readings like `sensors/basement/kitchen/temperature` and `sensors/basement/kitchen/humidity` you can use the `subtopics` option. So if you need voltage, temperature and humidity, subtopics option would look like `subtopics=temperature,voltage,humidity` and it would be published under 
``` 
ATCThermometer/temperature
ATCThermometer/voltage
ATCThermometer/humidity
``` 
or when you have specified a topic for your particular sensor like `basement/livingroom/` then it would like
``` 
basement/livingroom/temperature
basement/livingroom/voltage
basement/livingroom/humidity
``` 
When using subtopics options you should configure a topic for each sensor otherwise values would get mixed under topic `ATCThermometer/temperature`, of course.


Still there is also the JSON output at topic `ATCThermometer` respectively `basement/livingroom` 
To disable JSON output in this case, append nojson to suptopics, so in this case `subtopics=temperature,voltage,humidity,nojson`

Since the values transmitted as subtopics contain no timestamp, it makes no sense to cache them in case of a transmission failure. So these subtopic values are only sent as MQTT QOS level 0.

From a point of efficiency subtopics are less efficient because each subtopic needs a seperate transmission with its own overhead. So please use this feature only when really needed like with software like Homie that doesn't support JSON format.


## Tips

Use `sudo hcitool lescan --duplicate` to get the MAC of your sensor. Or use nRF Connect for Mobile https://play.google.com/store/apps/details?id=no.nordicsemi.android.mcp You can set a filter like -50dBm RSSI and get very close to your sensor. That's an easy way to get the MAC.

### Minus degrees

When looking at the specifications this LYWSD03MMC Sensor is specified from 0 °C to 60 °C. The LYWSDCGQ (the Bluetooth Temperatur sensor with the round display and an AAA battery) is specified from -9.9. 
I can confirm the LYWSD03MMC also goes down to -9.9 °C. At colder temperatures it only shows an "L". But even at lower temperatures the correct temperature is still sent! So you even could use ist to watch the temperature in your freezer which is a lot below -9.9 °C. However batterylife may be significantly reduced at those low temperatures.


## Sample output

```
 ./MiTemperature2.py --mqttconfigfile mqtt.conf
---------------------------------------------
MiTemperature2 / ATC Thermometer version 6.0
---------------------------------------------


Please read README.md in this folder. Latest version is available at https://github.com/JsBergbau/MiTemperature2#readme
This file explains very detailed about the usage and covers everything you need to know as user.


Script started
------------------------------
All devices within reach are read out, unless a devicelistfile and --onlydevicelist is specified.
In this mode debouncing is not available. Rounding option will round humidity and temperature to one decimal place.
Passive mode usually requires root rights. If you want to use it with normal user rights,
please execute "sudo setcap cap_net_raw,cap_net_admin+eip $(eval readlink -f `which python3`)"
You have to redo this step if you upgrade your python version.
----------------------------
Power ON bluetooth device 0
Bluetooth device 0 is already enabled
Enable LE scan
scan params: interval=1280.000ms window=1280.000ms own_bdaddr=public whitelist=no
socket filter set to ptype=HCI_EVENT_PKT event=LE_META_EVENT
Listening ...
BLE packet - ATC1441: AA:BB:CC:A1 00 1110161a18aabbcca100ea402f0a46a7 -58
Temperature:  23.4
Humidity:  64
Battery voltage: 2.63 V
RSSI: -58 dBm
Battery: 47 %

BLE packet - ATC1441: AA:BB:CC:A2 00 1110161a18aabbcca200e141450b09fe -48
Temperature:  22.5
Humidity:  65
Battery voltage: 2.825 V
RSSI: -48 dBm
Battery: 69 %

MQTT connected with result code 0
MQTT published, Client: <paho.mqtt.client.Client object at 0xb5c2acb8>  Userdata: None  mid: 1
MQTT published, Client: <paho.mqtt.client.Client object at 0xb5c2acb8>  Userdata: None  mid: 2
BLE packet - Custom: AA:BB:CC:A3 00 1602010612161a18a3ccbbaa520965180a0b594c04 -65
Temperature:  23.86
Humidity:  62.45
Battery voltage: 2.826 V
RSSI: -65 dBm
Battery: 89 %

MQTT published, Client: <paho.mqtt.client.Client object at 0xb5c2acb8>  Userdata: None  mid: 3
BLE packet - Custom: AA:BB:CC:A4 00 1312161a18a4ccbbaa4509b2188a0b537704 -70
Temperature:  23.73
Humidity:  63.22
Battery voltage: 2.954 V
RSSI: -70 dBm
Battery: 83 %

MQTT published, Client: <paho.mqtt.client.Client object at 0xb5c2acb8>  Userdata: None  mid: 4
BLE packet - ATC1441: AA:BB:CC:A5 00 1110161a18aabbcca5010c351e09a6dd -46
Temperature:  26.8
Humidity:  53
Battery voltage: 2.47 V
RSSI: -46 dBm
Battery: 30 %

BLE packet - ATC1441: AA:BB:CC:A6 00 1110161a18aabbcca600eb3e2a0a18f9 -45
Temperature:  23.5
Humidity:  62
Battery voltage: 2.584 V
RSSI: -45 dBm
Battery: 42 %

MQTT published, Client: <paho.mqtt.client.Client object at 0xb5c2acb8>  Userdata: None  mid: 5
MQTT published, Client: <paho.mqtt.client.Client object at 0xb5c2acb8>  Userdata: None  mid: 6
BLE packet - BTHome : AA:BB:CC:A7 00 120201060e16d2fc4000cf015b020109031419 -62
Packet type: Data
Temperature:  23.05
Humidity:  64.2
Battery voltage: 0 V
RSSI: -62 dBm
Battery: 0 %

```



### More info

This section remains for historical reasons. It was used in connect mode.

If you like gatttool you can use it, too. However it didn't notice when BT connection was lost, while this Python-Script automatically reestablishes the connection.

```
gatttool -I
connect AA:BB:CC:DD:EE:FF
#enable notifications
char-write-req 0x0038 0100
#enable lower power mode, please don't do when you want to interact with the device, because often then connection gets lost
char-write-req 0x0046 f40100
#Read battery-Level, just for reference, since it is always 99 consider: note value is in Hex format
char-read-hnd 0x001b
```

Strictly speaking enabling notifications every time is not necessary since the device remembers it between connects. However to make it always work, the Python-Script enables them upon every connection establishment.

Notification format
`Notification handle = 0x0036 value: f8 07 4a d6 0b`
f8 07 is the temperature as signed INT16 in little endian format. Divide it by 100 to get the temperature in degree Celsius
4a is the humidity. Only integer output :(
d6 and 0b are the battery voltage in Millivolts in little endian format.

Lower power mode: To safe power the connection interval is reduced. For more details, please see this Issue https://github.com/JsBergbau/MiTemperature2/issues/18#issuecomment-590986874

There can be done a lot more with that sensor. It stores highest and lowest values at hour level, has an integrated realtime clock and a few things more like changing the values for the comfort icon on the display. Credits go to jaggil who investigated on this and documented it well. You find the results here https://github.com/JsBergbau/MiTemperature2/issues/1 Just search for jaggil.

### Troubleshooting 

#### Connecting with Telink Flasher

With pvvx Telink Flasher https://pvvx.github.io/ATC_MiThermometer/TelinkMiFlasher.html you can flash the latest custom firmware.
If you have problems connecting to the device or connection interrupts, please read this https://github.com/pvvx/ATC_MiThermometer/issues/11#issuecomment-766776468
Xiaomi saved approximately one cent per device by waiving a capacitor. 
When applying settings to device and settings page is not showing up shortly after, then settings were lost and you have to begin again. 
So if this happens, try a new battery. But even new, cheap batteries, sometimes show this behaviour. So take another one and when settings are made you can use that battery again. It will still last a long time. 

## Calibration

Note: If you have calibrated your sensors and flash ATC firmware, you have to calibrate them again. With pvvx firmware sensors are quite accurate. I don't calibrate new ones anymore.

Especially humidity value is often not very accurate. You get better results if you calibrate against a known humidity. This can be done very easy with common salt (NaCl). Make a saturated solution and put it together with the Xiaomi Bluetooth thermometer in an airtight box. Ensure that no (salt) water gets in contact with the device. Saltwater is very corrosive.
Wait about 24 - 48 hours with a constant temperature. You should now have about 75 % relative humidity. I don't know how long it takes for the sensors to drift. So I will redo this procedure about every year. 

A quite constant temperature while calibration is very important, because with temperature also humidity changes and it takes some time for the system to rebalance the humidity. In my experiments at 20 °C room temperature it took about 48 hours, until humidity readings were quite stable and didn't change anymore. So give it time. If you take the sensors out of calibration humidity too early, they haven't reached the final value yet.

### Offset calibration

E.g. mine shows 79 % RH when actually there is 75 %. Set in the sensors.ini file for your sensor `humidityOffset=-4` to substract 4 from the readout value.

### Two point calibration

The offset is not linear over the whole humidity values, see https://www.rotronic.com/media/productattachments/files/c/a/capacitive_humidity_sensor_final.pdf Page 2.

>Linearity Errors. The typical response of a relative humidity capacitive sensor (between 0 and 100 percent RH) is not linear. Depending on the correction made by the electronic circuits, the instrument may have a linearity error.

So you should calibrate at another point. MagnesiumChloride is recommended as giving about 33% RH at 20 °C. Please use very pure MgCl. It is also sold as bath salt and stuff like that. For high accuracy please use a purity > 99 %.

Also Calciumchloride is suitable, but the humidity depends more on temperature. Be sure to have 20 °C. https://www.salzwiki.de/index.php/Deliqueszenzfeuchte
CaCl is often found in these small non-electric dehumidifiers which you can refill with refill packs.

My Xiaomi Bluetooth thermometer shows 39% RH at 33% RH. So wie here have an offset of 6.

Example: A hygrometer shows 70 % at 75% RH and 39% RH at 33% RH. So offset +6 at 75% RH and offset -6 at 33% RH.
Example for the Xiaomi to use 2 point calibration:
At 75% RH you have to substract 4 from the readout value, at 33% RH you have to substract 6.

Note the values in between are interpolated linear and the result is rounded to the nearest whole number. It makes no sense to give floatingpoint number when the input is none.

In sensors.ini use

```
offset1 = -6
offset2 = 5
calpoint1 = 33
calpoint2 = 75
```

## Docker usage
There is a docker image available on dockerhub you can use. See https://docs.docker.com/engine/install/debian/ for instructions on how to install docker on raspberry pi.   
Once this is installed, you can create a sensors.ini and mqtt.conf file on the host machine and use this to run the container using the these files
```
docker run --net=host --privileged -it -v $(pwd)/sensors.ini:/app/sensors.ini -v $(pwd)/mqtt.conf:/app/mqtt.conf  antxxxx/mitemperature2 -a --devicelistfile /app/sensors.ini --mqttconfigfile /app/mqtt.conf
```

## Callback for processing the data

Via the --callback option a script can be passed to sent the data to.
Example
`./MiTemperature2.py --callback sendToFile.sh`
If you don't give the sensor a name, the MAC-Address is used. The callback script must be within the same folder as this script.
The values outputted depends on the options like calibration or battery. So the format is printed in the first argument.
Example callback

```
#!/bin/bash
# This is quite useful for testing
echo $@ >> data.txt
exit 0
```

Gives in data.txt `sensorname,temperature,humidity,voltage,timestamp A4:C1:38:AA:BB:CC 24.63 61.14 2.819 1755374953`
To have a sensorsorname, instead of MAC-Adresse, you need sensors.ini file.

Whereas the timestamp is in the Unix timestamp format in UTC (seconds since 1.1.1970 00:00).

Via the --httpcallback option a formatted URL can be passed to sent the data to.
Example
`./MiTemperature2.py --httpcallback "http://127.0.0.1:8080/myscript?name={sensorname}&temp={temperature}&hum={humidity}&bat={batteryLevel}"`

This will call the script at the given URL and fill in the formatted values. Just like the built in MQTT support this is less expensive than executing a script via the --callback option every time a measurement is received. Supported values are: sensorname, temperature, humidity, voltage, humidityCalibrated, batteryLevel, rssi, timestamp.

There is a simple python HTTP-Server included, where you can check your callback parameters. You can execute it via `./debugHTTPServer.py`

There is an option not to report identical data to the callback. To distinguish between a failure and constantly the same values are read, the option takes the number after which identical measurements the data is reportet to the callback. Use the `--skipidentical N` for this. E.g. `--skipidentical 1` means 1 identical measurement is skipped, so only every second identical measurement is reportet to callback. I recommend numbers between 10 and 50, giving at least every minute respectively 5 minutes a call to the callback script (With 10 and 50 the actual time is slightly higher than 1 respectively 5 minutes). It is recommended to use the `--round` option, otherwise there is a lot of noise with changing the temperature. See https://github.com/JsBergbau/MiTemperature2/issues/2
  
Another option to reduce the number of callbacks is the use of the `--callback-interval N` parameter. Using callback functions on low end hardware (e.g. a Raspberry Pi Zero) can cause high cpu usages. This parameter limits the number of invoked callbacks. When you set this to 600, the callback function will not be invoked within 600 seconds from the previous callback.

All data received from the sensor is stored in a list and transmitted sequentially. This means if your backend like influxdb or httpcallback-target is not reachable when a new measurement is received, it will be tried again later (currently waiting 5 seconds before the next try). Thus no data is lost when your storage engine has some trouble. There is no upper limit (the only limit should be the RAM). Keep this in mind when specifing a wrong backend.

"sendToInflux.sh" is an example script for sending the data to influxdb via http-API. Precision was set to the level of seconds. This gives better compression ratios in influxdb.

## Send metrics to Prometheus

[Read instruction about integration with Prometheus Push Gateway](./prometheus/README.md)

## Send metrics to Zabbix

[Read instruction about integration with Zabbix](sendToZabbix.README.md)

## Node-RED flows
Finally there are flows for Node-RED. Especially if you have multiple receivers this is quite comfortable to manage the name and calibration data of your sensors at one place in Node-Red. No need to change configuration in any of your receivers. Note: If you use encrypted mode you need to provide the decryption key in a device list file on every receiver. Tip: Use Ansible to deploy updated lists on all receivers.

This solution makes it also very easy to have multiple receivers and you can easily move the devices around between them. As long as one device reaches one receiver everything will work. If it reaches multiple receivers you can even reboot one by one without data loss.

There are two slightly different versions. `Node-RED flows Callback mode.json` sends directly via curl and HTTP the data to Node-RED. This version is only intended when you don't have a MQTT broker.

`Node-RED flows MQTT mode.json` is the more efficient version because it is intended to be used with the integraded MQTT support and obviously a MQTT broker.

To use MiTemperature2 script with Node-RED import the flows from one of these files.

With that flow you can even start the script in ATC-Mode via Node-RED. If you are user `pi` and in your home directory, clone this Repo via `git clone https://github.com/JsBergbau/MiTemperature2`, make `MiTemperature2.py` executable (also `./sendToNodeRed.sh` when using callback version) and the preconfigured path to MiTemperature2 script doesn't have to be changed.

The Node-RED flow is documented with comments for easy usage. If theres missing some information, just open an issue and I'll have a look.

For easily switching between filtering in Node-Red or directly in the MiTemperature2 script, there are two scripts included.
``` ./iniToJSON.py -h
usage: iniToJSON.py [-h] --readfile filename [--writefile filename]

optional arguments:
  -h, --help            show this help message and exit
  --readfile filename, -rf filename
                        Specify filename of ini-File to convert
  --writefile filename, -wf filename
                        Specify filename of json-File to convert
```
Use these to convert between ini and JSON for usage in Node-RED.

```./jsonToIni.py -h
usage: jsonToIni.py [-h] --readfile filename --writefile filename

optional arguments:
  -h, --help            show this help message and exit
  --readfile filename, -rf filename
                        Specify filename of json-File to convert
  --writefile filename, -wf filename
                        Specify filename of json-File to convert
```


## Callback to Home-Assistant MQTT integration
Before using this callback script, please check if it is possible to do the same with integrated MQTT support.

etpedro https://github.com/etpedro has added a sendToMQTT_HA callback script that sends the data to an MQTT server and leverages Home-Assistant MQTT Autodiscovery creating a device for each sensor under MQTT integration. Each device has 4 entities: temperature, humidity, battery percentage and battery voltage.

Replace each variable according to your environment:

`mqtt.host` - MQTT Host

`mqtt.username` - MQTT Username

`mqtt.passwd`- MQTT Password


### Home-Assistant device details:


| Configuration | Value                    |
| ------------- | ------------------------ |
|name           | lywsd03mmc_"device_name" |
|identifiers    | lywsd03mmc_"device_name" |
|model          | LYWSD03MMC               |
|manufacturer   | Xiaomi                   |
