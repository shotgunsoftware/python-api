FROM python:2.7
MAINTAINER Autodesk <info@autodesk.com>

#RUN apt-get install -y python-pip
RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get install -y python-nose
COPY . /app
RUN cp /app/tests/example_config /app/config

WORKDIR /app