FROM python:3

MAINTAINER Phil Stelzer <phil@philstelzer.com>

ENV OS_USERNAME demo
ENV OS_PASSWORD openstack
ENV OS_TENANT_NAME demo
ENV OS_AUTH_URL "http://10.0.0.20:5000/v2.0"
ENV INFLUX_HOST influxdb.service.consul
ENV INFLUX_PORT 8086
ENV INFLUX_DB cluster_metrics
ENV STACK_ID 12345
ENV INTERVAL 10

ADD requirements.txt .

RUN pip install -r requirements.txt

ADD envdefault.py .
ADD main.py .

ENTRYPOINT ["python", "main.py"]