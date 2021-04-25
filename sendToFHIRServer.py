#!/usr/bin/env python3

#This script is contributed by luckfamousa, see https://github.com/JsBergbau/MiTemperature2/issues/82
#Thank you very much for your support

import sys, json
import hashlib
from datetime import datetime
import requests

# install dependency `pip install fhir.resources`
# in fact you do not really need this because we just use it for formal validation of our FHIR resources
# which should happen on your FHIR server anyways
from fhir.resources.observation import Observation

# you need to fill in your specific configuration here
fhirServer = "https://myfhirserver.io/R4"
token = "you still need to implement the specific authentication and authorization mechanism of your specific FHIR server"

# this will let the FHIR server autogenerate a logical ID for your resource
def postFHIR(obj):
  headers = {
    "Authorization": "Bearer {}".format(token),
    "Content-Type": "application/fhir+json"
  }
  return requests.post("{}/{}".format(fhirServer, type(obj).__name__), data=obj.json(), headers=headers)

# this tells the FHIR server to accept the logical ID you specified.
def putFHIR(obj):
  headers = {
    "Authorization": "Bearer {}".format(token),
    "Content-Type": "application/fhir+json"
  }
  return requests.put("{}/{}/{}".format(fhirServer, type(obj).__name__, obj.id), data=obj.json(), headers=headers) 

# modify if you have configured different parameters
device = sys.argv[2]
temperature = float(sys.argv[3])
humidity = int(sys.argv[4])
battery = float(sys.argv[5])
timestamp = int(sys.argv[6])

# encode measurements in a FHIR Observation resource 
# see: https://www.hl7.org/fhir/observation.html
obsj = {
  "resourceType": "Observation",
  "code": {
    "coding": [{
      "system": "https://github.com/pvvx/ATC_MiThermometer",
      "code": "LYWSD03MMC"
  }]},
  "status": "final",
  "effectiveDateTime": datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%dT%H:%M:%SZ'),
  "component": [
    {
      "code": {
        "coding": [{
          "system": "http://loinc.org",
          "code": "60832-3",
          "display": "Room temperature"
      }]},
      "valueQuantity": {
        "value": temperature,
        "unit": "Celsius",
        "system": "http://unitsofmeasure.org",
        "code": "Cel"
      }
    },
    {
      "code": {
        "coding": [{
          "system": "http://loinc.org",
          "code": "65643-9",
          "display": "Room humidity"
      }]},
      "valueQuantity": {
        "value": humidity,
        "unit": "%",
        "system": "http://unitsofmeasure.org",
        "code": "%"
      }
    },
    {
      "code": {
        "coding": [{
          "system": "http://loinc.org",
          "code": "LP6802-5",
          "display": "Sensor battery"
      }]},
      "valueQuantity": {
        "value": battery,
        "unit": "Volt",
        "system": "http://unitsofmeasure.org",
        "code": "V"
      }
    }
  ],
  # This line assumes that you have previously created the sensor as a device in the FHIR server 
  # and calculated its logical ID as a hash from the MAC address, as shown here.
  # You could do that for example by `putFHIR(createDevice(device))`
  "device": {
    "reference": "Device/{}".format(hashlib.sha256(device.encode("utf-8")).hexdigest())
  }
}

def createDevice(mac):
  devj = {
    "resourceType": "Device",
    "id": hashlib.sha256(mac.encode("utf-8")).hexdigest(),
    "identifier": [{
      "system": "https://github.com/pvvx/ATC_MiThermometer",
      "value": mac
    }],
    "status": "active",
    "deviceName": [{
      "name": "Xiaomi Mijia Smart Bluetooth Thermometer & Hygrometer measurement",
      "type": "user-friendly-name"
    },{
      "name": "LYWSD03MMC",
      "type": "model-name"
    }],
    "type": {
      "coding": [{
        "system": "http://snomed.info/sct",
        "code": "27991004"
      },{
        "system": "http://snomed.info/sct",
        "code": "470090000"
      }
    ]}
  }
  return Device.parse_obj(devj)

# send to FHIR server and print verbose output for debugging
response = postFHIR(Observation.parse_obj(obsj))
print(response.__dict__)
