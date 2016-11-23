#!/usr/bin/env python

import pcapy
# import os
import sys
import subprocess  # use commandline
# from requests import get  # whois
import requests
import re

"""
[kevin@Tardis test]$ ./pmap5.py -p test2.pcap -d

sudo tcpdump -s 0 -i en1 -w test.pcap
-s 0 will set the capture byte to its maximum i.e. 65535 and will not truncate
-i en1 captures Ethernet interface
-w test.pcap will create that pcap file

tcpdump -qns 0 -X -r osx.pcap

[kevin@Tardis tmp]$ sudo tcpdump -w osx.pcap
tcpdump: data link type PKTAP
tcpdump: listening on pktap, link-type PKTAP (Packet Tap), capture size 65535 bytes
^C4414 packets captured
4416 packets received by filter
0 packets dropped by kernel

"""


class Commands(object):
	"""
	Unfortunately the extremely simple/useful commands was depreciated in favor
	of the complex/confusing subprocess ... this aims to simplify.
	"""
	def getoutput(self, cmd):
		ans = subprocess.Popen([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()[0]
		return ans


class WhoIs(object):
	def __init__(self, ip):
		rec = requests.get('http://whois.arin.net/rest/ip/{}.txt'.format(ip))
		if rec.status_code != 200:
			print 'Error'
			return {}
		ans = {}
		r = re.compile(r"\s\s+")
		b = rec.text.split('\n')
		for l in b:
			if l and l[0] != '#':
				l = r.sub('', l)
				a = l.split(':')
				# print a
				ans[a[0]] = a[1]
		self.record = ans


class GetHostName(object):
	def __init__(self, ip):
		"""Use the avahi (zeroconfig) tools or dig to find a host name given an
		ip address.

		in: ip
		out: string w/ host name or 'unknown' if the host name couldn't be found
		"""
		name = 'unknown'
		if sys.platform == 'linux' or sys.platform == 'linux2':
			name = self.cmdLine("avahi-resolve-address {} | awk '{print $2}'".format(ip)).rstrip().rstrip('.')
		elif sys.platform == 'darwin':
			name = self.cmdLine('dig +short -x {} -p 5353 @224.0.0.251'.format(ip)).rstrip().rstrip('.')

		if name.find('connection timed out') >= 0: name = 'unknown'
		if name == '': name = 'unknown'

		self.name = name

	def cmdLine(self, cmd):
		return subprocess.Popen([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()[0]


class CapturePackets(object):
	"""
	todo
	"""
	def __init__(self, iface, filename='test.pcap', filter=None, num_packets=3000):
		# list all the network devices
		# print pcapy.findalldevs()

		max_bytes = 1024
		promiscuous = False
		read_timeout = 100  # in milliseconds
		pc = pcapy.open_live(iface, max_bytes, promiscuous, read_timeout)
		if filter: pc.setfilter(filter)
		self.dumper = pc.dump_open(filename)
		pc.loop(num_packets, self.recv_pkts)  # capture packets

	# callback for received packets
	def recv_pkts(self, hdr, data):
		try:
			# print data
			self.dumper.dump(hdr, data)
		except KeyboardInterrupt:  # probably show throw error instead
			exit('keyboard exit')
		except:
			exit('crap ... something went wrong')

	def run(self):
		pass
		# max_bytes = 1024
		# promiscuous = False
		# read_timeout = 100  # in milliseconds
		# pc = pcapy.open_live(iface, max_bytes, promiscuous, read_timeout)
		# if filter: pc.setfilter(filter)
		# self.dumper = pc.dump_open(filename)
		# pc.loop(num_packets, self.recv_pkts)  # capture packets


class MacLookup(object):
	def __init__(self, mac, full=False):
		self.vendor = self.get(mac, full)

	def get(self, mac, full):
		"""
		json response from www.macvendorlookup.com:

		{u'addressL1': u'1 Infinite Loop',
		u'addressL2': u'',
		u'addressL3': u'Cupertino CA 95014',
		u'company': u'Apple',
		u'country': u'UNITED STATES',
		u'endDec': u'202412195315711',
		u'endHex': u'B817C2FFFFFF',
		u'startDec': u'202412178538496',
		u'startHex': u'B817C2000000',
		u'type': u'MA-L'}
		"""
		try:
			r = requests.get('http://www.macvendorlookup.com/api/v2/' + mac)
		except requests.exceptions.HTTPError as e:
			print "HTTPError:", e.message
			return {'company': 'unknown'}

		if r.status_code == 204:  # no content found, bad MAC addr
			print 'ERROR: Bad MAC addr:', mac
			return {'company': 'unknown'}
		elif r.headers['content-type'] != 'application/json':
			print 'ERROR: Wrong content type:', r.headers['content-type']
			return {'company': 'unknown'}

		a = {}

		try:
			if full: a = r.json()[0]
			else: a['company'] = r.json()[0]['company']
			# print 'GOOD:',r.status_code,r.headers,r.ok,r.text,r.reason
		except:
			print 'ERROR:', r.status_code, r.headers, r.ok, r.text, r.reason
			a = {'company': 'unknown'}

		return a
