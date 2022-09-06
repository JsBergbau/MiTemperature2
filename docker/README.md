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

You can use this to run with sensors.ini and mqtt.conf on the host machine rather than having to use the versions in the docker repository

```
docker run --net=host --privileged -it -v $(pwd)/sensors.ini:/app/sensors.ini -v $(pwd)/mqtt.conf:/app/mqtt.conf  mitemperature2 -a --devicelistfile /app/sensors.ini --mqttconfigfile /app/mqtt.conf
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

# Cross compiling docker image and pushing to dockerhub

Follow this to set up and build dockerimage for multi arch. This can be done on an amd64 machine which is faster than building on a raspberry pi.   

First set up multi build arch
```
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
docker buildx create --name multiarch --driver docker-container --use
docker buildx inspect --bootstrap
```
Then log into dockerhub

```
docker login -u <USERNAME> -p <DOCKERHUB TOKEN>
```
Then build and push the image
```
TAG=latest # change as needed
docker buildx build \
    --push \
    --platform linux/amd64,linux/amd64/v2,linux/amd64/v3,linux/amd64/v4,linux/arm64,linux/ppc64le,linux/s390x,linux/386,linux/mips64le,linux/arm/v7,linux/arm/v6  \
    -t antxxxx/mitemperature2:${TAG} \
    -f docker/Dockerfile .
```


