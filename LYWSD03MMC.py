#!/usr/bin/python3 -u
#!/home/openhabian/Python3/Python-3.7.4/python -u
#-u to unbuffer output. Otherwise when calling with nohup or redirecting output things are printed very lately or would even mixup

print("---------------------------------------------")
print("MiTemperature2 / ATC Thermometer version 3.1")
print("---------------------------------------------")

from bluepy import btle
import argparse
import os
import re
from dataclasses import dataclass
from collections import deque
import threading
import time
import signal
import traceback
import math
import logging
import json
import requests

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
			#in atc mode also exclude voltage as it changes often due to frequent measurements
			return True if args.atc else (self.voltage == other.voltage)
		else:
			return False

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
			print("Publishing:",topic+"/"+subtopic)
			MQTTClient.publish(topic + "/" + subtopic,messageDict[subtopic],0)
	if not mqttJSONDisabled:
		MQTTClient.publish(topic,jsonMessage,1)


def signal_handler(sig, frame):
	if args.atc:
		disable_le_scan(sock)	
	os._exit(0)
		
def watchDog_Thread():
	global unconnectedTime
	global connected
	global pid
	while True:
		logging.debug("watchdog_Thread")
		logging.debug("unconnectedTime : " + str(unconnectedTime))
		logging.debug("connected : " + str(connected))
		logging.debug("pid : " + str(pid))
		now = int(time.time())
		if (unconnectedTime is not None) and ((now - unconnectedTime) > 60): #could also check connected is False, but this is more fault proof
			pstree=os.popen("pstree -p " + str(pid)).read() #we want to kill only bluepy from our own process tree, because other python scripts have there own bluepy-helper process
			logging.debug("PSTree: " + pstree)
			try:
				bluepypid=re.findall(r'bluepy-helper\((.*)\)',pstree)[0] #Store the bluepypid, to kill it later
			except IndexError: #Should not happen since we're now connected
				logging.debug("Couldn't find pid of bluepy-helper")
			os.system("kill " + bluepypid)
			logging.debug("Killed bluepy with pid: " + str(bluepypid))
			unconnectedTime = now #reset unconnectedTime to prevent multiple killings in a row
		time.sleep(5)
	


sock = None #from ATC 
lastBLEPaketReceived = 0
BLERestartCounter = 1
def keepingLEScanRunning(): #LE-Scanning gets disabled sometimes, especially if you have a lot of BLE connections, this thread periodically enables BLE scanning again
	global BLERestartCounter
	while True:
		time.sleep(1)
		now = time.time()
		if now - lastBLEPaketReceived > args.watchdogtimer:
			print("Watchdog: Did not receive any BLE Paket within", int(now - lastBLEPaketReceived), "s. Restarting BLE scan. Count:", BLERestartCounter)
			disable_le_scan(sock)
			enable_le_scan(sock, filter_duplicates=False)
			BLERestartCounter += 1
			print("")
			time.sleep(5) #give some time to take effect

mode="round"

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
parser=argparse.ArgumentParser(allow_abbrev=False)
parser.add_argument("--device","-d", help="Set the device MAC-Address in format AA:BB:CC:DD:EE:FF",metavar='AA:BB:CC:DD:EE:FF')
parser.add_argument("--battery","-b", help="Get estimated battery level, in ATC-Mode: Get battery level from device", metavar='', type=int, nargs='?', const=1)
parser.add_argument("--interface","-i", help="Specifiy the interface number to use, e.g. 1 for hci1", metavar='N', type=int, default=0)
parser.add_argument("--mqttconfigfile","-mcf", help="specify a configurationfile for MQTT-Broker")


atcgroup = parser.add_argument_group("ATC mode related arguments")
atcgroup.add_argument("--atc","-a", help="Read the data of devices with custom ATC firmware flashed, use --battery to get battery level additionaly in percent",action='store_true')
atcgroup.add_argument("--watchdogtimer","-wdt",metavar='X', type=int, help="Re-enable scanning after not receiving any BLE packet after X seconds")
atcgroup.add_argument("--devicelistfile","-df",help="Specify a device list file giving further details to devices")
atcgroup.add_argument("--onlydevicelist","-odl", help="Only read devices which are in the device list file",action='store_true')
atcgroup.add_argument("--rssi","-rs", help="Report RSSI via callback",action='store_true')


args=parser.parse_args()

if args.devicelistfile or args.mqttconfigfile:
	import configparser

