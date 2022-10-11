#!/usr/bin/env -S python3 -u
#-u to unbuffer output. Otherwise when calling with nohup or redirecting output things are printed very lately or would even mixup

print("---------------------------------------------")
print("MiTemperature2 / ATC Thermometer version 5.0")
print("---------------------------------------------")

readme="""

Please read README.md in this folder. Latest version is available at https://github.com/JsBergbau/MiTemperature2#readme
This file explains very detailed about the usage and covers everything you need to know as user.

"""

print(readme)


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
import ssl


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
			#in passive mode also exclude voltage as it changes often due to frequent measurements
			return True if args.passive else (self.voltage == other.voltage)
		else:
			return False

measurements=deque()
#globalBatteryLevel=0
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
	if args.passive:
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
					if (args.TwoPointCalibration or args.offset): #would be more efficient to generate fmt only once
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
						sensorname=mea.sensorname,
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
						r = requests.get(url, verify=False, timeout=1)
						r.raise_for_status()
					except requests.exceptions.RequestException as e:
						ret = 1

				if ret != 0:
					measurements.appendleft(mea) #put the measurement back
					print ("Data couln't be send to Callback, retrying...")
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
	#offset1=args.offset1
	#offset2=args.offset2
	#p1y=args.calpoint1
	#p2y=args.calpoint2
	p1y=calpoint1
	p2y=calpoint2
	p1x=p1y - offset1
	p2x=p2y - offset2
	m = (p1y - p2y) * 1.0 / (p1x - p2x) # y=mx+b
	#b = (p1x * p2y - p2x * p1y) * 1.0 / (p1y - p2y)
	b = p2y - m * p2x #would be more efficient to do these calculations only once
	humidityCalibrated=m*humidity + b
	if (humidityCalibrated > 100 ): #with correct calibration this should not happen
		humidityCalibrated = 100
	elif (humidityCalibrated < 0):
		humidityCalibrated = 0
	humidityCalibrated=int(round(humidityCalibrated,0))
	return humidityCalibrated


