#  Xiaomi Mijia LYWSD03MMC Bluetooth 4.2 Temperature Humidity sensor
With this script you can read out the value of your LYWSD03MMC sensor. Note Raspbery Pi 4 has a very limited bluetooth range. PI Zero W gives much longer range.

## Prequisites
python3 bluez python3-pip bluepy
`install via sudo apt install python3 bluez python3-pip`
pip3 install bluepy

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
  
  ##Sample output
  
 ./Xiaomi.py -d AA:BB:CC:DD:EE:FF -r -b 5
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

##To come
Implementing a correction/calibrating function for Humidity


