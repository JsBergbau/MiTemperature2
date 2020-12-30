#!/usr/bin/env python3

import sys
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

PROMETHEUS_URL = "http://localhost:9091"

val_sensor = sys.argv[2]
val_temp = sys.argv[3]
val_hum = sys.argv[4]
val_bat = sys.argv[5]

registry = CollectorRegistry()

t = Gauge('temp_celsius', 'Temperature, celsius', registry=registry, labelnames=('sensor', ))
h = Gauge('humidity_pct', 'Humidity, percentage', registry=registry, labelnames=('sensor', ))
bv = Gauge('battery_voltage', 'Battery, voltage', registry=registry, labelnames=('sensor', ))

t.labels(val_sensor).set(val_temp)
h.labels(val_sensor).set(val_hum)
bv.labels(val_sensor).set(val_bat)

push_to_gateway(PROMETHEUS_URL, job='tempBatch', grouping_key={'sensor': val_sensor}, registry=registry)
