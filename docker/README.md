
# Raspberry pi zero docker image

It might be difficult and/or tedious to install all prereqs on a pi zero.
(and Python 3.7 is long to build from sources compiling on the pi zero).

I've been willing to try docker on the pi zero as a way to "easyly" move applications/functions from one pi to another without needing to care (as much as possible) of all the prerequisits and potentially conflicting other apps.

#Usage:

## Building the docker image from base image (base image based on stretch + python 3)

I published the base image as xavierrrr/xrrzero:stretchpython3.7 in dockerhub. 

Run the following docker build command from project root directory

```
docker build -t mitemperature2localimage -f docker/Dockerfile .
```

**Update the Dockerfile with you sensor mac adress**

**Update the LYWSD03MMC.py command line for your use. The default file will invoke a simple callback python programs that is updating a vera verde box with sensor data.**

## Starting the docker image
```
sudo docker run --net=host -d -i -t mitemperature2localimage
```

# Pi Zero Docker installation on a frech stretch/buster installation

**I'm putting this here for quick reference**

```
sudo apt-get install apt-transport-https ca-certificates software-properties-common -y
curl -fsSL get.docker.com -o get-docker.sh && sh get-docker.sh
sudo usermod -aG docker pi
sudo curl https://download.docker.com/linux/raspbian/gpg

systemctl start docker.service
docker info
```
