# Description
This python script shows how to query data from OpenStack Ceilometer and posts the resulting values to a InfluxDB database.
It uses the ceilometer python API and the influxdb HTTP API.

# Reasons why this exists
I was missing a proper visualization for my Ceilometer metrics.
We are using heat to start a Mesos cluster and let this script run in the cluster.

I don't know whether this is useful for someone, but i guess it doesn't hurt anyone either.

# Install instructions

You possibly want to create a virtualenv before running this

`pip install -r requirements.txt`

# Running

You also can provide the parameters as environment variables.

`python main.py $OS_USERNAME $OS_PASSWORD $OS_TENANT_NAME $OS_AUTH_URL $INFLUX_HOST $INFLUX_PORT $INFLUX_DB $python main.py $OS_USERNAME $OS_PASSWORD $OS_TENANT_NAME $OS_AUTH_URL $INFLUX_HOST $INFLUX_PORT $INFLUX_DB $STACK_ID $INTERVAL`

## InfluxDB in a docker container for dev/testing
docker run -d -p 8083:8083 -p 8086:8086 exira/influxdb:0.13