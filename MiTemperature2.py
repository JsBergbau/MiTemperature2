#!/usr/bin/env -S python3 -u
#-u to unbuffer output. Otherwise when calling with nohup or redirecting output things are printed very lately or would even mixup

print("---------------------------------------------")
print("MiTemperature2 / ATC Thermometer version 6.1")
print("---------------------------------------------")

readme="""

Please read README.md in this folder. Latest version is available at https://github.com/JsBergbau/MiTemperature2#readme
This file explains very detailed about the usage and covers everything you need to know as user.

"""

print(readme)


import argparse
import os
import configparser
import socket
import threading
import time
import traceback
import logging
import json
import urllib.request
import urllib.error
import urllib.parse
import ssl
import signal
import bluetooth._bluetooth as bluez
import cryptoFunctions
from dataclasses import dataclass
from collections import deque
from bluetooth_utils import (
    toggle_device,
    enable_le_scan, parse_le_advertising_events,
    disable_le_scan, raw_packet_to_str
)


@dataclass
class Measurement:
	temperature: float
	humidity: int
	voltage: float
	calibratedHumidity: int = 0
	battery: int = 0
	timestamp: int = 0
	sensorname: str	= ""
	rssi: int = 0 

	def __eq__(self, other): #rssi may be different, so exclude it from comparison
		if self.temperature == other.temperature and self.humidity == other.humidity and self.calibratedHumidity == other.calibratedHumidity and self.battery == other.battery and self.sensorname == other.sensorname:
			return True
		else:
			return False

measurements=deque()
previousMeasurements={}
previousCallbacks={}
identicalCounters={}
MQTTClient=None
MQTTTopic=None
receiver=None
subtopics=None
mqttJSONDisabled=False

def myMQTTPublish(topic,jsonMessage):
	global subtopics
	if len(subtopics) > 0:
		messageDict = json.loads(jsonMessage)
		for subtopic in subtopics:
			print("Topic:",subtopic)
			MQTTClient.publish(topic + "/" + subtopic,messageDict[subtopic],0)
	if not mqttJSONDisabled:
		MQTTClient.publish(topic,jsonMessage,1)


def signal_handler(sig, frame):
	disable_le_scan(sock)	
	os._exit(0)
		
def thread_SendingData():
	global previousMeasurements
	global previousCallbacks
	global measurements
	path = os.path.dirname(os.path.abspath(__file__))

	while True:
		try:
			mea = measurements.popleft()
			invokeCallback = True

			if mea.sensorname in previousCallbacks:
				if args.callback_interval > 0 and (int(time.time()) - previousCallbacks[mea.sensorname] < args.callback_interval):
					print("Callback for " + mea.sensorname + " would be within interval (" + str(int(time.time()) - previousCallbacks[mea.sensorname]) + " < " + str(args.callback_interval) + "); don't invoke callback\n")
					invokeCallback = False


			if mea.sensorname in previousMeasurements:
				prev = previousMeasurements[mea.sensorname]
				if (mea == prev and identicalCounters[mea.sensorname] < args.skipidentical): #only send data when it has changed or X identical data has been skipped, ~10 packets per minute, 50 packets --> writing at least every 5 minutes
					print("Measurements for " + mea.sensorname + " are identical; don't send data\n")
					identicalCounters[mea.sensorname]+=1
					invokeCallback = False

			if invokeCallback:

				if args.callback:
					fmt = "sensorname,temperature,humidity,voltage" #don't try to separate by semicolon ';' os.system will use that as command separator
					if ' ' in mea.sensorname:
						sensorname = '"' + mea.sensorname + '"'
					else:
						sensorname = mea.sensorname
					params = sensorname + " " + str(mea.temperature) + " " + str(mea.humidity) + " " + str(mea.voltage)
					if mea.humidity != mea.calibratedHumidity: #Calibration has been done
						fmt +=",humidityCalibrated"
						params += " " + str(mea.calibratedHumidity)
					if (args.battery):
						fmt +=",batteryLevel"
						params += " " + str(mea.battery)
					if (args.rssi):
						fmt +=",rssi"
						params += " " + str(mea.rssi)
					params += " " + str(mea.timestamp)
					fmt +=",timestamp"
					cmd = path + "/" + args.callback + " " + fmt + " " + params
					print(cmd)
					ret = os.system(cmd)

				if args.httpcallback:
					url = args.httpcallback.format(
						sensorname=urllib.parse.quote(mea.sensorname), #allow MAC-adress
						temperature=mea.temperature,
						humidity=mea.humidity,
						voltage=mea.voltage,
						humidityCalibrated=mea.calibratedHumidity,
						batteryLevel=mea.battery,
						rssi=mea.rssi,
						timestamp=mea.timestamp,
					)
					print(url)
					ret = 0
					try:
						# Deactivate SSL verification, like before
						ctx = ssl._create_unverified_context()

						with urllib.request.urlopen(url, timeout=1, context=ctx) as r:
							if r.status != 200:  # r.raise_for_status()
								ret = 1
					except (urllib.error.URLError, urllib.error.HTTPError) as e:
						ret = 1

				if ret != 0:
					measurements.appendleft(mea) #put the measurement back
					print ("Data couldn't be send to callback, retrying...")
					time.sleep(5) #wait before trying again
				else: #data was sent
					previousMeasurements[mea.sensorname]=Measurement(mea.temperature,mea.humidity,mea.voltage,mea.calibratedHumidity,mea.battery,mea.timestamp,mea.sensorname) #using copy or deepcopy requires implementation in the class definition
					identicalCounters[mea.sensorname]=0
					previousCallbacks[mea.sensorname]=int(time.time())


		except IndexError:
			#print("No Data")
			time.sleep(1)
		except Exception as e:
			print(e)
			print(traceback.format_exc())

