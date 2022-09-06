FROM python:3.9-slim

# pybluez wont compile with the newer version of setuptools so use fixed version
RUN apt update && \
 apt -y upgrade && \
 apt -y install python3-pip libglib2.0-dev libbluetooth-dev bluetooth && \
 pip3 install --upgrade setuptools==57.5.0 && \
 pip3 install bluepy requests pybluez pycryptodomex paho-mqtt

COPY . /app

ENTRYPOINT ["python3", "/app/LYWSD03MMC.py"]
