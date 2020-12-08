# Read data from Xiaomi Mijia LYWSD03MMC Bluetooth 4.2 Temperature Humidity sensor

With this script you can read out the value of your LYWSD03MMC sensor, e.g. with Raspberry PI. Note Raspbery Pi 4 has a very limited bluetooth range. PI Zero W gives much longer range.

This sensor doesn't transmit its values in the advertisment data, like the LYWSDCGQ Bluetooth thermometer. This is more privacy friendly since no one can sniff your temperature readings. On the other side this means you have to establish a bluetooth connection with the device to get the data. When you're connected no other connection is accepted, meaning if you hold the connection no other can readout your temperature and humidity.

Once you're connected the LYWSD03MMC it advertises its values about every 6 seconds, so about 10 temperature/humidity readings per minute.

## Prequisites / Requirements

You need Python3 3.7 or above because of the dataclasses used in the Callback Function. If you don't have Python 3.7 please take the previous version from here https://raw.githubusercontent.com/JsBergbau/MiTemperature2/5d7b215d7b22d4c21d9244f8a4102513b928f2c7/LYWSD03MMC.py This version is a bit behind and connection error handling has a bug. If you really need this script, please open and issue and I'll post a new bugfree version.

For example Raspbian Stretch has only Python 3.5.3. If you like to upgrade your Distribution to current Buster release follow this Tutorial https://pimylifeup.com/upgrade-raspbian-stretch-to-raspbian-buster/ If doing so: Omit the rpi-update step.

If you like installing/compiling Python3.7 please take a look at this tutorial https://gist.github.com/SeppPenner/6a5a30ebc8f79936fa136c524417761d However it took about 5 hours to compile/run the regressiontests on a Raspberry PI3B. I use this compiled version directly without install. If you do, too, you have to change the first line in the script, pointing to your compiled Python version. For bluepy you can copy the bluepy-folder from home/pi/.local/lib/python3.7/site-packages/bluepy to <yourPath>Python-3.7.4/Lib and do a chmod +x bluepy-helper in <yourPath>Python-3.7.4/Lib/bluepy

Prequisites: python3 bluez python3-pip bluepy
install via

`sudo apt install python3 bluez python3-pip`

`pip3 install bluepy`

### Requirements for reading Xiaomi Temperature and Humidity Sensor with ATC firmware

Additional requirements if you want to use the atc version. If you don't use ATC version, please ignore this section.
```
apt install bluetooth libbluetooth-dev
pip3 install pybluez
```

Bluetooth LE Scanning needs root. To run the script for AT with normal user rights, please execute
```
sudo setcap cap_net_raw,cap_net_admin+eip $(eval readlink -f `which python3`)
```
After a Python upgrade, you have to redo the above step.

## Usage

```
./LYWSD03MMC.py
usage: LYWSD03MMC.py [-h] [--device AA:BB:CC:DD:EE:FF] [--battery ]
                     [--count N] [--interface N] [--unreachable-count N]
                     [--round] [--debounce] [--offset OFFSET]
                     [--TwoPointCalibration] [--calpoint1 CALPOINT1]
                     [--offset1 OFFSET1] [--calpoint2 CALPOINT2]
                     [--offset2 OFFSET2] [--callback CALLBACK] [--name NAME]
                     [--skipidentical N] [--influxdb N] [--atc]
                     [--watchdogtimer X] [--devicelistfile DEVICELISTFILE]
                     [--onlydevicelist] [--rssi]

optional arguments:
  -h, --help            show this help message and exit
  --device AA:BB:CC:DD:EE:FF, -d AA:BB:CC:DD:EE:FF
                        Set the device MAC-Address in format AA:BB:CC:DD:EE:FF
  --battery [], -b []   Get estimated battery level
  --count N, -c N       Read/Receive N measurements and then exit script
  --interface N, -i N   Specifiy the interface number to use, e.g. 1 for hci1
  --unreachable-count N, -urc N
                        Exit after N unsuccessful connection tries

Rounding and debouncing:
  --round, -r           Round temperature to one decimal place
  --debounce, -deb      Enable this option to get more stable temperature
                        values, requires -r option

Offset calibration mode:
  --offset OFFSET, -o OFFSET
                        Enter an offset to the reported humidity value

2 Point Calibration:
  --TwoPointCalibration, -2p
                        Use complex calibration mode. All arguments below are
                        required
  --calpoint1 CALPOINT1, -p1 CALPOINT1
                        Enter the first calibration point
  --offset1 OFFSET1, -o1 OFFSET1
                        Enter the offset for the first calibration point
  --calpoint2 CALPOINT2, -p2 CALPOINT2
                        Enter the second calibration point
  --offset2 OFFSET2, -o2 OFFSET2
                        Enter the offset for the second calibration point

Callback related arguments:
  --callback CALLBACK, -call CALLBACK
                        Pass the path to a program/script that will be called
                        on each new measurement
  --name NAME, -n NAME  Give this sensor a name reported to the callback
                        script
  --skipidentical N, -skip N
                        N consecutive identical measurements won't be reported
                        to callbackfunction
  --influxdb N, -infl N
                        Optimize for writing data to influxdb,1 timestamp
                        optimization, 2 integer optimization

ATC mode related arguments:
  --atc, -a             Read the data of devices with custom ATC firmware
                        flashed
  --watchdogtimer X, -wdt X
                        Re-enable scanning after not receiving any BLE packet
                        after X seconds
  --devicelistfile DEVICELISTFILE, -df DEVICELISTFILE
                        Specify a device list file giving further details to
                        devices
  --onlydevicelist, -odl
                        Only read devices which are in the device list file
  --rssi, -rs           Report RSSI via callback

```

