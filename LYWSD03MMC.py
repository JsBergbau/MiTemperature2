#!/usr/bin/python3 -u
#!/home/openhabian/Python3/Python-3.7.4/python -u
#-u to unbuffer output. Otherwise when calling with nohup or redirecting output things are printed very lately or would even mixup

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

	def __eq__(self, other): #rssi may be different
		if self.temperature == other.temperature and self.humidity == other.humidity and self.calibratedHumidity == other.calibratedHumidity and self.battery == other.battery and self.voltage == other.voltage and self.sensorname == other.sensorname:
			return True
		else:
			return False

measurements=deque()
#globalBatteryLevel=0
previousMeasurement=Measurement(0,0,0,0,0,0,0,0)
identicalCounter=0

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
	

def thread_SendingData():
	global previousMeasurement
	global measurements
	path = os.path.dirname(os.path.abspath(__file__))
	while True:
		try:
			mea = measurements.popleft()
			if (mea == previousMeasurement and identicalCounter < args.skipidentical): #only send data when it has changed or X identical data has been skipped, ~10 pakets per minute, 50 pakets --> writing at least every 5 minutes
				print("Measurements are identical don't send data\n")
				identicalCounter+=1
				continue
			identicalCounter=0
			fmt = "sensorname,temperature,humidity,voltage" #don't try to seperate by semicolon ';' os.system will use that as command seperator
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
			if (ret != 0):
					measurements.appendleft(mea) #put the measurement back
					print ("Data couln't be send to Callback, retrying...")
					time.sleep(5) #wait before trying again
			else: #data was sent
				previousMeasurement=Measurement(mea.temperature,mea.humidity,mea.voltage,mea.calibratedHumidity,mea.battery,0) #using copy or deepcopy requires implementation in the class definition

		except IndexError:
			#print("Keine Daten")
			time.sleep(1)
		except Exception as e:
			print(e)
			print(traceback.format_exc())

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
	b = p2y - m * p2x #would be more efficient to do this calculations only once
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
				#print("Temperatur unrounded: " + str(temp
				
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
			if args.battery:
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

			if(args.callback):
				measurements.append(measurement)
		

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

# Main loop --------
parser=argparse.ArgumentParser(allow_abbrev=False)
parser.add_argument("--device","-d", help="Set the device MAC-Address in format AA:BB:CC:DD:EE:FF",metavar='AA:BB:CC:DD:EE:FF')
parser.add_argument("--battery","-b", help="Get estimated battery level", metavar='', type=int, nargs='?', const=1)
parser.add_argument("--count","-c", help="Read/Receive N measurements and then exit script", metavar='N', type=int)
parser.add_argument("--interface","-i", help="Specifiy the interface number to use, e.g. 1 for hci1", metavar='N', type=int, default=0)
parser.add_argument("--unreachable-count","-urc", help="Exit after N unsuccessful connection tries", metavar='N', type=int, default=0)


rounding = parser.add_argument_group("Rounding and debouncing")
rounding.add_argument("--round","-r", help="Round temperature to one decimal place",action='store_true')
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
callbackgroup.add_argument("--name","-n", help="Give this sensor a name reported to the callback script")
callbackgroup.add_argument("--skipidentical","-skip", help="N consecutive identical measurements won't be reported to callbackfunction",metavar='N', type=int, default=0)
callbackgroup.add_argument("--influxdb","-infl", help="Optimize for writing data to influxdb,1 timestamp optimization, 2 integer optimization",metavar='N', type=int, default=0)

atcgroup = parser.add_argument_group("ATC mode related arguments")
atcgroup.add_argument("--atc","-a", help="Read the data of devices with custom ATC firmware flashed",action='store_true')
atcgroup.add_argument("--watchdogtimer","-wdt",metavar='X', type=int, help="Re-enable scanning after not receiving any BLE packet after X seconds")
atcgroup.add_argument("--devicelistfile","-df",help="Specify a device list file giving further details to devices")
atcgroup.add_argument("--onlydevicelist","-odl", help="Only read devices which are in the device list file",action='store_true')
atcgroup.add_argument("--rssi","-rs", help="Report RSSI via callback",action='store_true')


args=parser.parse_args()
if args.device:
	if re.match("[0-9a-fA-F]{2}([:]?)[0-9a-fA-F]{2}(\\1[0-9a-fA-F]{2}){4}$",args.device):
		adress=args.device
	else:
		print("Please specify device MAC-Address in format AA:BB:CC:DD:EE:FF")
		os._exit(1)
elif not args.atc:
	parser.print_help()
	os._exit(1)

