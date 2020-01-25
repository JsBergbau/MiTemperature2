#
# NOTE: THIS DOCKERFILE IS GENERATED VIA "update.sh"
#
# PLEASE DO NOT EDIT IT DIRECTLY.
#

# Start from a Python3.7 
FROM xavierrrr/xrrzero:stretchpython3.7 

# http://bugs.python.org/issue19846
# > At the moment, setting "LANG=C" on a Linux system *fundamentally breaks Python 3*, and that's not OK.
ENV LANG C.UTF-8

RUN /usr/local/bin/pip3.7 install bluepy
RUN /usr/local/bin/pip3.7 install requests

COPY ../LYWSD03MMC.py LYWSD03MMC.py 
COPY ../sendtovera.py sendtovera.py 

ENTRYPOINT service dbus start

##Change to the proper LYWSD03MMC call for your system
ENTRYPOINT while true; do /usr/local/bin/python3.7m LYWSD03MMC.py -d A4:C1:38:7F:E6:DC -r -b 100 --skipidentical 50 -deb --callback sendtovera.py; sleep 2; done

# start with sudo docker run --net=host -t your_image_name /bin/bash