mode="round"
class MyDelegate(btle.DefaultDelegate):
	def __init__(self, params):
		btle.DefaultDelegate.__init__(self)
		# ... initialise here
	
	def handleNotification(self, cHandle, data):
		global measurements
		try:
			measurement = Measurement(0,0,0,0,0,0,0,0)
			if args.influxdb == 1:
				measurement.timestamp = int((time.time() // 10) * 10)
			else:
				measurement.timestamp = int(time.time())
			temp=int.from_bytes(data[0:2],byteorder='little',signed=True)/100
			#print("Temp received: " + str(temp))
			if args.round:
				#print("Temperature unrounded: " + str(temp
				
				if args.debounce:
					global mode
					temp*=10
					intpart = math.floor(temp)
					fracpart = round(temp - intpart,1)
					#print("Fracpart: " + str(fracpart))
					if fracpart >= 0.7:
						mode="ceil"
					elif fracpart <= 0.2: #either 0.8 and 0.3 or 0.7 and 0.2 for best even distribution
						mode="trunc"
					#print("Modus: " + mode)
					if mode=="trunc": #only a few times
						temp=math.trunc(temp)
					elif mode=="ceil":
						temp=math.ceil(temp)
					else:
						temp=round(temp,0)
					temp /=10.
					#print("Debounced temp: " + str(temp))
				else:
					temp=round(temp,1)
			humidity=int.from_bytes(data[2:3],byteorder='little')
			print("Temperature: " + str(temp))
			print("Humidity: " + str(humidity))
			voltage=int.from_bytes(data[3:5],byteorder='little') / 1000.
			print("Battery voltage:",voltage,"V")
			measurement.temperature = temp
			measurement.humidity = humidity
			measurement.voltage = voltage
			measurement.sensorname = args.name
			#if args.battery:
				#measurement.battery = globalBatteryLevel
			batteryLevel = min(int(round((voltage - 2.1),2) * 100), 100) #3.1 or above --> 100% 2.1 --> 0 %
			measurement.battery = batteryLevel
			print("Battery level:",batteryLevel)
				

			if args.offset:
				humidityCalibrated = humidity + args.offset
				print("Calibrated humidity: " + str(humidityCalibrated))
				measurement.calibratedHumidity = humidityCalibrated

			if args.TwoPointCalibration:
				humidityCalibrated= calibrateHumidity2Points(humidity,args.offset1,args.offset2, args.calpoint1, args.calpoint2)
				print("Calibrated humidity: " + str(humidityCalibrated))
				measurement.calibratedHumidity = humidityCalibrated

			if args.callback or args.httpcallback:
				measurements.append(measurement)

			if(args.mqttconfigfile):
				if measurement.calibratedHumidity == 0:
					measurement.calibratedHumidity = measurement.humidity
				jsonString=buildJSONString(measurement)
				myMQTTPublish(MQTTTopic,jsonString)
				#MQTTClient.publish(MQTTTopic,jsonString,1)


		except Exception as e:
			print("Fehler")
			print(e)
			print(traceback.format_exc())
		
# Initialisation  -------

def connect():
	#print("Interface: " + str(args.interface))
	p = btle.Peripheral(adress,iface=args.interface)	
	val=b'\x01\x00'
	p.writeCharacteristic(0x0038,val,True) #enable notifications of Temperature, Humidity and Battery voltage
	p.writeCharacteristic(0x0046,b'\xf4\x01\x00',True)
	p.withDelegate(MyDelegate("abc"))
	return p

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
parser.add_argument("--device","-d", help="Set the device MAC-Address in format AA:BB:CC:DD:EE:FF",metavar='AA:BB:CC:DD:EE:FF')
parser.add_argument("--battery","-b", help="Get estimated battery level, in passive mode: Get battery level from device", metavar='', type=int, nargs='?', const=1)
parser.add_argument("--count","-c", help="Read/Receive N measurements and then exit script", metavar='N', type=int)
parser.add_argument("--interface","-i", help="Specifiy the interface number to use, e.g. 1 for hci1", metavar='N', type=int, default=0)
parser.add_argument("--unreachable-count","-urc", help="Exit after N unsuccessful connection tries", metavar='N', type=int, default=0)
parser.add_argument("--mqttconfigfile","-mcf", help="specify a configurationfile for MQTT-Broker")


rounding = parser.add_argument_group("Rounding and debouncing")
rounding.add_argument("--round","-r", help="Round temperature to one decimal place (and in passive mode humidity to whole numbers)",action='store_true')
rounding.add_argument("--debounce","-deb", help="Enable this option to get more stable temperature values, requires -r option",action='store_true')

offsetgroup = parser.add_argument_group("Offset calibration mode")
offsetgroup.add_argument("--offset","-o", help="Enter an offset to the reported humidity value",type=int)

complexCalibrationGroup=parser.add_argument_group("2 Point Calibration")
complexCalibrationGroup.add_argument("--TwoPointCalibration","-2p", help="Use complex calibration mode. All arguments below are required",action='store_true')
complexCalibrationGroup.add_argument("--calpoint1","-p1", help="Enter the first calibration point",type=int)
complexCalibrationGroup.add_argument("--offset1","-o1", help="Enter the offset for the first calibration point",type=int)
complexCalibrationGroup.add_argument("--calpoint2","-p2", help="Enter the second calibration point",type=int)
complexCalibrationGroup.add_argument("--offset2","-o2", help="Enter the offset for the second calibration point",type=int)

callbackgroup = parser.add_argument_group("Callback related arguments")
callbackgroup.add_argument("--callback","-call", help="Pass the path to a program/script that will be called on each new measurement")
callbackgroup.add_argument("--httpcallback","-http", help="Pass the URL to a program/script that will be called on each new measurement")
callbackgroup.add_argument("--name","-n", help="Give this sensor a name reported to the callback script")
callbackgroup.add_argument("--skipidentical","-skip", help="N consecutive identical measurements won't be reported to callbackfunction",metavar='N', type=int, default=0)
callbackgroup.add_argument("--callback-interval","-int", help="Only invoke callbackfunction every N seconds, e.g. 600 = 10 minutes",type=int, default=0)
callbackgroup.add_argument("--influxdb","-infl", help="Optimize for writing data to influxdb,1 timestamp optimization, 2 integer optimization",metavar='N', type=int, default=0)

passivegroup = parser.add_argument_group("Passive mode related arguments")
passivegroup.add_argument("--passive","-p","--atc","-a", help="Read the data of devices based on BLE advertisements, use --battery to get battery level additionaly in percent",action='store_true')
passivegroup.add_argument("--watchdogtimer","-wdt",metavar='X', type=int, help="Re-enable scanning after not receiving any BLE packet after X seconds")
passivegroup.add_argument("--devicelistfile","-df",help="Specify a device list file giving further details to devices")
passivegroup.add_argument("--onlydevicelist","-odl", help="Only read devices which are in the device list file",action='store_true')
passivegroup.add_argument("--rssi","-rs", help="Report RSSI via callback",action='store_true')


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
	

if args.device:
	if re.match("[0-9a-fA-F]{2}([:]?)[0-9a-fA-F]{2}(\\1[0-9a-fA-F]{2}){4}$",args.device):
		adress=args.device
	else:
		print("Please specify device MAC address in format AA:BB:CC:DD:EE:FF")
		os._exit(1)
elif not args.passive:
	parser.print_help()
	os._exit(1)

if args.TwoPointCalibration:
	if(not(args.calpoint1 is not None and args.offset1 is not None
	       and args.calpoint2 is not None and args.offset2 is not None)):
		print("In 2 Point calibration you have to enter 4 points")
		os._exit(1)
	elif(args.offset):
		print("Offset calibration and 2 Point calibration can't be used together")
		os._exit(1)
if not args.name:
	args.name = args.device

if args.callback or args.httpcallback:
	dataThread = threading.Thread(target=thread_SendingData)
	dataThread.start()

signal.signal(signal.SIGINT, signal_handler)	

if args.device: 

	p=btle.Peripheral()
	cnt=0

	connected=False
	#logging.basicConfig(level=logging.DEBUG)
	logging.basicConfig(level=logging.ERROR)
	logging.debug("Debug: Starting script...")
	pid=os.getpid()	
	bluepypid=None
	unconnectedTime=None
	connectionLostCounter=0

	watchdogThread = threading.Thread(target=watchDog_Thread)
	watchdogThread.start()
	logging.debug("watchdogThread started")

	while True:
		try:
			if not connected:
				#Bluepy sometimes hangs and makes it even impossible to connect with gatttool as long it is running
				#on every new connection a new bluepy-helper is called
				#we now make sure that the old one is really terminated. Even if it hangs a simple kill signal was sufficient to terminate it
				# if bluepypid is not None:
					# os.system("kill " + bluepypid)
					# print("Killed possibly remaining bluepy-helper")
				# else:
					# print("bluepy-helper couldn't be determined, killing not allowed")
						
				print("Trying to connect to " + adress)
				p=connect()
				# logging.debug("Own PID: "  + str(pid))
				# pstree=os.popen("pstree -p " + str(pid)).read() #we want to kill only bluepy from our own process tree, because other python scripts have there own bluepy-helper process
				# logging.debug("PSTree: " + pstree)
				# try:
					# bluepypid=re.findall(r'bluepy-helper\((.*)\)',pstree)[0] #Store the bluepypid, to kill it later
				# except IndexError: #Should not happen since we're now connected
					# logging.debug("Couldn't find pid of bluepy-helper")				
				connected=True
				unconnectedTime=None
				
			# if args.battery:
					# if(cnt % args.battery == 0):
						# print("Warning the battery option is deprecated, Aqara device always reports 99 % battery")
						# batt=p.readCharacteristic(0x001b)
						# batt=int.from_bytes(batt,byteorder="little")
						# print("Battery-Level: " + str(batt))
						# globalBatteryLevel = batt
				
				
			if p.waitForNotifications(2000):
				# handleNotification() was called
				
				cnt += 1
				if args.count is not None and cnt >= args.count:
					print(str(args.count) + " measurements collected. Exiting in a moment.")
					p.disconnect()
					time.sleep(5)
					#It seems that sometimes bluepy-helper remains and thus prevents a reconnection, so we try killing our own bluepy-helper
					pstree=os.popen("pstree -p " + str(pid)).read() #we want to kill only bluepy from our own process tree, because other python scripts have there own bluepy-helper process
					bluepypid=0
					try:
						bluepypid=re.findall(r'bluepy-helper\((.*)\)',pstree)[0] #Store the bluepypid, to kill it later
					except IndexError: #Should normally occur because we're disconnected
						logging.debug("Couldn't find pid of bluepy-helper")
					if bluepypid != 0:
						os.system("kill " + bluepypid)
						logging.debug("Killed bluepy with pid: " + str(bluepypid))
					os._exit(0)
				print("")
				continue
		except Exception as e:
			print("Connection lost")
			connectionLostCounter +=1
			if connected is True: #First connection abort after connected
				unconnectedTime=int(time.time())
				connected=False
			if args.unreachable_count != 0 and connectionLostCounter >= args.unreachable_count:
				print("Maximum numbers of unsuccessful connections reached, exiting")
				os._exit(0)
			time.sleep(1)
			logging.debug(e)
			logging.debug(traceback.format_exc())		
			
		print ("Waiting...")
		# Perhaps do something else here

elif args.passive:
	print("Script started in passive mode")
	print("------------------------------")
	print("In this mode all devices within reach are read out, unless a devicelistfile and --onlydevicelist is specified.")
	print("Also --name Argument is ignored, if you require names, please use --devicelistfile.")
	print("In this mode debouncing is not available. Rounding option will round humidity and temperature to one decimal place.")
	print("Passive mode usually requires root rights. If you want to use it with normal user rights, \nplease execute \"sudo setcap cap_net_raw,cap_net_admin+eip $(eval readlink -f `which python3`)\"")
	print("You have to redo this step if you upgrade your python version.")
	print("----------------------------")

	import sys
	import bluetooth._bluetooth as bluez
	import cryptoFunctions

	from bluetooth_utils import (toggle_device,
								enable_le_scan, parse_le_advertising_events,
								disable_le_scan, raw_packet_to_str)

	advCounter=dict()
	#encryptedPacketStore=dict()
	sensors = dict()
	if args.devicelistfile:
		#import configparser
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
	
	try:
		sock = bluez.hci_open_dev(dev_id)
	except:
		print("Error: cannot open bluetooth device %i" % dev_id)
		raise

	enable_le_scan(sock, filter_duplicates=False)

	try:
		prev_data = None

		def decode_data_atc(mac, adv_type, data_str, rssi, measurement):
			preeamble = "161a18"
			packetStart = data_str.find(preeamble)
			offset = packetStart + len(preeamble)
			strippedData_str = data_str[offset:offset+26] #if shorter will just be shorter then 13 Bytes
			strippedData_str = data_str[offset:] #if shorter will just be shorter then 13 Bytes
			macStr = mac.replace(":","").upper()
			dataIdentifier = data_str[(offset-4):offset].upper()

			batteryVoltage=None

			if(dataIdentifier == "1A18") and not args.onlydevicelist or (dataIdentifier == "1A18" and mac in sensors) and (len(strippedData_str) in (16, 22, 26, 30)): #only Data from ATC devices
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