sock = None #from ATC 
lastBLEPacketReceived = 0
BLERestartCounter = 1
def keepingLEScanRunning(): #LE-Scanning gets disabled sometimes, especially if you have a lot of BLE connections, this thread periodically enables BLE scanning again
	global BLERestartCounter
	while True:
		time.sleep(1)
		now = time.time()
		if now - lastBLEPacketReceived > args.watchdogtimer:
			print("Watchdog: Did not receive any BLE packet within", int(now - lastBLEPacketReceived), "s. Restarting BLE scan. Count:", BLERestartCounter)
			disable_le_scan(sock)
			enable_le_scan(sock, filter_duplicates=False)
			BLERestartCounter += 1
			print("")
			time.sleep(5) #give some time to take effect


def calibrateHumidity2Points(humidity, offset1, offset2, calpoint1, calpoint2):
	p1y=calpoint1
	p2y=calpoint2
	p1x=p1y - offset1
	p2x=p2y - offset2
	m = (p1y - p2y) * 1.0 / (p1x - p2x) # y=mx+b
	b = p2y - m * p2x #would be more efficient to do these calculations only once
	humidityCalibrated=m*humidity + b
	if (humidityCalibrated > 100 ): #with correct calibration this should not happen
		humidityCalibrated = 100
	elif (humidityCalibrated < 0):
		humidityCalibrated = 0
	humidityCalibrated=int(round(humidityCalibrated,0))
	return humidityCalibrated



def buildJSONString(measurement):
	jsonstr = '{"temperature": ' + str(measurement.temperature) + ', "humidity": ' + str(measurement.humidity) + ', "voltage": ' + str(measurement.voltage) \
		+ ', "calibratedHumidity": ' + str(measurement.calibratedHumidity) + ', "battery": ' + str(measurement.battery) \
		+ ', "timestamp": '+ str(measurement.timestamp) +', "sensor": "' + measurement.sensorname + '", "rssi": ' + str(measurement.rssi) \
		+ ', "receiver": "' + receiver  + '"}'
	return jsonstr

def MQTTOnConnect(client, userdata, flags, rc):
    print("MQTT connected with result code "+str(rc))

def MQTTOnPublish(client,userdata,mid):
	print("MQTT published, Client:",client," Userdata:",userdata," mid:", mid)

def MQTTOnDisconnect(client, userdata,rc):
	print("MQTT disconnected, Client:", client, "Userdata:", userdata, "RC:", rc)	

# Main loop --------
parser=argparse.ArgumentParser(allow_abbrev=False,epilog=readme)
parser.add_argument("--interface","-i", help="Specify the interface number to use, e.g. 1 for hci1", metavar='N', type=int, default=0)
parser.add_argument("--mqttconfigfile","-mcf", help="Specify a configurationfile for MQTT broker")