if args.mqttconfigfile:
	try:
		import paho.mqtt.client as mqtt
	except:
		print("Please install MQTT-Library via 'pip/pip3 install paho-mqtt'")
		exit(1)
	if not os.path.exists(args.mqttconfigfile):
		print ("Error MQTT config file '",args.mqttconfigfile,"' not found")
		os._exit(1)
	mqttConfig = configparser.ConfigParser()
	# print(mqttConfig.sections())
	mqttConfig.read(args.mqttconfigfile)
	broker = mqttConfig["MQTT"]["broker"]
	port = int(mqttConfig["MQTT"]["port"])
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
	# client.on_publish = MQTTOnPublish
	client.on_disconnect = MQTTOnDisconnect
	client.reconnect_delay_set(min_delay=1,max_delay=60)
	client.loop_start()
	client.username_pw_set(username,password)
	if len(lwt) > 0:
		print("Using lastwill with topic:",lwt,"and message:",lastwill)
		client.will_set(lwt,lastwill,qos=1)
	
	client.connect_async(broker,port)
	MQTTClient=client
	

if not args.atc:
	parser.print_help()
	os._exit(1)

signal.signal(signal.SIGINT, signal_handler)	

if args.atc:
	import sys
	import bluetooth._bluetooth as bluez

	from bluetooth_utils import (toggle_device,
								enable_le_scan, parse_le_advertising_events,
								disable_le_scan, raw_packet_to_str)

	advCounter=dict() 
	sensors = dict()
	if args.devicelistfile:
		#import configparser
		if not os.path.exists(args.devicelistfile):
			print ("Error specified device list file '",args.devicelistfile,"' not found")
			os._exit(1)
		sensors = configparser.ConfigParser()
		sensors.read(args.devicelistfile)
		#Convert macs in devicelist file to Uppercase
		sensorsnew={}
		for key in sensors:
			sensorsnew[key.upper()] = sensors[key]
		sensors = sensorsnew

	if args.onlydevicelist and not args.devicelistfile:
		print("Error: --onlydevicelist requires --devicelistfile <devicelistfile>")
		os._exit(1)

	dev_id = args.interface  # the bluetooth device is hci0
	toggle_device(dev_id, True)
	
	try:
		sock = bluez.hci_open_dev(dev_id)
	except:
		print("Cannot open bluetooth device %i" % dev_id)
		raise

	enable_le_scan(sock, filter_duplicates=False)

	try:
		prev_data = None

		def le_advertise_packet_handler(mac, adv_type, data, rssi):
			global lastBLEPaketReceived
			if args.watchdogtimer:
				lastBLEPaketReceived = time.time()
			lastBLEPaketReceived = time.time()
			data_str = raw_packet_to_str(data)
			preeamble = "10161a18"
			paketStart = data_str.find(preeamble)
			offset = paketStart + len(preeamble)
				#print("reveived BLE packet")+
			atcData_str = data_str[offset:offset+26]
			ATCPaketMAC = atcData_str[0:12].upper()
			macStr = mac.replace(":","").upper() 
			atcIdentifier = data_str[(offset-4):offset].upper()

			if(atcIdentifier == "1A18" and ATCPaketMAC == macStr) and not args.onlydevicelist or (atcIdentifier == "1A18" and mac in sensors) and len(atcData_str) == 26: #only Data from ATC devices, double checked
				advNumber = atcData_str[-2:]
				if macStr in advCounter:
					lastAdvNumber = advCounter[macStr]
				else:
					lastAdvNumber = None
				if lastAdvNumber == None or lastAdvNumber != advNumber:
					advCounter[macStr] = advNumber
					print("BLE packet: %s %02x %s (RSSI %d)" % (mac, adv_type, data_str, rssi))
					global measurements
					measurement = Measurement(0,0,0,0,0,0,0,0)
					measurement.timestamp = int(time.time())


					temperature = int.from_bytes(bytearray.fromhex(atcData_str[12:16]),byteorder='big',signed=True) / 10.
					print("Temperature: ", temperature)
					humidity = int(atcData_str[16:18], 16)
					print("Humidity: ", humidity)
					batteryVoltage = int(atcData_str[20:24], 16) / 1000
					print ("Battery voltage:", batteryVoltage,"V")
					print ("RSSI:", rssi, "dBm")

					batteryPercent = int(atcData_str[18:20], 16)
					print ("Battery:", batteryPercent,"%")
					measurement.battery = batteryPercent
					measurement.humidity = humidity
					measurement.temperature = temperature
					measurement.voltage = batteryVoltage
					measurement.rssi = rssi

					currentMQTTTopic = MQTTTopic
					if mac in sensors:
						try:
							measurement.sensorname = sensors[mac]["sensorname"]
						except:
							measurement.sensorname = mac
						if "topic" in sensors[mac]:
							currentMQTTTopic=sensors[mac]["topic"]
					else:
						measurement.sensorname = mac
					
					if measurement.calibratedHumidity == 0:
						measurement.calibratedHumidity = measurement.humidity

					if args.mqttconfigfile:
						jsonString=buildJSONString(measurement)
						myMQTTPublish(currentMQTTTopic,jsonString)

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
