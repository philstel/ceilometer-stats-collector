import requests
import json
import ceilometerclient.client
from datetime import timedelta, datetime
import argparse
from envdefault import EnvDefault
import threading
from flask import Flask, Response
import os

app = Flask(__name__)

args = {
    'OS_USERNAME': os.environ.get('OS_USERNAME'),
    'OS_PASSWORD': os.environ.get('OS_PASSWORD'),
    'OS_TENANT_NAME': os.environ.get('OS_TENANT_NAME'),
    'OS_AUTH_URL': os.environ.get('OS_AUTH_URL'),
    'STACK_ID': os.environ.get('STACK_ID')
}

cclient = ceilometerclient.client.get_client(2,
                                             os_username=args['OS_USERNAME'],
                                             os_password=args['OS_PASSWORD'],
                                             os_tenant_name=args['OS_TENANT_NAME'],
                                             os_auth_url=args['OS_AUTH_URL'])

# helper function
def distinct(iterable, keyfunc=None):
    seen = set()
    for item in iterable:
        key = item if keyfunc is None else keyfunc(item)
        if key not in seen:
            seen.add(key)
            yield item

@app.route('/metrics')
def metrics():
    # check how many instances are alive in our cluster
    activeInstancesQuery = [dict(field='metadata.user_metadata.stack', op='eq', value=args['STACK_ID']),
                            dict(field='timestamp', op='gt', value=datetime.utcnow() - timedelta(seconds=7))]

    activeInstances = cclient.statistics.list('cpu_util', q=activeInstancesQuery, groupby='resource_id')
    print("Aktive Instanzen: %s" % len(activeInstances))

    #for instance in activeInstances:
    #    print("Instanz: %s, CPU Auslastung: %s %s" % (instance.groupby['resource_id'], instance.avg, instance.unit))

    ### get all CPU usage data for those instances
    allInstancesWithCpuUsageInStackQuery = [dict(field='metadata.user_metadata.stack', op='eq', value=args['STACK_ID']),
                                            dict(field='meter', op='eq', value='cpu_util'),
                                            dict(field='timestamp', op='gt', value=datetime.utcnow() - timedelta(seconds=7))]

    allInstancesWithCpuUsageInStack = cclient.new_samples.list(q=allInstancesWithCpuUsageInStackQuery, limit=100)
    for instance in allInstancesWithCpuUsageInStack:
        print("Instanz: %s, CPU Auslastung: %s %s" % (instance.metadata['display_name'], instance.volume, instance.unit))

    allSlavesWithDuplicates = filter(lambda i: i.metadata.get('user_metadata.type', "") == "slave", allInstancesWithCpuUsageInStack)
    allSlaves = distinct(allSlavesWithDuplicates, lambda slave: slave.resource_id)

    allMastersWithDuplicates = filter(lambda i: i.metadata.get('user_metadata.type', "") == "master", allInstancesWithCpuUsageInStack)
    allMasters = distinct(allMastersWithDuplicates, lambda master: master.resource_id)

    numberOfSlaves = len(list(allSlaves))
    numberOfMasters = len(list(allMasters))
    print("Anzahl Slaves: %s" % numberOfSlaves)
    print("Anzahl Master: %s" % numberOfMasters)

    data = ""
    for instance in allInstancesWithCpuUsageInStack:
        data += '\ncpu_load,host=%s,type=%s value=%s' % (instance.metadata['display_name'],
                                                    instance.metadata.get('user_metadata.type', ""),
                                                    instance.volume)

    output = """slave_count %s
master_count %s%s
    """ % (numberOfSlaves, numberOfMasters, data)

    return Response(output, mimetype='text/plain')