#  Xiaomi Mijia LYWSD03MMC Bluetooth 4.2 Temperature Humidity sensor
With this script you can read out the value of your LYWSD03MMC sensor. Note Raspbery Pi 4 has a very limited bluetooth range. PI Zero W gives much longer range.

## Prequisites
python3 bluez python3-pip bluepy
`install via sudo apt install python3 bluez python3-pip`
`pip3 install bluepy`

## Usage
```
usage: Xiaomi.py [-h] [--device DEVICE] [--battery N] [--round]

optional arguments:
  -h, --help            show this help message and exit
  --device DEVICE, -d DEVICE
                        Set the device MAC-Adress in format AA:BB:CC:DD:EE:FF
  --battery N, -b N     Read batterylevel every x update
  --round, -r           Round temperature to one decimal place
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

Strictly speaking enabling notifications every time is not necessary since the device remembers it between connects. However to make it always work the Python-Script enables them upon every connection establishment.

Notification format
`Notification handle = 0x0036 value: f8 07 4a d6 0b`
f8 07 is the temperature as INT16 in little endian format. Divide it by 100 to get the temperature in degree Celsius
4a is the humidity. Only integer output :(
d6 and 0b are unknown to me. Tell me if you know what these values mean.

## To come
Implementing a correction/calibrating function for Humidity


