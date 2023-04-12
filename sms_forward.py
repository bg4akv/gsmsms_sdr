#!/usr/bin/python
#!coding=utf-8

import socket
import struct
import threading
import queue
import time
import subprocess
import re
import os
from scapy.all import sniff, UDP
import pdb

g_forward_udp_port = 47290;
g_q = queue.Queue();
g_set = set();
g_s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM);

def recv_new_data(p):
	#pdb.set_trace();
	#if g_listen_udp_dst_port != int(p[UDP].dport):
	#   return
	
	udpdata = str(p[UDP].payload)
	
	_b_find = 0;
	for s_key in g_set:
	    if s_key==udpdata:
	       _b_find = 1;
	       break;
			
	if _b_find == 0:
		g_set.clear();
		g_set.add(udpdata);
		#print udpdata.encode('hex')
		g_s.sendto(udpdata.encode('utf-8'), ("127.0.0.1", g_forward_udp_port));

if __name__ == '__main__':
	try:
		#while True:
		#str_filter = 'udp and port %d' % g_listen_udp_dst_port;
		str_filter = 'udp portrange 4729-6000';
		sniff(iface='lo', filter=str_filter, prn=recv_new_data,count = 0 ,store=0 )

	except KeyboardInterrupt:
		try:
			child1.kill()
			child2.kill()
			child3.kill()
			print("[-]Kill Process Done.")
		except:
			pass
