#!/usr/bin/python3

import configparser
import argparse
import os
import json as JSON

parser = argparse.ArgumentParser(allow_abbrev=False)
parser.add_argument("--readfile", "-rf", help="Specify filename of json-File to convert",
                    metavar='filename', required=True)
parser.add_argument("--writefile", "-wf", help="Specify filename of json-File to convert",
                    metavar='filename', required=True)
args = parser.parse_args()

if not os.path.exists(args.readfile):
    print("Error specified device list file '",
          args.devicelistfile, "' not found")
    os._exit(1)

with open (args.readfile,"r") as json_file:
	json=JSON.load(json_file)

# for key in json:
# 	print(key)
sensors = configparser.ConfigParser()
sensors.read_dict(json)
with open (args.writefile,"x") as ini_file:
	sensors.write(ini_file)