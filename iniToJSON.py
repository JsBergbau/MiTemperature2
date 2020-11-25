#!/usr/bin/python3

import configparser
import argparse
import os
import json as JSON

parser = argparse.ArgumentParser(allow_abbrev=False)
parser.add_argument("--readfile", "-rf", help="Specify filename of ini-File to convert",
                    metavar='filename', required=True)
parser.add_argument("--writefile", "-wf", help="Specify filename of json-File to convert",
                    metavar='filename')	
args=parser.parse_args()

if not os.path.exists(args.readfile):
    print("Error specified device list file '",
          args.devicelistfile, "' not found")
    os._exit(1)
sensors = configparser.ConfigParser()
sensors.read(args.readfile)

json="{"
for sensor in sensors:
	if sensor == "DEFAULT":
		continue
	
	json +='"'+sensor+'" : {'
	for option in sensors.options(sensor):
		json += '"' + option +'" : '
		if option == "sensorname" or option[:-1] == "info":
			optionvalue = '"'+sensors[sensor][option] + '",'
		else:
			optionvalue = sensors[sensor][option] + ','
		json += optionvalue + ""
	json = json[:-1] + "},"
json = json[:-1] + "}"	

#print(json)

json=JSON.loads(json)

if args.writefile:
	output = open(args.writefile,"x")
	output.write(JSON.dumps(json, indent=4))
else:
	print(JSON.dumps(json, indent=4))