Note: When using rounding option you could see 0.1 degress more in the script output than shown on the display. Obviously the LYWSD03MMC just truncates the second decimal place.

Reading the battery level with the standard Bluetooth Low Energy characteristics doesn't work. It always returns 99 % battery level. Or to be correct, sometimes 10 % when the battery is really empty, see https://github.com/JsBergbau/MiTemperature2/issues/1#issuecomment-588156894 . But often before that device just shuts down before it can report another battery level. With every measurement the Aqara sensor also transmits the battery voltage. This voltage is transformed into a battery level 3.1V are 100%, 2.1V 0%.

The `--count` option is intended to save even more power. So far it is not proven, that only connecting at some interval will actually save power. See this discussion https://github.com/JsBergbau/MiTemperature2/issues/3#issuecomment-572982314

With the `--interface` option you specify the number of the bluetooth adapter to use. So `--interface 1` for using hci1

With `--influxdb 1` you can use a influxdb optimized output. In this mode a timestamp with the current data is sent every 10 seconds to influxdb. Or technically speaking, each received measurement is snapped to a grid of 10 seconds. Don't use this feature together with `--skipidentical` otherwise it won't help. To use RLE compression for timestamps influxdb requires all 1000 timestamps which are mostly in a block to have the same interval. Only one missing timestamp leads to s8b compression for timestamps. Since influxdb handles identical values very efficiently you save much more space by writing every 10 seconds instead of skipping identical values. Without RLE 1000 timestamps needed about 1129 Bytes of data in my measurement. With RLE its only 12 Byte. Of course there are now more measurements stored in influxdb, but still overall size in influxdb is still lower. Depends also environment, of course. With a very steady environment and very seldom writing identical valus then size in influxdb would be smaller not writing every 10 seconds, of course. Integer optimizsation `--influxdb 2`is not implemented yet.

`--unreachable-count N, -urc N` Use this option when you want to exit your script after collection the measurement but your sensor is somehow not reachable. Then after the specified number of failed connection tries the script will exit.

### ATC Mode Usage

Thanks to https://github.com/atc1441/ATC_MiThermometer there is an alternative firmware which sends out the measurements as Bluetooth Low Energy Advertisments. In this mode you don't have to connect to the sensor. This saves a lot of power, especially in cases where the signal strength is low, see https://github.com/JsBergbau/MiTemperature2/issues/32 
I've also noticed a higher range. In addition you can have multiple receivers, see Node-RED section https://github.com/JsBergbau/MiTemperature2#callback-to-node-red
For longer batterylife and higher stability ATC mode is recommended.

In this mode the script listens for BLE advertisments and filters for ATC flashed LYWSD03MMC sensors. So you start only one instance of this script and it reads out all your sensors. You can have multiple receivers and thus have a kind of cell network and your sensors are portable in a quite wide range. Use it optimally with influxdb and `--influxdb 1`. With this option timestamps are snapped to 10s and since influxdb only stores one value for one timestamp you won't have duplicate data in your database.

ATC firmware gives temperature only with one decimal place, so rounding and debouncing options are not available.

