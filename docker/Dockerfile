FROM python:3.9-slim

# pybluez wont compile with the newer version of setuptools so use fixed version
RUN apt -y install wget && \
 wget https://repo.zabbix.com/zabbix/6.4/raspbian/pool/main/z/zabbix-release/zabbix-release_6.4-1+debian11_all.deb && \
 dpkg -i zabbix-release_6.4-1+debian11_all.deb && \
 apt update && \
 apt -y upgrade && \
 apt -y install python3-pip libglib2.0-dev libbluetooth-dev bluetooth && \
 pip3 install --upgrade setuptools==57.5.0 && \
 pip3 install bluepy requests pybluez pycryptodomex paho-mqtt \
 apt -y install zabbix-sender

COPY . /app

ENTRYPOINT ["python3", "/app/LYWSD03MMC.py"]