rounding = parser.add_argument_group("Rounding and debouncing")
rounding.add_argument("--round","-r", help="Round temperature to one decimal place and humidity to whole numbers)",action='store_true')

callbackgroup = parser.add_argument_group("Callback related arguments")
callbackgroup.add_argument("--callback","-call", help="Pass the path to a program/script that will be called on each new measurement")
callbackgroup.add_argument("--httpcallback","-http", help="Pass the URL to a program/script that will be called on each new measurement")
callbackgroup.add_argument("--skipidentical","-skip", help="N consecutive identical measurements won't be reported to callback function",metavar='N', type=int, default=0)
callbackgroup.add_argument("--callback-interval","-int", help="Only invoke callback function every N seconds, e.g. 600 = 10 minutes",type=int, default=0)
callbackgroup.add_argument("--influxdb","-infl", help="Optimize for writing data to influxdb,1 timestamp optimization, 2 integer optimization",metavar='N', type=int, default=0)
callbackgroup.add_argument("--battery","-b", help="Pass the battery level to callback", metavar='', type=int, nargs='?', const=1)
callbackgroup.add_argument("--rssi","-rs", help="Report RSSI via callback",action='store_true')

passivegroup = parser.add_argument_group("Additional options")
passivegroup.add_argument("--watchdogtimer","-wdt",metavar='X', type=int, help="Re-enable scanning after not receiving any BLE packet after X seconds")
passivegroup.add_argument("--devicelistfile","-df",help="Specify a device list file giving further details to devices")
passivegroup.add_argument("--onlydevicelist","-odl", help="Only read devices which are in the device list file",action='store_true')
passivegroup.add_argument("--bthome-onlyfull-transmit","-bot", help="Begin transmit BTHome data only, when both packet types (battery and temperature) have been received", action='store_true')


args=parser.parse_args()

if args.mqttconfigfile:
	try:
		import paho.mqtt.client as mqtt
	except:
		print('Please install MQTT-Library via "pip/pip3 install \'paho-mqtt<2.0.0\'"')
		exit(1)
	if not os.path.exists(args.mqttconfigfile):
		print ("Error MQTT config file '",args.mqttconfigfile,"' not found")
		os._exit(1)
	mqttConfig = configparser.ConfigParser()
	mqttConfig.read(args.mqttconfigfile)
	broker = mqttConfig["MQTT"]["broker"]
	port = int(mqttConfig["MQTT"]["port"])

	# MQTTS parameters
	tls = int(mqttConfig["MQTT"]["tls"]) if "tls" in mqttConfig["MQTT"] else 0
	if tls != 0:
		cacerts = mqttConfig["MQTT"]["cacerts"] if mqttConfig["MQTT"]["cacerts"] else None
		certificate = mqttConfig["MQTT"]["certificate"] if mqttConfig["MQTT"]["certificate"] else None
		certificate_key = mqttConfig["MQTT"]["certificate_key"] if mqttConfig["MQTT"]["certificate_key"] else None
		insecure = int(mqttConfig["MQTT"]["insecure"])
	username = mqttConfig["MQTT"]["username"]
	password = mqttConfig["MQTT"]["password"]
	MQTTTopic = mqttConfig["MQTT"]["topic"]
	lastwill = mqttConfig["MQTT"]["lastwill"]
	lwt = mqttConfig["MQTT"]["lwt"]
	clientid=mqttConfig["MQTT"]["clientid"]
	receiver=mqttConfig["MQTT"]["receivername"]
	subtopics=mqttConfig["MQTT"]["subtopics"]
	if len(subtopics) > 0:
		subtopics=subtopics.split(",")
		if "nojson" in subtopics:
			subtopics.remove("nojson")
			mqttJSONDisabled=True

	if len(receiver) == 0:
		import socket
		receiver=socket.gethostname()

	client = mqtt.Client(clientid)
	client.on_connect = MQTTOnConnect
	client.on_publish = MQTTOnPublish
	client.on_disconnect = MQTTOnDisconnect
	client.reconnect_delay_set(min_delay=1,max_delay=60)
	client.loop_start()
	client.username_pw_set(username,password)
	if len(lwt) > 0:
		print("Using lastwill with topic:",lwt,"and message:",lastwill)
		client.will_set(lwt,lastwill,qos=1)
	# MQTTS parameters
	if tls:
		client.tls_set(cacerts, certificate, certificate_key, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS, ciphers=None)
		client.tls_insecure_set(insecure)
	
	client.connect_async(broker,port)
	MQTTClient=client
	