`--watchdogtimer X` sometimes your device leaves BLE scanning mode, then you won't receive any data anymore. To avoid this after X seconds without receiving any BLE packet (not only from ATC sensors) BLE scanning mode is re-enabled. If you have configured your ATC LYWSD03MMC to advertise new data every 10 seconds, I recommend a setting of 5 seconds, so `--watchdogtimer 5`. On a Raspberry PI Zero W polling 10 sensors (2 are currently unreachable) this re-enabling BLE scan can happen a few times per minute. When polling 8 reachable sensors it happens less frequent but still at least once or twice a minute. 

One note about new advertising data: The ATC LYWSD03MMC sends out the data about every second. After 10 seconds (or your configured interval) it advertises new data and to detect this, it increases the paket counter. Only the values of first paket of this series with the same paketcounter is displayed and reported by callback, since the data in one series is identical.

`--devicelistfile <filename>` Use this option to give your sensors a name/alias. This file can also be on a network drive. So you can keep it up to date on a single place for multiple receivers. Also in this file is space for calibration data. 

Note: ATC firmware shows other humidity values than the stock Xiaomi firmware, so you have to re-calibrate your sensors. The temperature value is unchanged compared to the Xiaomi sensor firmware.

An example is given in the sensors.ini file in this repository. It is quite self explaining

```
[default]
[info]
info1=MAC Adresses must be in UPPERCASE otherwise sensor won't be found by the script
info2=now all available options are listet. If offset1, offset2, calpoint1 and calpoint2 are given 2Point calibration is used instead of humidityOffset.
info3= Note options are case sensitive
;info4=Use semicolon to comment out lines
sensorname=Specify an easy readable name
humidityOffset=-5
offset1 = -10
offset2 = 10
calpoint1 = 33
calpoint2 = 75

;[AA:BB:CC:DD:EE:FF]
; sensorname=Bathroom
; humidityOffset=-30
; offset1 = -10
; offset2 = -10
; calpoint1 = 33
; calpoint2 = 75

[BD:AD:CA:1F:4D:12]
sensorname=Living Room
offset1 = -2
offset2 = 2
calpoint1 = 33
calpoint2 = 75
```

`--onlydevicelist` Use this option to read only the data from sensors which are in your device list. This is quite useful if you have some spare sensors and you don't want your database get flooded with this data.

`--rssi` Reports the RSSI via callback

Hint for storing the data in influx: 
When you have configured an advertisment interval of 10 seconds: Ideally store one measurement every 25 seconds to use very efficient RLE compression for your measurements. With storing the data every 25s, almost every timestamp is stored. This leads to RLE compression of the timestamp thus saving a lot of space in influxdb. With an interval of 20 seconds in tests it occured quite often, that timestamp slots were not filled and thus no RLE compression can be used. 

With original firmware where you connect to each sensor every 6 seconds an measurement is sent and storing every 10 seconds a measurement is a good value.

ATC mode uses passive scanning for saving battery life of the sensors. Read more about this here https://github.com/JsBergbau/MiTemperature2/issues/41#issuecomment-735361200

## Tips

Use `sudo hcitool lescan --duplicate` to get the MAC of your Sensor.
This sensor only sends its measurements only via notifications. There are quite often notifications because the temperature is measured with a precision of 2 decimal places, but only one shown on the display (and this value is truncated, see above). Trying to directly read/poll the characteristics returns always zeroes.

### Debouncing

The temperature values often change between the same values. To get cleaner temperature curves a debouncing function has been implemented. See here https://github.com/JsBergbau/MiTemperature2/issues/2 for more info.

### Minus degrees

When looking at the specifications this LYWSD03MMC Sensor is specified from 0 °C to 60 °C. The LYWSDCGQ (the Bluetooth Temperatur sensor with the round display and an AAA battery) is specified from -9.9. 
I can confirm the LYWSD03MMC also goes down to -9.9 °C. At colder temperatures it only shows an "L". But even at lower temperatures the correct temperature is still sent! So you even could use ist to watch the temperature in your freezer which is a lot below -9.9 °C. However batterylife may be significantly reduced at those low temperatures.

### High battery usage

