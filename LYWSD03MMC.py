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
			#print(data)
		except:
			print("Fehler")
		


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
args=parser.parse_args()
if args.device:
	if re.match("[0-9a-fA-F]{2}([:]?)[0-9a-fA-F]{2}(\\1[0-9a-fA-F]{2}){4}$",args.device):
		adress=args.device
	else:
		print("Please specify device MAC-Adress in format AA:BB:CC:DD:EE:FF")
		os._exit(1)
else:
	print("Please specify device address")
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
