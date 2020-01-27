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
	calibratedHumidity: int = 0
	battery: int = 0
	timestamp: int = 0

	def __eq__(self, other):
		if self.temperature == other.temperature and self.humidity == other.humidity and self.calibratedHumidity == other.calibratedHumidity and self.battery == other.battery:
			return  True
		else:
			return False

measurements=deque()
globalBatteryLevel=0
previousMeasurement=Measurement(0,0,0,0)
identicalCounter=0

def signal_handler(sig, frame):
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
			fmt = "sensorname,temperature,humidity" #don't try to seperate by semicolon ';' os.system will use that as command seperator
			params = args.name + " " + str(mea.temperature) + " " + str(mea.humidity)
			if (args.TwoPointCalibration or args.offset): #would be more efficient to generate fmt only once
				fmt +=",humidityCalibrated"
				params += " " + str(mea.calibratedHumidity)
			if (args.battery):
				fmt +=",batteryLevel"
				params += " " + str(mea.battery)
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
				previousMeasurement=Measurement(mea.temperature,mea.humidity,mea.calibratedHumidity,mea.battery,0) #using copy or deepcopy requires implementation in the class definition

		except IndexError:
			#print("Keine Daten")
			time.sleep(1)
		except Exception as e:
			print(e)
			print(traceback.format_exc())

mode="round"
class MyDelegate(btle.DefaultDelegate):
	def __init__(self, params):
		btle.DefaultDelegate.__init__(self)
		# ... initialise here
	
	def handleNotification(self, cHandle, data):
		global measurements
		try:
			measurement = Measurement(0,0,0,0,0)
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
			measurement.temperature = temp
			measurement.humidity = humidity

			if args.offset:
				humidityCalibrated = humidity + args.offset
				print("Calibrated humidity: " + str(humidityCalibrated))
				measurement.calibratedHumidity = humidityCalibrated

			if args.TwoPointCalibration:
				offset1=args.offset1
				offset2=args.offset2
				p1y=args.calpoint1
				p2y=args.calpoint2
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
				print("Calibrated humidity: " + str(humidityCalibrated))
				measurement.calibratedHumidity = humidityCalibrated

			if args.battery:
				measurement.battery = globalBatteryLevel

			measurements.append(measurement)

		except Exception as e:
			print("Fehler")
			print(e)
			print(traceback.format_exc())
		
# Initialisation  -------

def connect():
	p = btle.Peripheral(adress)	
	val=b'\x01\x00'
	p.writeCharacteristic(0x0038,val,True)
	p.withDelegate(MyDelegate("abc"))
	return p

# Main loop --------
parser=argparse.ArgumentParser()
parser.add_argument("--device","-d", help="Set the device MAC-Address in format AA:BB:CC:DD:EE:FF",metavar='AA:BB:CC:DD:EE:FF')
parser.add_argument("--battery","-b", help="Read batterylevel every Nth update", metavar='N', type=int)
parser.add_argument("--count","-c", help="Read/Receive N measurements and then exit script", metavar='N', type=int)

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

callbackgroup = parser.add_argument_group("Callback related functions")
callbackgroup.add_argument("--callback","-call", help="Pass the path to a program/script that will be called on each new measurement")
callbackgroup.add_argument("--name","-n", help="Give this sensor a name reported to the callback script")
callbackgroup.add_argument("--skipidentical","-skip", help="N consecutive identical measurements won't be reported to callbackfunction",metavar='N', type=int, default=0)

args=parser.parse_args()
if args.device:
	if re.match("[0-9a-fA-F]{2}([:]?)[0-9a-fA-F]{2}(\\1[0-9a-fA-F]{2}){4}$",args.device):
		adress=args.device
	else:
		print("Please specify device MAC-Address in format AA:BB:CC:DD:EE:FF")
		os._exit(1)
else:
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

p=btle.Peripheral()
cnt=0

if args.callback:
	dataThread = threading.Thread(target=thread_SendingData)
	dataThread.start()
	
signal.signal(signal.SIGINT, signal_handler)	
connected=False
#logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.ERROR)
logging.debug("Debug: Starting script...")
pid=os.getpid()	
bluepypid=None
unconnectedTime=None

watchdogThread = threading.Thread(target=watchDog_Thread)
watchdogThread.start()
logging.debug("watchdogThread startet")

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
			
		if args.battery:
				if(cnt % args.battery == 0):
					batt=p.readCharacteristic(0x001b)
					batt=int.from_bytes(batt,byteorder="little")
					print("Battery-Level: " + str(batt))
					globalBatteryLevel = batt
			
			
		if p.waitForNotifications(2000):
			# handleNotification() was called
			
			cnt += 1
			if args.count is not None and cnt >= args.count:
				print(str(args.count) + " measurements collected. Exiting in a moment.")
				p.disconnect()
				time.sleep(5)
				os._exit(0)
			print("")
			continue
	except Exception as e:
		print("Connection lost")
		if connected is True: #First connection abort after connected
			unconnectedTime=int(time.time())
			connected=False
		time.sleep(1)
		logging.debug(e)
		logging.debug(traceback.format_exc())		
		
	print ("Waiting...")
	# Perhaps do something else here