There is currently no way to detect a too high battery drain except having empty batteries in less than 2 month. If you encouter lots of empty batteries, please reduce distance between LYWSD03MMC sensor and your Bluetooth receiver. With a voltage drop of 0.1 V in 1.5 month everything is perfectly fine. If it is a bit more, don't worry. Can be a button cell of lower quality. For more infos please visit https://github.com/JsBergbau/MiTemperature2/issues/32

## Sample output

```
 ./LYWSD03MMC.py -d AA:BB:CC:DD:EE:FF -r -b
Trying to connect to AA:BB:CC:DD:EE:FF
Temperature: 20.6
Humidity: 54
Battery voltage: 2.944
Battery level: 84

Temperature: 20.6
Humidity: 54
Battery voltage: 2.944
Battery level: 84

Temperature: 20.6
Humidity: 54
Battery voltage: 2.944
Battery level: 84

Temperature: 20.6
Humidity: 54
Battery voltage: 2.944
Battery level: 84

Temperature: 20.6
Humidity: 54
Battery voltage: 2.944
Battery level: 84

Temperature: 20.6
Humidity: 54
Battery voltage: 2.944
Battery level: 84

Temperature: 20.6
Humidity: 54
Battery voltage: 2.944
Battery level: 84

Temperature: 20.6
Humidity: 54
Battery voltage: 2.944
Battery level: 84

Temperature: 20.6
Humidity: 54
Battery voltage: 2.944
Battery level: 84
```

### Sample output ATC mode

```
./LYWSD03MMC.py --atc
Script started in ATC Mode
----------------------------
In this mode all devices within reach are read out, unless a namefile and --namefileonlydevices is specified.
Also --name Argument is ignored, if you require names, please use --namefile.
In this mode rounding and debouncing are not available, since ATC firmware sends out only one decimal place.
ATC mode usually requires root rights. If you want to use it with normal user rights,
please execute "sudo setcap cap_net_raw,cap_net_admin+eip $(eval readlink -f `which python3`)"
You have to redo this step if you upgrade your python version.
----------------------------
Power ON bluetooth device 0
Bluetooth device 0 is already enabled
Enable LE scan
scan params: interval=1280.000ms window=1280.000ms own_bdaddr=public whitelist=no
socket filter set to ptype=HCI_EVENT_PKT event=LE_META_EVENT
Listening ...
BLE packet: XX:XX:XX:XX:XX:XX 00 1110161a18xxxxxxxxxxxx00dc2e420afdd6 -60
Temperature:  22.0
Humidity:  46
Battery voltage: 2.813 V
RSSI: -60 dBm

BLE packet: XX:XX:XX:XX:XX:XX 00 1110161a18xxxxxxxxxxxx00e22d570bab16 -90
Temperature:  22.6
Humidity:  45
Battery voltage: 2.987 V
RSSI: -90 dBm

BLE packet: XX:XX:XX:XX:XX:XX 00 1110161a18xxxxxxxxxxxx009d314f0b6456 -65
Temperature:  15.7
Humidity:  49
Battery voltage: 2.916 V
RSSI: -65 dBm

BLE packet: XX:XX:XX:XX:XX:XX 00 1110161a18xxxxxxxxxxxx00d2313d0ace30 -90
Temperature:  21.0
Humidity:  49
Battery voltage: 2.766 V
RSSI: -90 dBm

BLE packet: XX:XX:XX:XX:XX:XX 00 1110161a18xxxxxxxxxxxx00d331430b0579 -91
Temperature:  21.1
Humidity:  49
Battery voltage: 2.821 V
RSSI: -91 dBm

BLE packet: XX:XX:XX:XX:XX:XX 00 1110161a18xxxxxxxxxxxx008431530b872b -77
Temperature:  13.2
Humidity:  49
Battery voltage: 2.951 V
RSSI: -77 dBm

BLE packet: XX:XX:XX:XX:XX:XX 00 1110161a18xxxxxxxxxxxx00cf344d0b5264 -81
Temperature:  20.7
Humidity:  52
Battery voltage: 2.898 V
RSSI: -81 dBm

BLE packet: XX:XX:XX:XX:XX:XX 00 1110161a18xxxxxxxxxxxx00d5304d0b5607 -64
Temperature:  21.3
Humidity:  48
Battery voltage: 2.902 V
RSSI: -64 dBm

BLE packet: XX:XX:XX:XX:XX:XX 00 1110161a18xxxxxxxxxxxx00bf36500b765d -87
Temperature:  19.1
Humidity:  54
Battery voltage: 2.934 V
RSSI: -87 dBm

BLE packet: XX:XX:XX:XX:XX:XX 00 1110161a18xxxxxxxxxxxx00d2303a0ab84b -73
Temperature:  21.0
Humidity:  48
Battery voltage: 2.744 V
RSSI: -73 dBm

BLE packet: XX:XX:XX:XX:XX:XX 00 1110161a18xxxxxxxxxxxx008431530b872c -77
Temperature:  13.2
Humidity:  49
Battery voltage: 2.951 V
RSSI: -77 dBm

BLE packet: XX:XX:XX:XX:XX:XX 00 1110161a18xxxxxxxxxxxx00d2314f0b60d1 -91
Temperature:  21.0
Humidity:  49
Battery voltage: 2.912 V
RSSI: -91 dBm

BLE packet: XX:XX:XX:XX:XX:XX 00 1110161a18xxxxxxxxxxxx00d330400aedf1 -94
Temperature:  21.1
Humidity:  48
Battery voltage: 2.797 V
RSSI: -94 dBm

BLE packet: XX:XX:XX:XX:XX:XX 00 1110161a18xxxxxxxxxxxx00484a420af634 -91
Temperature:  7.2
Humidity:  74
Battery voltage: 2.806 V
RSSI: -91 dBm

BLE packet: XX:XX:XX:XX:XX:XX 00 1110161a18xxxxxxxxxxxx00d231530b8ab0 -88
Temperature:  21.0
Humidity:  49
Battery voltage: 2.954 V
RSSI: -88 dBm
```

