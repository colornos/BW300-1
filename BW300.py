import multiprocessing
import sys
import pygatt.backends
import logging
from configparser import ConfigParser
import time
import subprocess
from struct import *
from binascii import hexlify
import os
import threading
from time import sleep
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

GPIO.setwarnings(False)

# Interesting characteristics
Char_heartrate = '00002A35-0000-1000-8000-00805f9b34fb'  # heartrate data

def sanitize_timestamp(timestamp):

    retTS = time.time()

    return retTS

def decodeheartrate(handle, values):

    data = unpack('<BHHxxxxxIH', bytes(values[0:16]))
    retDict = {}
    retDict["valid"] = (data[0] == 0x1e)
    retDict["systolic"] = data[1]
    retDict["diastolic"] = data[2]
    retDict["timestamp"] = sanitize_timestamp(data[3])
    retDict["pulse"] = data[4]
    return retDict

def processIndication(handle, values):

    if handle == handle_heartrate:
        result = decodeheartrate(handle, values)
        if result not in heartratedata:
            log.info(str(result))
            heartratedata.append(result)
        else:
            log.info('Duplicate heartratedata record')
    else:
        log.debug('Unhandled Indication encountered')

def wait_for_device(devname):
    found = False
    while not found:
        try:
            # wait for bpm to wake up and connect to it
            found = adapter.filtered_scan(devname)
        except pygatt.exceptions.BLEError:
            # reset adapter when (see issue #33)
            adapter.reset()
    return

def connect_device(address):
    device_connected = False
    tries = 3
    device = None
    while not device_connected and tries > 0:
        try:
            device = adapter.connect(address, 8, addresstype)
            device_connected = True
        except pygatt.exceptions.NotConnectedError:
            tries -= 1
    return device

def init_ble_mode():
    p = subprocess.Popen("sudo btmgmt le on", stdout=subprocess.PIPE,
                         shell=True)
    (output, err) = p.communicate()
    if not err:
        log.info(output)
        return True
    else:
        log.info(err)
        return False

'''
Main program loop
'''

config = ConfigParser()
config.read('BW300.ini')
path = "plugins/"
plugins = {}

# set up logging
numeric_level = getattr(logging,
                        config.get('Program', 'loglevel').upper(),
                        None)
if not isinstance(numeric_level, int):
    raise ValueError('Invalid log level: %s' % loglevel)
logging.basicConfig(level=numeric_level,
                    format='%(asctime)s %(levelname)-8s %(funcName)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename=config.get('Program', 'logfile'),
                    filemode='w')
log = logging.getLogger(__name__)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(numeric_level)
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(funcName)s %(message)s')
ch.setFormatter(formatter)
log.addHandler(ch)

# Load configured plugins

if config.has_option('Program', 'plugins'):
    config_plugins = config.get('Program', 'plugins').split(',')
    config_plugins = [plugin.strip(' ') for plugin in config_plugins]
    log.info('Configured plugins: %s' % ', '.join(config_plugins))

    sys.path.insert(0, path)
    for plugin in config_plugins:
        log.info('Loading plugin: %s' % plugin)
        mod = __import__(plugin)
        plugins[plugin] = mod.Plugin()
    log.info('All plugins loaded.')
else:
    log.info('No plugins configured.')
sys.path.pop(0)

ble_address = config.get('BPM', 'ble_address')
device_name = config.get('BPM', 'device_name')
device_model = config.get('BPM', 'device_model')

if device_model == 'BW300':
    addresstype = pygatt.BLEAddressType.public
    # On BS410 time=0 equals 1/1/2010. 
    # time_offset is used to convert to unix standard
    time_offset = 0
else:
    addresstype = pygatt.BLEAddressType.random
    time_offset = 0
'''
Start BLE comms and run that forever
'''
log.info('BW300 Started')
if not init_ble_mode():
    sys.exit()

adapter = pygatt.backends.GATTToolBackend()
adapter.start()

while True:
    wait_for_device(device_name)
    device = connect_device(ble_address)
    if device:
        heartratedata = []
        handle_heartrate = device.get_handle(Char_heartrate)
        continue_comms = True

        try:
            device.subscribe(Char_heartrate,
                             callback=processIndication,
                             indication=True)
        except pygatt.exceptions.NotConnectedError:
            continue_comms = False

        if continue_comms:
            log.info('Waiting for notifications for another 30 seconds')
            time.sleep(30)
            try:
                device.disconnect()
            except pygatt.exceptions.NotConnectedError:
                log.info('Could not disconnect...')

            log.info('Done receiving data from blood pressure monitor')
            # process data if all received well
            if heartratedata:
                # Sort scale output by timestamp to retrieve most recent three results
                heartratedatasorted = sorted(heartratedata, key=lambda k: k['timestamp'], reverse=True)
                    
                # Run all plugins found
                for plugin in plugins.values():
                        plugin.execute(config, heartratedatasorted)
                else:
                    log.error('Unreliable data received. Unable to process')
