import requests
import json
import ceilometerclient.client
from datetime import timedelta, datetime
import argparse
from envdefault import EnvDefault
import threading

parser = argparse.ArgumentParser()
parser.add_argument("OS_USERNAME", action=EnvDefault, envvar='OS_USERNAME', help="Username to use for the ceilometer API")
parser.add_argument("OS_PASSWORD", action=EnvDefault, envvar='OS_PASSWORD', help="Password to use for the ceilometer API")
parser.add_argument("OS_TENANT_NAME", action=EnvDefault, envvar='OS_TENANT_NAME', help="Tenant name to use for the ceilometer API")
parser.add_argument("OS_AUTH_URL", action=EnvDefault, envvar='OS_AUTH_URL', help="Auth url to use for the ceilometer API")
parser.add_argument("INFLUX_HOST", action=EnvDefault, envvar='INFLUX_HOST', help="InfluxDB IP or Hostname")
parser.add_argument("INFLUX_PORT", action=EnvDefault, envvar='INFLUX_PORT', help="InfluxDB Port")
parser.add_argument("INFLUX_DB", action=EnvDefault, envvar='INFLUX_DB', help="InfluxDB Database to use")
parser.add_argument("STACK_ID", action=EnvDefault, envvar='STACK_ID', help="Heat Stack ID to observe. Queries will use this to find Resources belonging to the stack.")
parser.add_argument("INTERVAL", action=EnvDefault, envvar='INTERVAL', help="The interval to use for querying ceilometer and pushing the data to influx", type=int)
args = parser.parse_args()

print(datetime.utcnow())
cclient = ceilometerclient.client.get_client(2,
                                             os_username=args.OS_USERNAME,
                                             os_password=args.OS_PASSWORD,
                                             os_tenant_name=args.OS_TENANT_NAME,
                                             os_auth_url=args.OS_AUTH_URL)

influxdbConnectionString = 'http://%s:%s' % (args.INFLUX_HOST, args.INFLUX_PORT)

# create influxdb database if not existent
requests.post(influxdbConnectionString + '/query', data={'q': 'CREATE DATABASE %s' % args.INFLUX_DB})

def insertCpuDataForInstance(instance):
    requests.post(influxdbConnectionString + '/write?db=%s' % args.INFLUX_DB,
                  data='cpu_load,host=%s,type=%s value=%s' % (instance.metadata['display_name'],
                                                              instance.metadata.get('user_metadata.type', ""),
                                                              instance.volume))
# helper function
def distinct(iterable, keyfunc=None):
    seen = set()
    for item in iterable:
        key = item if keyfunc is None else keyfunc(item)
        if key not in seen:
            seen.add(key)
            yield item

def periodicCollect():
    # check how many instances are alive in our cluster
    activeInstancesQuery = [dict(field='metadata.user_metadata.stack', op='eq', value=args.STACK_ID),
                            dict(field='timestamp', op='gt', value=datetime.utcnow() - timedelta(seconds=15))]

    activeInstances = cclient.statistics.list('cpu_util', q=activeInstancesQuery, groupby='resource_id')
    print("Aktive Instanzen: %s" % len(activeInstances))

    #for instance in activeInstances:
    #    print("Instanz: %s, CPU Auslastung: %s %s" % (instance.groupby['resource_id'], instance.avg, instance.unit))

    ### get all CPU usage data for those instances and post them to influx
    allInstancesWithCpuUsageInStackQuery = [dict(field='metadata.user_metadata.stack', op='eq', value=args.STACK_ID),
                                            dict(field='meter', op='eq', value='cpu_util'),
                                            dict(field='timestamp', op='gt', value=datetime.utcnow() - timedelta(seconds=15))]

    allInstancesWithCpuUsageInStack = cclient.new_samples.list(q=allInstancesWithCpuUsageInStackQuery, limit=100)
    for instance in allInstancesWithCpuUsageInStack:
        print("Instanz: %s, CPU Auslastung: %s %s" % (instance.metadata['display_name'], instance.volume, instance.unit))
        insertCpuDataForInstance(instance)

    allSlavesWithDuplicates = filter(lambda i: i.metadata.get('user_metadata.type', "") == "slave", allInstancesWithCpuUsageInStack)
    allSlaves = distinct(allSlavesWithDuplicates, lambda slave: slave.resource_id)

    allMastersWithDuplicates = filter(lambda i: i.metadata.get('user_metadata.type', "") == "master", allInstancesWithCpuUsageInStack)
    allMasters = distinct(allMastersWithDuplicates, lambda master: master.resource_id)

    numberOfSlaves = len(list(allSlaves))
    numberOfMasters = len(list(allMasters))
    print("Anzahl Slaves: %s" % numberOfSlaves)
    print("Anzahl Master: %s" % numberOfMasters)

    # Insert Node count
    requests.post(influxdbConnectionString + '/write?db=%s' % args.INFLUX_DB, data='slave_count value=%s' % numberOfSlaves)
    requests.post(influxdbConnectionString + '/write?db=%s' % args.INFLUX_DB, data='master_count value=%s' % numberOfMasters)

    threading.Timer(args.INTERVAL, periodicCollect).start()

periodicCollect()
