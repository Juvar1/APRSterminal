
class Ax25():
    ssid = 0
    dst = 0
    src = 0
    rpt = [0]
    info = ""
    def __init__(self, frame):
        if (frame.__len__() > 0):
            self.decodeAx25(frame)
        else:
            pass

    def decode(self, data):
        res = []
        for char in data[:6]:
            res.append(chr(ord(char)>>1))
        addr = "".join(res)
        
        last = ord(data[6])
        #hrr = last >> 5
        ssid = (last >> 1) & 0xf
        ext = last & 0x1
        
        if ssid != 0:
            call = "%s-%d" % (addr.strip(), ssid)
        else:
            call = addr
        return (call, ssid, ext)

    def decodeAx25(self, frame):
        # destination address
        (dest_addr, dest_ssid, dest_ext) = self.decode(frame[1:8])
        self.dst = dest_addr
        
        # source address
        (src_addr, src_ssid, src_ext) = self.decode(frame[8:15])
        self.src = src_addr
        self.ssid = src_ssid
        
        # repeaters
        frame = frame[15:]
        self.rpt = []
        ext = src_ext
        while ext == 0:
            rpt_addr, rpt_ssid, ext = self.decode(frame[:7])
            self.rpt.append(rpt_addr)
            frame = frame[7:]

        # control
        ctrl = ord(frame[0])
      
        if (ctrl & 0x3) == 0x3:
            self.info = frame[2:] # U frame
        elif (ctrl & 0x3) == 0x1:
            pass # S frame
        elif (ctrl & 0x1) == 0x0:
            pass # I frame

