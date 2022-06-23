# Docker image

It's pretty straightforward to run the script using the dockerfile provided here.

#Usage:

## Building the docker image

Run the following docker build command from the project root directory

Docker needs to be running as root due to the dependencies of the project so if you use rootless docker, you may need to use `sudo` for each docker command.

```
docker build -t mitemperature2 -f docker/Dockerfile .
```

## Starting the docker image

```
docker run --net=host --privileged -it mitemperature2 <parameters>
```

Example:

```
docker run --net=host --privileged -it mitemperature2 -a --devicelistfile /app/sensors.ini --mqttconfigfile /app/mqtt.conf
```

# Raspberry Pi Docker installation

**I'm putting this here for quick reference**

```
sudo apt-get install apt-transport-https ca-certificates software-properties-common -y
curl -fsSL get.docker.com -o get-docker.sh && sh get-docker.sh
sudo usermod -aG docker pi
sudo curl https://download.docker.com/linux/raspbian/gpg

systemctl start docker.service
docker info
```
