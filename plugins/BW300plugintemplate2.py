#!/usr/bin/env python
# -*- coding: utf8 -*-
import sys
import logging
from ConfigParser import SafeConfigParser
import os
import thread
import urllib2, urllib

class Plugin:

    def __init__(self):
        return

    def execute(self, config, heartratedata):
 #       self.heartratedata = heartratedata
        # --- part of plugin skeleton
        log = logging.getLogger(__name__)
        log.info('Starting plugin: ' + __name__)
        #read ini file from same location as plugin resides, named [pluginname].ini
        configfile = os.path.dirname(os.path.realpath(__file__)) + '/' + __name__ + '.ini'
        pluginconfig = SafeConfigParser()
        pluginconfig.read(configfile)
        log.info('ini read from: ' + configfile)
        
        # --- start plugin specifics here

	device = '104019001'
	f1=open("one.txt", "r")
    	if f1.mode == 'r':
            contents1 = f1.read()

        f2=open("two.txt", "r")
        if f2.mode == 'r':
            contents2 = f2.read()

        f3=open("three.txt", "r")
        if f3.mode == 'r':
            contents3 = f3.read()

        f4=open("four.txt", "r")
        if f4.mode == 'r':
            contents4 = f4.read()

	byte1 = str(contents1)
	byte2 = str(contents2)
	byte3 = str(contents3)
	byte4 = str(contents4)

	if (byte1 == 0) and (byte2 == 0) and (byte3 == 0) and (byte4 == 0):
	    print "No card detected!"
	else:

	    systolic = heartratedata[0]['systolic']
	    diastolic = heartratedata[0]['diastolic']
            pulse = heartratedata[0]['pulse']
	    mydata=[('device', device),('byte1', byte1),('byte2', byte2),('byte3', byte3),('byte4', byte4),('one', systolic),('two', diastolic),('three', pulse)]   #The first is the var name the second is the value
	    mydata=urllib.urlencode(mydata)
	    path='http://colornos.com/sensors/helloworld3.php'    #the url you want to POST to
	    req=urllib2.Request(path, mydata)
	    req.add_header("Content-type", "application/x-www-form-urlencoded")
	    page=urllib2.urlopen(req).read()
	    print page

	    log.info('Finished plugin: ' + __name__)
