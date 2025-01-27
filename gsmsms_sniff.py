#!/usr/bin/python
#!coding=utf-8
#le4f.net

import socket
import struct
import threading
import queue
import time
import subprocess
import re
import os
import pdb

def covert_cellphone_num(num):
    phone_number = []
    for i in num:
        i = ord(i)
        i = (i << 4 & 0xF0) + (i >> 4 & 0x0F)
        phone_number.append(chr(i))

    return ("".join(phone_number).encode('hex'))[:-1]

def handle_message(**kargs):
    gsm_sms_segs = ""

    while True:
        data = kargs['messages'].get(True)
        if data[0:2] == '\x02\x04': #GSM_TAP header Version02 & HeaderLength 16bytes

            #uplink = struct.unpack('H', data[4:6])[0]
            #uplink = (uplink & 0x40 == 0x40)
            #print data.encode('hex')
            #skip header 16 bytes, directly handle the LAPDm part
            address_field = struct.unpack('B', data[16:17])[0]
            control_field = struct.unpack('B', data[17:18])[0]
            length_field =  struct.unpack('B', data[18:19])[0]

            if (address_field >> 2) & 0x1F == 3: # GSM SMS
                if (control_field & 0x01) == 0x00:  # frame type == information frame
                    # caculate segments data length
                    seg_len = (length_field >> 2) & 0x3F
                    # if there are more segments
                    has_segments = ((length_field >> 1) & 0x01 == 0x1)
                    # caculate segments sequence
                    seq = (control_field >> 1) & 0x07

                    gsm_sms_segs += data[19:19+seg_len]

                    # reassemble all segments when handling the last packet
                    if has_segments == False:

                        gsm_sms = gsm_sms_segs
                        gsm_sms_segs = ""

                        to_number = ""
                        from_number = ""
                        to_number_len = 0
                        from_number_len = 0
                        is_sms_submit = False
                        is_sms_deliver = False
                        has_tpudhi = False
                        has_tpvpf = False
                        is_mms = False

                        if (len(gsm_sms) > 10 and ord(gsm_sms[0:1]) & 0x0F == 0x09) and (ord(gsm_sms[1:2]) == 0x01) and (ord(gsm_sms[2:3]) > 0x10): # SMS Message
                            try:
                                #print gsm_sms.encode('hex') //hoho
                                # determinate if this is uplink message aka MS to Network
                                is_uplink = (ord(gsm_sms[3:4]) == 0x00)
                                #print ("Type: SUBMIT" if is_uplink else "Type: DELIVER")

                                if is_uplink:
                                    to_number_len = struct.unpack('B', gsm_sms[6:7])[0] - 1
                                    to_number = gsm_sms[8:8+to_number_len]
                                    to_number = covert_cellphone_num(to_number)

                                    # check if this is SMS-SUBMIT
                                    sms_submit = struct.unpack('B', gsm_sms[7+to_number_len+2:7+to_number_len+2+1])[0]
                                    if sms_submit & 0x03 == 0x01:
                                        is_sms_submit = True
                                        # check if TP UD includes a extra header
                                        has_tpudhi = ((struct.unpack('B', gsm_sms[7+to_number_len+2:7+to_number_len+2+1])[0] & 0x40) == 0x40)
                                        has_tpvpf = ((struct.unpack('B', gsm_sms[7+to_number_len+2:7+to_number_len+2+1])[0] >> 3 & 0x02) == 0x02)
                                        from_number_len = struct.unpack('B', gsm_sms[8+to_number_len+3:8+to_number_len+3+1])[0]
                                        from_number_len = (from_number_len / 2) + (from_number_len % 2)
                                        from_number = gsm_sms[8+to_number_len+3+2:8+to_number_len+3+2+from_number_len]
                                        from_number = covert_cellphone_num(from_number)

                                        print("[!]{1} From: {2}\tTo: {3}", GetCurrentTime(), from_number, to_number)

                                else:
                                    to_number_len = struct.unpack('B', gsm_sms[5:6])[0] - 1
                                    to_number = gsm_sms[7:7+to_number_len]
                                    to_number = covert_cellphone_num(to_number)

                                    # check if this is SMS-DELIVER
                                    sms_deliver = struct.unpack('B', gsm_sms[7+to_number_len+2:7+to_number_len+2+1])[0]
                                    if sms_deliver & 0x03 == 0x0:
                                        is_sms_deliver = True
                                        # check if TP UD includes a extra header
                                        has_tpudhi = ((struct.unpack('B', gsm_sms[7+to_number_len+2:7+to_number_len+2+1])[0] & 0x40) == 0x40)

                                        from_number_len = struct.unpack('B', gsm_sms[7+to_number_len+3:7+to_number_len+3+1])[0]
                                        from_number_len = (from_number_len / 2) + (from_number_len % 2)
                                        from_number = gsm_sms[7+to_number_len+3+2:7+to_number_len+3+2+from_number_len]
                                        from_number = covert_cellphone_num(from_number)

                                        print("[!]{1} From: {2}\tTo: {3}", GetCurrentTime(), from_number, to_number)

                                if is_sms_deliver:
                                    try:
                                        # if there is additional header, skip it
                                        header_len = 0
                                        if has_tpudhi:
                                            header_len = struct.unpack('B', gsm_sms[7+to_number_len+3+2+from_number_len+10:7+to_number_len+3+2+from_number_len+10+1])[0]

                                        mms = struct.unpack('B', gsm_sms[7+to_number_len+3+2+from_number_len+1:7+to_number_len+3+2+from_number_len+1+1])[0]
                                        if ((mms >> 2) & 0x03) == 0x01:
                                            is_mms = True

                                        if header_len == 0:
                                            sms = gsm_sms[7+to_number_len+3+2+from_number_len + 10:]
                                        else:
                                            sms = gsm_sms[7+to_number_len+3+2+from_number_len + 10 + header_len + 1:]
                                        #print sms.encode('hex')

                                        # adjust string from big-endian to little-endian
                                        #sms_len = (len(sms) / 2)
                                        #sms = struct.unpack((">" + "H" * sms_len), sms)
                                        #sms = struct.pack("<" + ("H" * sms_len), *sms)
                                        #print sms.encode('hex')

                                        #SMS is using utf-16 encode
                                        if not is_mms:
                                            print('[*]Msg:' + sms.decode('UTF-16BE'))
                                            #print "INSERT INTO sms_data(sms_to, sms_from, sms_message) VALUES('%s', '%s', '%s')" % (to_number.encode('utf-8'), from_number.encode('utf-8'), sms.decode('UTF-16BE').encode('utf-8'))
                                        else:
                                            print("[!]{1} MMS message.", GetCurrentTime())

                                    except:
                                        print("[-]{1} Can't Decode The Message", GetCurrentTime())

                                elif is_sms_submit:
                                    try:
                                        # if there is additional header, skip it
                                        header_len = 0
                                        # looks like uplink sms doesn't have a TP service centre time stamp
                                        if has_tpudhi:
                                            header_len = struct.unpack('B', gsm_sms[8+to_number_len+3+2+from_number_len+3:8+to_number_len+3+2+from_number_len+3+1])[0]

                                        mms = struct.unpack('B', gsm_sms[8+to_number_len+3+2+from_number_len+1:8+to_number_len+3+2+from_number_len+1+1])[0]
                                        if ((mms >> 2) & 0x03) == 0x01:
                                            is_mms = True

                                        if has_tpvpf:
                                            if header_len == 0:
                                                sms = gsm_sms[8+to_number_len+3+2+from_number_len + 3 + 1:]
                                            else:
                                                sms = gsm_sms[8+to_number_len+3+2+from_number_len + 3 + header_len + 1 + 1:]
                                        else:
                                            if header_len == 0:
                                                sms = gsm_sms[8+to_number_len+3+2+from_number_len + 3:]
                                            else:
                                                sms = gsm_sms[8+to_number_len+3+2+from_number_len + 3 + header_len + 1:]
                                        #print sms.encode('hex')

                                        # adjust string from big-endian to little-endian
                                        #sms_len = (len(sms) / 2)
                                        #sms = struct.unpack((">" + "H" * sms_len), sms)
                                        #sms = struct.pack("<" + ("H" * sms_len), *sms)
                                        #print sms.encode('hex')

                                        #SMS is using utf-16 encode
                                        if not is_mms:
                                            print("[*]Msg: " + sms.decode("UTF-16BE"))
                                        else:
                                            print("[!]{1} MMS message.", GetCurrentTime())
                                    except:
                                        print("[-]{1} Can't Decode The Message", GetCurrentTime())
                                else:
                                    print("[!]{1} SMS Status Report. ", GetCurrentTime())
                            except:
                                print("[-]{1} Unexpected packets format.", GetCurrentTime())

def GetCurrentTime():
    return time.strftime('%Y/%m/%d %H:%M:%S',time.localtime(time.time()))

if __name__ == '__main__':
	print("[*]Sniffer Loading...")
	print("[*]Press Ctrl+C to Exit.")
	try:
		q = queue.Queue()
		t = threading.Thread(target=handle_message, name="handle_message_thread", kwargs={'messages':q})
		t.daemon = True
		t.start()
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.bind(('0.0.0.0', 47290))
		while True:
			data, addr = s.recvfrom(2048)
			#print data.encode('hex')
			#pdb.set_trace();
			q.put(data)
		s.close()
	except KeyboardInterrupt:
		try:
			child1.kill()
			child2.kill()
			child3.kill()
			print("[-]Kill Process Done.")
		except:
			pass