### More info

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

Sometimes script fails to connect and tries to connect forever.
Just exec `killall bluepy-helper` You can even do this while script is running. It will disconnect, but recovery automatically.

Since version 1.1 there is a watchdog-Thread checking when connection is lost for at least 60 seconds and then killing the corresponding bluepy-helper, so that other connections aren't affected. This is a workaround for an obvious bug in bluepy. This bug only occured so far when trying to (re)connect. Then this call to bluepy blocks sometimes forever.

If that doesn't help, a problem with the bluetooth stack could be the cause. To resolve:

```
sudo hciconfig hci0 down
sudo hciconfig hci0 up
```

Sometimes bluetooth gets stucks, especially if you have other software accessing/using bluetooth on your devices. After a reboot everything was fine again. If that happens a lot, you can use an additional Blueooth receiver and use it with the `--interface` option.

## Calibration

Note: If you have calibrated your sensors and flash ATC firmware, you have to calibrate them again.

Especially humidity value is often not very accurate. You get better results if you calibrate against a known humidity. This can be done very easy with common salt (NaCl). Make a saturated solution and put it together with the Xiaomi Bluetooth thermometer in an airtight box. Ensure that no (salt) water gets in contact with the device. Saltwater is very corrosive.
Wait about 24 - 48 hours with a constant temperature. You should now have about 75 % relative humidity. I don't know how long it takes for the sensors to drift. So I will redo this procedure about every year. 

A quite constant temperature while calibration is very important, because with temperature also humidity changes and it takes some time for the system to rebalance the humidity. In my experiments at 20 °C room temperature it took about 48 hours until humidity readings were quite stable and didn't change anymore. So give it time. If you take the sensors out of calibration humidity too early they haven't reached the final value yet.

### Offset calibration

E.g. mine shows 79 % RH when actually there is 75 %. Excecute the script with `-o -4` to substract 4 from the readout value.

### Two point calibration

The offset is not linear over the whole humidity values, see https://www.rotronic.com/media/productattachments/files/c/a/capacitive_humidity_sensor_final.pdf Page 2.

>Linearity Errors. The typical response of a relative humidity capacitive sensor (between 0 and 100 percent RH) is not linear. Depending on the correction made by the electronic circuits, the instrument may have a linearity error.

So you should calibrate at another point. MagnesiumChloride is recommended as giving about 33% RH at 20 °C. Please use very pure MgCl. It is also sold as bath salt and stuff like that. For high accuracy please use a purity > 99 %.

Also Calciumchloride is suitable, but the humidity depends more on temperature. Be sure to have 20 °C. https://www.salzwiki.de/index.php/Deliqueszenzfeuchte
CaCl is often found in these small non-electric dehumidifiers which you can refill with refill packs.

