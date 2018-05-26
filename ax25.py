# original code from GitHub, mumrah/run.py
# https://gist.github.com/mumrah/8fe7597edde50855211e27192cce9f88
# minor bug fix and simplification by
# Juvar, Juha-Pekka Varjonen, OH1FWW, 2018

import struct

class Ax25():
    ssid = 0
    dst = 0
    src = 0
    rpt = [0]
    info = ""
    def __init__(self, frame):
        if (frame.__len__() > 0):
            self.decode(frame)
        else:
            pass

    def decode_addr(self, data, cursor):
        (a1, a2, a3, a4, a5, a6, a7) = struct.unpack("<BBBBBBB", data[cursor:cursor+7])
        hrr = a7 >> 5
        ssid = (a7 >> 1) & 0xf     
        ext = a7 & 0x1

        self.ssid = ssid

        addr = struct.pack("<BBBBBB", a1 >> 1, a2 >> 1, a3 >> 1, a4 >> 1, a5 >> 1, a6 >> 1)
        if ssid != 0:
            call = "{}-{}".format(addr.strip(), ssid)
            self.ssid = ssid
        else:
            call = addr
        return (call, hrr, ext)

    def decode(self, frame):
        pos = 0
        what_is_this = struct.unpack("<B", frame[pos])
        pos += 1

        # DST
        (dest_addr, dest_hrr, dest_ext) = self.decode_addr(frame, pos)
        pos += 7
        self.dst = dest_addr
        
        # SRC
        (src_addr, src_hrr, src_ext) = self.decode_addr(frame, pos)  
        pos += 7
        self.src = src_addr
        
        # REPEATERS
        self.rpt = []
        ext = src_ext
        while ext == 0:
            rpt_addr, rpt_hrr, ext = self.decode_addr(frame, pos)
            self.rpt.append(rpt_addr)
            pos += 7

        # CTRL
        (ctrl,) = struct.unpack("<B", frame[pos])
        pos += 1
      
        if (ctrl & 0x3) == 0x3:
            pos += 1
            self.info = frame[pos:] # U frame
        elif (ctrl & 0x3) == 0x1:
            pass # S frame
        elif (ctrl & 0x1) == 0x0:
            pass # I frame