if args.callback or args.httpcallback:
	dataThread = threading.Thread(target=thread_SendingData)
	dataThread.start()

signal.signal(signal.SIGINT, signal_handler)	

print("Script started")
print("------------------------------")
print("All devices within reach are read out, unless a devicelistfile and --onlydevicelist is specified.")
print("In this mode debouncing is not available. Rounding option will round humidity and temperature to one decimal place.")
print("Passive mode usually requires root rights. If you want to use it with normal user rights, \nplease execute \"sudo setcap cap_net_raw,cap_net_admin+eip $(eval readlink -f `which python3`)\"")
print("You have to redo this step if you upgrade your python version.")
print("----------------------------")


advCounter=dict()
sensors = dict()
if args.devicelistfile:
	if not os.path.exists(args.devicelistfile):
		print ("Error: specified device list file '",args.devicelistfile,"' not found")
		os._exit(1)
	sensors = configparser.ConfigParser()
	sensors.read(args.devicelistfile)
	#Convert macs in devicelist file to Uppercase
	sensorsnew={}
	for key in sensors:
		sensorsnew[key.upper()] = sensors[key]
	sensors = sensorsnew

	#loop through sensors to generate key
	sensorsnew=sensors
	for sensor in sensors:
		if "decryption" in sensors[sensor]:
			if sensors[sensor]["decryption"][0] == "k":
				sensorsnew[sensor]["key"] = sensors[sensor]["decryption"][1:]
				#print(sensorsnew[sensor]["key"])
	sensors = sensorsnew

if args.onlydevicelist and not args.devicelistfile:
	print("Error: --onlydevicelist requires --devicelistfile <devicelistfile>")
	os._exit(1)

dev_id = args.interface  # the bluetooth device is hci0
toggle_device(dev_id, True)

sensor_cache = {}

try:
	sock = bluez.hci_open_dev(dev_id)
except:
	print("Error: cannot open bluetooth device %i" % dev_id)
	raise

enable_le_scan(sock, filter_duplicates=False)