My Xiaomi Bluetooth thermometer shows 39% RH at 33% RH. So wie here have an offset of 6.
Another hygrometer show 69 % at 75% RH and 33% RH at 33% RH. So offset +6 at 75% TH and offset 0 at 33% RH.
Example for the Xiaomi to use 2 point calibration:
At 75% RH you have to substract 4 from the readout value, at 33% RH you have to substract 6.

`-2p -p2 75 -o2 -4 -p1 33 -o1 -6`

```
-2p: Enables 2 point calibration
-p2 75: Point 2 at 75% RH
-o2 -4: Offset -4 at Point 2
-p1 33: Point 2 at 33% RH
-o1 -6: Offset -6 at Point 2
```

Note the values in between are interpolated linear and the result is rounded to the nearest whole number. It makes no sense to give floatingpoint number when the input is none.

Output example:

```
./LYWSD03MMC.py -d AA:BB:CC:DD:EE:FF -2p -p2 75 -o2 -4 -p1 33 -o1 -6
Trying to connect to AA:BB:CC:DD:EE:FF
Temperature: 20.62
Humidity: 54
Battery voltage: 2.944
Calibrated humidity: 49

Temperature: 20.6
Humidity: 54
Battery voltage: 2.944
Calibrated humidity: 49

Temperature: 20.61
Humidity: 54
Battery voltage: 2.944
Calibrated humidity: 49

```

## Callback for processing the data

Via the --call option a script can be passed to sent the data to.
Example
`./LYWSD03MMC.py -d AA:BB:CC:DD:EE:FF -2p -p2 75 -o2 -4 -p1 33 -o1 -6 --name MySensor --callback sendToFile.sh`
If you don't give the sensor a name, the MAC-Address is used. The callback script must be within the same folder as this script.
The values outputted depends on the options like calibration or battery. So the format is printed in the first argument.
Example callback

```
#!/bin/bash
# This is quite useful for testing
echo $@ >> data.txt
exit 0
```

Gives in data.txt `sensorname,temperature,humidity,voltage,humidityCalibrated,timestamp MySensor 20.61 54 2.944 49 1582120122`

Whereas the timestamp is in the Unix timestamp format in UTC (seconds since 1.1.1970 00:00).

There is an option not to report identical data to the callback. To distinguish between a failure and constantly the same values are read, the option takes the number after which identical measurements the data is reportet to the callback. Use the `--skipidentical N` for this. E.g. `--skipidentical 1` means 1 identical measurement is skipped, so only every second identical measurement is reportet to callback. I recommend numbers between 10 and 50, giving at least every minute respectively 5 minutes a call to the callback script (With 10 and 50 the actual time is slightly higher than 1 respectively 5 minutes). It is recommended to use the `--round` and `--debounce` option, otherwise there is a lot of noise with changing the temperature. See https://github.com/JsBergbau/MiTemperature2/issues/2

All data received from the sensor is stored in a list and transmitted sequentially. This means if your backend like influxdb is not reachable when a new measurement is received, it will be tried again later (currently waiting 5 seconds before the next try). Thus no data is lost when your storage engine has some trouble. There is no upper limit (the only limit should be the RAM). Keep this in mind when specifing a wrong backend.

"sendToInflux.sh" is an example script for sending the data to influxdb via http-API. Precision was set to the level of seconds. This gives better compression ratios in influxdb.

## Send metrics to Prometheus

[Read instruction about integartion with Prometheus Push Gateway](./prometheus/README.md)

## Callback to Node-RED
Finally there is a callback and sample flows to send the data to Node-RED. Especially if you have multiple receivers this is quite comfortable to manage the name and calibration data of your sensors at one place in Node-Red. No need to change configuration in any of your Receivers. 

This solution makes it also very easy to have multiple Receivers and you can easily move the devices around between them. As long as one device reaches one receiver everything will work. If it reaches multiple receivers you can even reboot them without data loss.

To use the script with Node-RED just import the flows from `MiTemperature2 Node-Red Flows.txt`
With that flow you can even start the script in ATC-Mode via Node-RED. If you are user `pi` and in your home directory, clone this Repo via `git clone https://github.com/JsBergbau/MiTemperature2`, make `LYWSD03MMC.py` and `./sendToNodeRed.sh` executable and you even have not to change the script execution part.

The Node-RED flow is documented with comments for easy usage. If theres missing some information, just open an issue and I'll have a look.

For easily switching between filtering of Node-Red and the Python-Script LYWSD03MMC there are two scripts included.
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


