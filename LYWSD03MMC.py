#!/usr/bin/python3

from bluepy import btle
import argparse
import os
import re


class MyDelegate(btle.DefaultDelegate):
	def __init__(self, params):
		btle.DefaultDelegate.__init__(self)
		# ... initialise here

	def handleNotification(self, cHandle, data):
		try:
			temp=int.from_bytes(data[0:2],byteorder='little')/100
			if args.round:
				#print("Temperatur unrounded: " + str(temp))
				temp=round(temp,1)
			humidity=int.from_bytes(data[2:3],byteorder='little')
			print("Temperature: " + str(temp))
			print("Humidity: " + str(humidity))

			if args.offset:
				humidityCalibrated = humidity + args.offset
				print("Calibrated humidity: " + str(humidityCalibrated))

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

			#print(data)
		except Exception as e:
			print("Fehler")
			print(e)
		


# Initialisation  -------

def connect():
	p = btle.Peripheral(adress)	
	val=b'\x01\x00'
	p.writeCharacteristic(0x0038,val,True)
	#print(val.hex())
	p.withDelegate(MyDelegate("abc"))
	return p

# Main loop --------
parser=argparse.ArgumentParser()
parser.add_argument("--device","-d", help="Set the device MAC-Adress in format AA:BB:CC:DD:EE:FF")
parser.add_argument("--battery","-b", help="Read batterylevel every x update", metavar='N', type=int)
parser.add_argument("--round","-r", help="Round temperature to one decimal place",action='store_true')

# parentgroup=parser.add_argument_group("Calibration")
# parentgroup.add_mutually_exclusive_group()

#calgroup = parser.add_mutually_exclusive_group()
offsetgroup = parser.add_argument_group("Offset calibration mode")
offsetgroup.add_argument("--offset","-o", help="Enter an offset to the humidity value read",type=int)
# calgroup.add_argument_group(offsetgroup)
# parentgroup.add_argument_group(offsetgroup)

complexCalibrationGroup=parser.add_argument_group("2 Point Calibration")
complexCalibrationGroup.add_argument("--TwoPointCalibration","-2p", help="Use complex calibration mode. All arguments below are required",action='store_true')
complexCalibrationGroup.add_argument("--calpoint1","-p1", help="Enter the first calibration point",type=int)
complexCalibrationGroup.add_argument("--offset1","-o1", help="Enter the offset for the first calibration point",type=int)
complexCalibrationGroup.add_argument("--calpoint2","-p2", help="Enter the second calibration point",type=int)
complexCalibrationGroup.add_argument("--offset2","-o2", help="Enter the offset for the second calibration point",type=int)
#
# calgroup.add_argument_group(complexCalibrationGroup)
# parentgroup.add_argument_group(complexCalibrationGroup)

args=parser.parse_args()
if args.device:
	if re.match("[0-9a-fA-F]{2}([:]?)[0-9a-fA-F]{2}(\\1[0-9a-fA-F]{2}){4}$",args.device):
		adress=args.device
	else:
		print("Please specify device MAC-Adress in format AA:BB:CC:DD:EE:FF")
		os._exit(1)
else:
	parser.print_help()
	# print("Please specify device address")
	os._exit(1)
if args.TwoPointCalibration:
	if(not(args.calpoint1 and args.offset1 and args.calpoint2 and args.offset2)):
		print("In 2 Point calibration you have to enter 4 points")
		os._exit(1)
	elif(args.offset):
		print("Offset calibration and 2 Point calibration can't be used together")
		os._exit(1)

p=btle.Peripheral()
cnt=0
while True:
	try:
		if p.waitForNotifications(2000):
			# handleNotification() was called
			if args.battery:
				#every = int(args.battery)
				if(cnt % args.battery == 0):
					batt=p.readCharacteristic(0x001b)
					batt=int.from_bytes(batt,byteorder="little")
					print("Battery-Level: " + str(batt))
			cnt += 1
			print("")
			continue
	except:
		print("Trying to connect to " + adress)
		p=connect()
		
	print ("Waiting...")
	# Perhaps do something else here
