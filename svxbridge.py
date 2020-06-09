#!/usr/bin/env python
#    
#  SP2ONG 2019
#
#  SVXBridge - link SVXLink  <> Analog_Bridge via USRP



from time import time, sleep, clock, localtime, strftime
from random import randint
import shlex


import socket
import struct
import thread
import pyaudio
import audioop
import serial

#################################
# USRP configuration Variables
ipAddress = "127.0.0.1"

# put number of txPort = 46001 from Ananlog_Bridge.ini
# usrpPortRX = txPort
usrpPortRX = 46001

# put number of rxPort = 46002 from Ananlog_Bridge.ini
# usrpPortTX = rxPort
usrpPortTX = 46002

# Output device index see utils/index-audio.py for the good ports 
outputDeviceIndex = 0

# Input device index see utils/index-audio.py for the good ports
inputDeviceIndex = 17

# Port SVXLink squlech read/write 
ser = serial.Serial('/tmp/SQL')

# Port SVXLink PTT - only read status
s = serial.Serial('/tmp/PTT')

#################################

# Status of /tmp/PTT:
#  "T" - TX
#  "R" - TX
class ReadLine:
    def __init__(self, s):
        self.s = s

    def readline(self):
        while True:
            data = self.s.read(1)
            i = data.find(b"T")
            if i >= 0:
               r = "True"
               return r
            i = data.find(b"R")
            if i >= 0:
               r = "False"
               return r

# USRP send stream audio from DMR Analog_Bridge to  SVXLink via ALSA Loop hw:loopback,1,0

def rxAudioStream():
    global ipAddress

    FORMAT = pyaudio.paInt16
    CHUNK = 160
    CHANNELS = 1
    RATE = 48000
    state = None

    stream = p.open(format=FORMAT,
                    channels = CHANNELS,
                    rate = RATE,
                    output = True,
                    frames_per_buffer = CHUNK,
                    output_device_index = outputDeviceIndex
                    )
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    udp.bind(("", usrpPortRX))
    lastsql = 0

    while True:
        soundData, addr = udp.recvfrom(1024)
        if addr[0] != ipAddress:
            ipAddress = addr[0]
        if (soundData[0:4] == 'USRP'):
            keyup, = struct.unpack(">i", soundData[12:16])
            if keyup == 0:
               # SQL Close
               ser.write("Z")
               lastsql = 0
            if keyup == 1 and lastsql != keyup:
               # SQL Open
               ser.write("O")
               lastsql = 1
            type, = struct.unpack("i", soundData[20:24])
            audio = soundData[32:]
            if (type == 0): # voice
                audio = soundData[32:]
                if (len(audio) == 320):
                    if RATE == 48000:
                        (audio48, state) = audioop.ratecv(audio, 2, 1, 8000, 48000, state)
                        stream.write(bytes(audio48), 160 * 6)
                    else:
                        stream.write(audio, 160)
        else:
           # SQL Close
           ser.write("Z")
    udp.close()
    # SQL Close
    ser.write("Z")


# USRP send stream audio from SVXLink via ALSA Loop hw:loopback,1,2 to Analog_Bridge 

def txAudioStream():
    FORMAT = pyaudio.paInt16
    CHUNK = 960
    CHANNELS = 1
    RATE = 48000
    state = None 

    stream = p.open(format=FORMAT,
                    channels = CHANNELS,
                    rate = RATE,
                    input = True,
                    frames_per_buffer = CHUNK,
                    input_device_index = inputDeviceIndex
                    )
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    lastPtt = ptt
    seq = 0
    while True:
        try:

            if RATE == 48000:       # If we are reading at 48K we need to resample to 8K
                audio48 = stream.read(CHUNK, exception_on_overflow=False)
                (audio, state) = audioop.ratecv(audio48, 2, 1, 48000, 8000, state)
            else:
                audio = stream.read(CHUNK, exception_on_overflow=False)
            if ptt != lastPtt:
                usrp = 'USRP' + struct.pack('>iiiiiii',seq, 0, ptt, 0, 0, 0, 0)
                udp.sendto(usrp, (ipAddress, usrpPortTX))
                seq = seq + 1
                #print 'PTT: {}'.format(ptt)
            lastPtt = ptt
            if ptt:
                usrp = 'USRP' + struct.pack('>iiiiiii',seq, 0, ptt, 0, 0, 0, 0) + audio
                udp.sendto(usrp, (ipAddress, usrpPortTX))
                #print 'transmitting'
                seq = seq + 1
        except:
            print("overflow")



ptt = False 

p = pyaudio.PyAudio()

thread.start_new_thread( rxAudioStream, () )
thread.start_new_thread( txAudioStream, () )


#Loop for read status of PTT from /tmp/PTT
device = ReadLine(s)
while True:
    p = (device.readline().decode('utf-8'))
    if p == "True" or p == "False":
      ptt = not ptt

