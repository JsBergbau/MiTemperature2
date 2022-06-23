FROM python:3.9

RUN apt-get update

RUN apt-get -y install python3-pip libglib2.0-dev libbluetooth-dev bluetooth

RUN pip3 install bluepy
RUN pip3 install requests
# pybluez wont compile with the newer version
RUN pip3 install --upgrade setuptools==57.5.0
RUN pip3 install pybluez
RUN pip3 install pycryptodomex
RUN pip3 install paho-mqtt

COPY . /app

ENTRYPOINT ["python3", "/app/LYWSD03MMC.py"]