sensor_cache = {} #for BTHome v2 format, since battery and temperature/humidity are sent in differenct packets :(
try:
	prev_data = None

	# globaler Cache (z.B. oben in deinem Script definieren)


	def decode_data_bthome_pvvx(mac, adv_type, data_str, rssi, measurement):

		if args.onlydevicelist and mac not in sensors:
			return
		preamble = "16d2fc40"  # unencrypted, BTHome v2
		packet_start = data_str.find(preamble)
		if packet_start == -1:
			return

		offset = packet_start + len(preamble)
		payload = data_str[offset:]
		#print(">>> stripped payload:", payload)

		temperature = None
		humidity = None
		voltage = None
		battery = None
		print("BLE packet - BTHome : %s %02x %s %d" % (mac, adv_type, data_str, rssi))
		try:
			i = 0
			while i < len(payload):
				if i + 2 > len(payload):
					break
				type_id = payload[i:i+2]
				i += 2

				# Battery level (%)
				if type_id == "01":
					battery = int(payload[i:i+2], 16)
					i += 2

				# Temperature (sint16, x0.01 °C)
				elif type_id == "02":
					temp_raw = int.from_bytes(bytes.fromhex(payload[i:i+4]), byteorder="little", signed=True)
					temperature = temp_raw / 100.0
					i += 4

				# Humidity (uint16, x0.01 %)
				elif type_id == "03":
					hum_raw = int.from_bytes(bytes.fromhex(payload[i:i+4]), byteorder="little", signed=False)
					humidity = hum_raw / 100.0
					i += 4

				# Voltage (uint16, x0.001 V)
				elif type_id == "0c":
					volt_raw = int.from_bytes(bytes.fromhex(payload[i:i+4]), byteorder="little", signed=False)
					voltage = volt_raw / 1000.0
					i += 4

				else:
					# Unknown type, skip
					#print(f"Unknown Type: {type_id} → Value {payload[i:i+4]}")
					i += 2

			cached = sensor_cache.get(mac, {})

			if battery is not None:
				print("Packet type: Battery")
				cached["battery"] = battery
			
			if voltage is not None:       # pvvx firmware seems to have bug. In rare occasions battery-level paket is received, but without voltage
					cached["voltage"] = voltage
				
			if temperature is not None or humidity is not None:
				print("Packet type: Data")
				cached["temperature"] = temperature
				cached["humidity"] = humidity

			sensor_cache[mac] = cached

			if args.bthome_onlyfull_transmit:
				have_batt = ("battery" in cached) or ("voltage" in cached)
				have_env  = ("temperature" in cached) or ("humidity" in cached)
				if not (have_batt and have_env): #data not complete yet
					return

			measurement.temperature = cached.get("temperature", 0)
			measurement.humidity = cached.get("humidity", 0)
			measurement.voltage = cached.get("voltage", 0)
			measurement.battery = cached.get("battery", 0)
			measurement.rssi = rssi

			return measurement

		except Exception as e:
			print("Fehler beim Parsen:", e)
			return







	def decode_data_atc(mac, adv_type, data_str, rssi, measurement):
		preeamble = "161a18"
		packetStart = data_str.find(preeamble)
		if (packetStart == -1):
			return
		offset = packetStart + len(preeamble)
		strippedData_str = data_str[offset:offset+26] #if shorter will just be shorter then 13 Bytes
		strippedData_str = data_str[offset:] #if shorter will just be shorter then 13 Bytes
		macStr = mac.replace(":","").upper()
		dataIdentifier = data_str[(offset-4):offset].upper()

		batteryVoltage=None

		if(dataIdentifier == "1A18") and not args.onlydevicelist or (mac in sensors) and (len(strippedData_str) in (16, 22, 26, 30)): #only Data from ATC devices
			if len(strippedData_str) == 30: #custom format, next-to-last ist adv number
				advNumber = strippedData_str[-4:-2]
			else:
				advNumber = strippedData_str[-2:] #last data in packet is adv number
			if macStr in advCounter:
				lastAdvNumber = advCounter[macStr]
			else:
				lastAdvNumber = None
			if lastAdvNumber == None or lastAdvNumber != advNumber:

				if len(strippedData_str) == 26: #ATC1441 Format
					print("BLE packet - ATC1441: %s %02x %s %d" % (mac, adv_type, data_str, rssi))
					advCounter[macStr] = advNumber
					#temperature = int(data_str[12:16],16) / 10.    # this method fails for negative temperatures
					temperature = int.from_bytes(bytearray.fromhex(strippedData_str[12:16]),byteorder='big',signed=True) / 10.
					humidity = int(strippedData_str[16:18], 16)
					batteryVoltage = int(strippedData_str[20:24], 16) / 1000
					batteryPercent = int(strippedData_str[18:20], 16)

				elif len(strippedData_str) == 30: #Custom format
					print("BLE packet - Custom: %s %02x %s %d" % (mac, adv_type, data_str, rssi))
					advCounter[macStr] = advNumber
					temperature = int.from_bytes(bytearray.fromhex(strippedData_str[12:16]),byteorder='little',signed=True) / 100.
					humidity = int.from_bytes(bytearray.fromhex(strippedData_str[16:20]),byteorder='little',signed=False) / 100.
					batteryVoltage = int.from_bytes(bytearray.fromhex(strippedData_str[20:24]),byteorder='little',signed=False) / 1000.
					batteryPercent =  int.from_bytes(bytearray.fromhex(strippedData_str[24:26]),byteorder='little',signed=False)

				elif len(strippedData_str) == 22 or len(strippedData_str) == 16: #encrypted: length 22/11 Bytes on custom format, 16/8 Bytes on ATC1441 Format
					if macStr in advCounter:
						lastData = advCounter[macStr]
					else:
						lastData = None

					if lastData == None or lastData != strippedData_str:
						print("BLE packet - Encrypted: %s %02x %s %d, length: %d" % (mac, adv_type, data_str, rssi, len(strippedData_str)/2))
						advCounter[macStr] = strippedData_str
						if mac in sensors and "key" in sensors[mac]:
							bindkey = bytes.fromhex(sensors[mac]["key"])
							macReversed=""
							for x in range(-1,-len(macStr),-2):
								macReversed += macStr[x-1] + macStr[x]
							macReversed = bytes.fromhex(macReversed.lower())
							#print("New encrypted format, MAC:" , macStr, "Reversed: ", macReversed)
							lengthHex=data_str[offset-8:offset-6]
							#lengthHex="0b"
							ret = cryptoFunctions.decrypt_aes_ccm(bindkey,macReversed,bytes.fromhex(lengthHex + "161a18" + strippedData_str))
							if ret == None: #Error decrypting
								print("\n")
								return
							#temperature, humidity, batteryPercent = cryptoFunctions.decrypt_aes_ccm(bindkey,macReversed,bytes.fromhex(lengthHex + "161a18" + strippedData_str))
							temperature, humidity, batteryPercent = ret
						else:
							print("Warning: No key provided for sensor:", mac,"\n")
							return
					else:
						return #repeated packet
				else: #no fitting packet
					return

			else: #Packet is just repeated
				return

			measurement.battery = batteryPercent
			measurement.humidity = humidity
			measurement.temperature = temperature
			measurement.voltage = batteryVoltage if batteryVoltage != None else 0
			measurement.rssi = rssi
			return measurement

	def decode_data_lywsdcgq(mac, adv_type, data_str, rssi, measurement):
		preeamble = "5020aa01"
		packetStart = data_str.find(preeamble)
		if (packetStart == -1):
			return
		offset = packetStart + len(preeamble)
		strippedData_str = data_str[offset:offset+28]
		strippedData_str = data_str[offset:]
		macStr = mac.replace(":","").upper()
		dataIdentifier = data_str[(offset+14):(offset+16)].upper()

		if(dataIdentifier == "0D") and not args.onlydevicelist or (dataIdentifier == "0D" and mac in sensors) and len(strippedData_str) == 28:
			print("BLE packet - lywsdcgq 0D: %s %02x %s %d" % (mac, adv_type, data_str, rssi))
			temperature = int.from_bytes(bytearray.fromhex(strippedData_str[20:24]),byteorder='little',signed=True) / 10.
			humidity = int.from_bytes(bytearray.fromhex(strippedData_str[24:28]),byteorder='little',signed=True) / 10.

			measurement.humidity = humidity
			measurement.temperature = temperature
			measurement.rssi = rssi
			return measurement

		elif(dataIdentifier == "06") and not args.onlydevicelist or (dataIdentifier == "06" and mac in sensors) and len(strippedData_str) == 24:
			print("BLE packet - lywsdcgq 06: %s %02x %s %d" % (mac, adv_type, data_str, rssi))
			humidity = int.from_bytes(bytearray.fromhex(strippedData_str[20:24]),byteorder='little',signed=True) / 10.

			measurement.humidity = humidity
			measurement.rssi = rssi
			return measurement

		elif(dataIdentifier == "04") and not args.onlydevicelist or (dataIdentifier == "04" and mac in sensors) and len(strippedData_str) == 24:
			print("BLE packet - lywsdcgq 04: %s %02x %s %d" % (mac, adv_type, data_str, rssi))
			temperature = int.from_bytes(bytearray.fromhex(strippedData_str[20:24]),byteorder='little',signed=True) / 10.

			measurement.temperature = temperature
			measurement.rssi = rssi
			return measurement

		elif(dataIdentifier == "0A") and not args.onlydevicelist or (dataIdentifier == "0A" and mac in sensors) and len(strippedData_str) == 22:
			print("BLE packet - lywsdcgq 0A: %s %02x %s %d" % (mac, adv_type, data_str, rssi))
			batteryPercent = int.from_bytes(bytearray.fromhex(strippedData_str[20:22]),byteorder='little',signed=False)

			measurement.battery = batteryPercent
			measurement.rssi = rssi
			return measurement

	# Tested with Qingping CGG1 and CGDK2
	def decode_data_qingping(mac, adv_type, data_str, rssi, measurement):
		preeamble = "cdfd88"
		packetStart = data_str.find(preeamble)
		if (packetStart == -1):
			return
		offset = packetStart + len(preeamble)
		strippedData_str = data_str[offset:offset+32]
		macStr = mac.replace(":","").upper()
		dataIdentifier = data_str[(offset-2):offset].upper()

		if(dataIdentifier == "88") and not args.onlydevicelist or (dataIdentifier == "88" and mac in sensors) and len(strippedData_str) == 32:
			print("BLE packet - Qingping: %s %02x %s %d" % (mac, adv_type, data_str, rssi))
			temperature = int.from_bytes(bytearray.fromhex(strippedData_str[18:22]),byteorder='little',signed=True) / 10.
			humidity = int.from_bytes(bytearray.fromhex(strippedData_str[22:26]),byteorder='little',signed=True) / 10.
			batteryPercent = int(strippedData_str[30:32], 16)

			measurement.battery = batteryPercent
			measurement.humidity = humidity
			measurement.temperature = temperature
			measurement.rssi = rssi
			return measurement

	def le_advertise_packet_handler(mac, adv_type, data, rssi):
		global lastBLEPacketReceived
		if args.watchdogtimer:
			lastBLEPacketReceived = time.time()
		lastBLEPacketReceived = time.time()
		data_str = raw_packet_to_str(data)

		global measurements
		measurement = Measurement(0,0,0,0,0,0,0,0)
		measurement = (
			decode_data_atc(mac, adv_type, data_str, rssi, measurement)
			or
			decode_data_lywsdcgq(mac, adv_type, data_str, rssi, measurement)
			or
			decode_data_qingping(mac, adv_type, data_str, rssi, measurement)
			or
			decode_data_bthome_pvvx(mac, adv_type, data_str, rssi, measurement)
		)

		if measurement:
			if args.influxdb == 1:
				measurement.timestamp = int((time.time() // 10) * 10)
			else:
				measurement.timestamp = int(time.time())

			if args.round:
				measurement.temperature=round(measurement.temperature,1)
				measurement.humidity=round(measurement.humidity,1)

			if mac in sensors and "sensorname" in sensors[mac]:
				print("Sensorname:",  sensors[mac]["sensorname"])

			print("Temperature: ", measurement.temperature)
			print("Humidity: ", measurement.humidity)
			if measurement.voltage != None:
				print ("Battery voltage:", measurement.voltage,"V")
			print ("RSSI:", rssi, "dBm")
			print ("Battery:", measurement.battery,"%")
			
			currentMQTTTopic = MQTTTopic
			if mac in sensors:
				try:
					measurement.sensorname = sensors[mac]["sensorname"]
				except:
					measurement.sensorname = mac
				if "offset1" in sensors[mac] and "offset2" in sensors[mac] and "calpoint1" in sensors[mac] and "calpoint2" in sensors[mac]:
					measurement.humidity = calibrateHumidity2Points(measurement.humidity,int(sensors[mac]["offset1"]),int(sensors[mac]["offset2"]),int(sensors[mac]["calpoint1"]),int(sensors[mac]["calpoint2"]))
					print ("Humidity calibrated (2 points calibration): ", measurement.humidity)
				elif "humidityOffset" in sensors[mac]:
					measurement.humidity = measurement.humidity + int(sensors[mac]["humidityOffset"])
					print ("Humidity calibrated (offset calibration): ", measurement.humidity)
				if "topic" in sensors[mac]:
					currentMQTTTopic=sensors[mac]["topic"]
			else:
				measurement.sensorname = mac
			
			if measurement.calibratedHumidity == 0:
				measurement.calibratedHumidity = measurement.humidity

			if args.callback or args.httpcallback:
				measurements.append(measurement)

			if args.mqttconfigfile:
				jsonString=buildJSONString(measurement)
				myMQTTPublish(currentMQTTTopic,jsonString)
				#MQTTClient.publish(currentMQTTTopic,jsonString,1)

			#print("Length:", len(measurements))
			print("")

	if  args.watchdogtimer:
		keepingLEScanRunningThread = threading.Thread(target=keepingLEScanRunning)
		keepingLEScanRunningThread.start()
		logging.debug("keepingLEScanRunningThread started")



	# Blocking call (the given handler will be called each time a new LE
	# advertisement packet is detected)
	parse_le_advertising_events(sock,
								handler=le_advertise_packet_handler,
								debug=False)
except KeyboardInterrupt:
	disable_le_scan(sock)
