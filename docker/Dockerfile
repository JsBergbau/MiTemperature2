FROM python:3.7.8

# http://bugs.python.org/issue19846
# > At the moment, setting "LANG=C" on a Linux system *fundamentally breaks Python 3*, and that's not OK.
ENV LANG C.UTF-8

#RUN apt-get -y --no-install-recommends install python-pip libglib2.0-dev
RUN apt-get update && apt-get install -y bluez bluetooth usbutils mosquitto mosquitto-clients && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
RUN /usr/local/bin/pip3.7 install bluepy && /usr/local/bin/pip3.7 install requests

COPY LYWSD03MMC.py LYWSD03MMC.py
COPY ble_scan_example.py ble_scan_example.py
COPY sendToMQTT.sh sendToMQTT.sh

#Change to the following line to match your needs
ENTRYPOINT /usr/local/bin/python3.7m LYWSD03MMC.py -d A4:C1:38:A3:70:35 -n a4c138a37035 --unreachable-count 10 -r -b 100 --skipidentical 50 -deb --callback sendToMQTT.sh

# start the created image with sudo docker run --net=host -t your_image_name /bin/bash