if args.TwoPointCalibration:
	if(not(args.calpoint1 and args.offset1 and args.calpoint2 and args.offset2)):
		print("In 2 Point calibration you have to enter 4 points")
		os._exit(1)
	elif(args.offset):
		print("Offset calibration and 2 Point calibration can't be used together")
		os._exit(1)
if not args.name:
	args.name = args.device

if args.callback:
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
				print("Maximum numbers of unsuccessful connections reaches, exiting")
				os._exit(0)
			time.sleep(1)
			logging.debug(e)
			logging.debug(traceback.format_exc())		
			
		print ("Waiting...")
		# Perhaps do something else here

elif args.atc:
	print("Script started in ATC Mode")
	print("----------------------------")
	print("In this mode all devices within reach are read out, unless a namefile and --namefileonlydevices is specified.")
	print("Also --name Argument is ignored, if you require names, please use --namefile.")
	print("In this mode rounding and debouncing are not available, since ATC firmware sends out only one decimal place.")
	print("ATC mode usually requires root rights. If you want to use it with normal user rights, \nplease execute \"sudo setcap cap_net_raw,cap_net_admin+eip $(eval readlink -f `which python3`)\"")
	print("You have to redo this step if you upgrade your python version.")
	print("----------------------------")

	import sys
	import bluetooth._bluetooth as bluez

	from bluetooth_utils import (toggle_device,
								enable_le_scan, parse_le_advertising_events,
								disable_le_scan, raw_packet_to_str)

	advCounter=dict() 
	sensors = dict()
	if args.devicelistfile:
		import configparser
		if not os.path.exists(args.devicelistfile):
			print ("Error specified device list file '",args.devicelistfile,"' not found")
			os._exit(1)
		sensors = configparser.ConfigParser()
		sensors.read(args.devicelistfile)

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
			#print("reveived BLE packet")
			data_str = raw_packet_to_str(data)
			ATCPaketMAC = data_str[10:22].upper()
			macStr = mac.replace(":","").upper() 
			atcIdentifier = data_str[6:10].upper()
			if(atcIdentifier == "1A18" and ATCPaketMAC == macStr) and not args.onlydevicelist or (atcIdentifier == "1A18" and mac in sensors): #only Data from ATC devices, double checked
				advNumber = data_str[-2:]
				if macStr in advCounter:
					lastAdvNumber = advCounter[macStr]
				else:
					lastAdvNumber = None
				if lastAdvNumber == None or lastAdvNumber != advNumber:
					advCounter[macStr] = advNumber
					print("BLE packet: %s %02x %s %d" % (mac, adv_type, data_str, rssi))
					#print("AdvNumber: ", advNumber)
					#temp = data_str[22:26].encode('utf-8')
					#temperature = int.from_bytes(bytearray.fromhex(data_str[22:26]),byteorder='big') / 10.
					global measurements
					measurement = Measurement(0,0,0,0,0,0,0,0)
					if args.influxdb == 1:
						measurement.timestamp = int((time.time() // 10) * 10)
					else:
						measurement.timestamp = int(time.time())


					#temperature = int(data_str[22:26],16) / 10.
					temperature = int.from_bytes(bytearray.fromhex(data_str[22:26]),byteorder='big',signed=True) / 10.
					print("Temperature: ", temperature)
					humidity = int(data_str[26:28], 16)
					print("Humidity: ", humidity)
					batteryVoltage = int(data_str[30:34], 16) / 1000
					print ("Battery voltage:", batteryVoltage,"V")
					print ("RSSI:", rssi, "dBm")

					if args.battery:
						batteryPercent = int(data_str[28:30], 16)
						print ("Battery:", batteryPercent,"%")
						measurement.battery = batteryPercent
					measurement.humidity = humidity
					measurement.temperature = temperature
					measurement.voltage = batteryVoltage
					measurement.rssi = rssi

					if mac in sensors:
						try:
							measurement.sensorname = sensors[mac]["sensorname"]
						except:
							measurement.sensorname = mac
						if "offset1" in sensors[mac] and "offset2" in sensors[mac] and "calpoint1" in sensors[mac] and "calpoint2" in sensors[mac]:
							measurement.humidity = calibrateHumidity2Points(humidity,int(sensors[mac]["offset1"]),int(sensors[mac]["offset2"]),int(sensors[mac]["calpoint1"]),int(sensors[mac]["calpoint2"]))
							print ("Humidity calibrated (2 points calibration): ", measurement.humidity)
						elif "humidityOffset" in sensors[mac]:
							measurement.humidity = humidity + int(sensors[mac]["humidityOffset"])
							print ("Humidity calibrated (offset calibration): ", measurement.humidity)
					else:
						measurement.sensorname = mac
					if(args.callback):
						measurements.append(measurement)
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
