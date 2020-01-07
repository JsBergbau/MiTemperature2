#  Read data from Xiaomi Mijia LYWSD03MMC Bluetooth 4.2 Temperature Humidity sensor
With this script you can read out the value of your LYWSD03MMC sensor, e.g. with Raspberry PI. Note Raspbery Pi 4 has a very limited bluetooth range. PI Zero W gives much longer range.

## Prequisites / Requirements
You need Python3 3.7 or above because of the dataclasses used in the Callback Function. If you don't have Python 3.7 please take the previous version from here https://raw.githubusercontent.com/JsBergbau/MiTemperature2/5d7b215d7b22d4c21d9244f8a4102513b928f2c7/LYWSD03MMC.py

For example Raspbian Stretch has only Python 3.5.3. If you like to upgrade your Distribution to current Buster release follow this Tutorial https://pimylifeup.com/upgrade-raspbian-stretch-to-raspbian-buster/ If doing so: Omit the rpi-update step.

Prequisites: python3 bluez python3-pip bluepy
install via
`sudo apt install python3 bluez python3-pip`
`pip3 install bluepy`


## Usage
```
./LYWSD03MMC.py
usage: LYWSD03MMC.py [-h] [--device DEVICE] [--battery N] [--round]
                     [--name NAME] [--callback CALLBACK] [--offset OFFSET]
                     [--TwoPointCalibration] [--calpoint1 CALPOINT1]
                     [--offset1 OFFSET1] [--calpoint2 CALPOINT2]
                     [--offset2 OFFSET2]

optional arguments:
  -h, --help            show this help message and exit
  --device DEVICE, -d DEVICE
                        Set the device MAC-Adress in format AA:BB:CC:DD:EE:FF
  --battery N, -b N     Read batterylevel every x update
  --round, -r           Round temperature to one decimal place
  --name NAME, -n NAME  Give this sensor a name, used at callback function
  --callback CALLBACK, -call CALLBACK
                        Pass the path to a program/script that will be called
                        on each new measurement

Offset calibration mode:
  --offset OFFSET, -o OFFSET
                        Enter an offset to the humidity value read

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
  ```
  
  Note: When using rounding option you could see 0.1 degress more in the script output than shown on the display. Obviously the LYWSD03MMC just trancates the second decimal place.
  In order to save power: It is recommended to read the battery level quite seldom. When using the --battery option Battery-Level is always read on the first run.
  
  
  ## Tipps
  Use `sudo hcitool lescan --duplicate` to get the MAC of your Sensor.
  This sensor only sends its measurements only via notifications. There are quite often notifications because the temperature is measured with a precision of 2 decimal places, but only one shown on the display (and this value is truncated, see above). Trying to directly read/poll the characteristics returns always zeroes. 
  
  ## Sample output
```  
 ./LYWSD03MMC.py -d AA:BB:CC:DD:EE:FF -r -b 5
Trying to connect to AA:BB:CC:DD:EE:FF
Waiting...
Temperature: 20.1
Humidity: 77
Battery-Level: 99

Temperature: 20.1
Humidity: 77

Temperature: 20.1
Humidity: 77

Temperature: 20.1
Humidity: 77

Temperature: 20.1
Humidity: 77

Temperature: 20.1
Humidity: 77
Battery-Level: 99
```

### More info
If you like gatttool you can use it, too. However it didn't notice when BT connection was lost, while this Python-Script automatically reestablishes the connection.
```
gatttool -I
connect AA:BB:CC:DD:EE:FF
#enable notifications
char-write-req 0x0038 0100
#Read battery-Level, consider: note value is in Hex format
char-read-hnd 0x001b
```

Strictly speaking enabling notifications every time is not necessary since the device remembers it between connects. However to make it always work, the Python-Script enables them upon every connection establishment.

Notification format
`Notification handle = 0x0036 value: f8 07 4a d6 0b`
f8 07 is the temperature as INT16 in little endian format. Divide it by 100 to get the temperature in degree Celsius
4a is the humidity. Only integer output :(
d6 and 0b are unknown to me. Tell me if you know what these values mean.

### Troubleshooting
Sometimes script immediately fails to connect and quits. Seems to be a problem with the bluetooth stack. To resolve:
```
sudo hciconfig hci0 down
sudo hciconfig hci0 up
```

## Calibration
Especially humidity value is often not very accurate. You get better results if you calibrate against a known humidity. This can be done very easy with common salt (NaCl). Make a saturated solution and put it together with the Xiaomi Bluetooth thermometer in an airtight box. Ensure that no (salt) water gets in contact with the device. Saltwater is very corrosive. 
Wait about 24 hours with a constant temperature. You should now have about 75 % relative humidity. I don't know how long it takes for the sensors to drift. So I will redo this procedure about every year.

### Offset calibration
E.g. mine shows 79 % RH when actually there is 75 %. Excecute the script with `-o -4` to substract 4 from the readout value.

### Two point calibration
The offset is not linear over the whole humidity values. So you should calibrate at another point. MagnesiumChloride is recommended giving about 33% RH at 20 °C. Also Calciumchloride is suitable, but the humidity depends more on temperature. Be sure to have 20 °C. https://www.salzwiki.de/index.php/Deliqueszenzfeuchte
 
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
Waiting...
Temperature: 20.83
Humidity: 39
Calibrated humidity: 33

Temperature: 20.82
Humidity: 39
Calibrated humidity: 33
```

## Callback for processing the data
Via the --call option a script can be passed to sent the data to. 
Example
`./LYWSD03MMC.py -d AA:BB:CC:DD:EE:FF -2p -p2 75 -o2 -4 -p1 33 -o1 -6 -b 5 --name MySensor --callback sendData.sh`
If you don't give the sensor a name, the MAC-Address is used. The callback script must be within the same folder as this script.
The values outputted depends on the options like calibration or battery. So the format is printed in the first argument.
Example callback
```
#!/bin/bash
echo $@ >> data.txt
```
Gives in data.txt `sensorname,temperature,humidity,humidityCalibrated,batteryLevel MySensor 20.19 39 33 99`

If successive measurements contain the same data no data is send. So only changed data is reported to the callback. It is recommended to use the --round option, otherwise there is a lot of noise with changing the temperature in the second decimal place. 

Because of the implementation batterylevel is read after the first data received from sensor. This means after startup the first batteryvalue reported is always zero. After the second temperature reading the correct batterie value is passed to the callback function and updated via the --battery Option

All data received from the sensor is stored in a list and transmitted sequentially. This means if your backend like influxdb is not reachable when a new measurement is received, it will be tried again later (currently waiting 5 seconds before the next try). Thus no data is lost when your storage engine has some trouble. There is no upper limit (the only limit should be the RAM). Keep this in mind when specifing a wrong backend. 

"sendToInflux.sh" is an example script for sending the data to influxdb via http-API. 
