#    MIC-E decoder
#    Ported from DireWolf C source code
#    https://github.com/wb2osz/direwolf/blob/master/decode_aprs.c
#    with minor changes and localization by 
#    Juvar, Juha-Pekka Varjonen, OH1FWW, 2018

#    Copyright (C) 2011, 2012, 2013, 2014, 2015  John Langner, WB2OSZ

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 2 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.


class Mice():

    def __init__(self, dest, info):
        self.cust_msg = 0
        self.std_msg = 0
        self.aprs_mic_e(dest, info)

    def mic_e_dest(self,c, mask):

        if (c >= "0" and c <= "9"):
            return c

        if (c >= "A" and c <= "J"):
            self.cust_msg |= mask
            return chr(ord(c) - 17)

        if (c >= "P" and c <= "Y"):
            self.std_msg |= mask
            return chr(ord(c) - 32)

        # K, L, Z should be converted to space.
        # others are invalid.
        # But caller expects only values 0 - 9.

        if (c == "K"):
            self.cust_msg |= mask
            return 0

        if (c == "L"):
            return 0

        if (c == "Z"):
            self.std_msg |= mask
            return 0

        raise ValueError("Invalid character \"%c\" in MIC-E destination/latitude" % c)
        return 0

    def aprs_mic_e(self, dest, info):
        std_text = ["Emergency", "Priority", "Special", "Committed", "Returning", "In Service", "En Route", "Off Duty"]
        cust_text = ["Emergency", "Custom-6", "Custom-5", "Custom-4", "Custom-3", "Custom-2", "Custom-1", "Custom-0" ]

        g_lat = \
            int(self.mic_e_dest(dest[0], 4)) * 1000 +\
            int(self.mic_e_dest(dest[1], 2)) * 100 +\
            int(self.mic_e_dest(dest[2], 1)) * 10 +\
            int(self.mic_e_dest(dest[3], 0)) +\
            float(self.mic_e_dest(dest[4], 0)) / 10 +\
            float(self.mic_e_dest(dest[5], 0)) / 100

        # 4th character of desination indicates north / south

        if (((dest[3] >= "0") and (dest[3] <= "9")) or (dest[3] == "L")):
            #South
            self.lat = "%.2f%c" % (g_lat,"S")
        elif ((dest[3] >= "P") and (dest[3] <= "Z")):
            #north
            self.lat = "%.2f%c" % (g_lat,"N")
        else:
            raise ValueError("Invalid MIC-E N/S encoding in 4th character of destination")

        # Longitude is mostly packed into 3 bytes of message but
        # has a couple bits of information in the destination.

        if (((dest[4] >= "0") and (dest[4] <= "9")) or (dest[4] == "L")):
            offset = 0
        elif ((dest[4] >= "P") and (dest[4] <= "Z")):
            offset = 1
        else:
            offset = 0
            raise ValueError("Invalid MIC-E Longitude Offset in 5th character of destination")

        # First character of information field is longitude in degrees.
        # It is possible for the unprintable DEL character to occur here.

        # 5th character of desination indicates longitude offset of +100.
        # Not quite that simple :-(

        ch = ord(info[1])
        if ((offset and (ch >= 118)) and (ch <= 127)):
            g_lon = (ch - 118) * 100 # 0 - 9 degrees
        elif (((not offset) and (ch >= 38)) and (ch <= 127)):
            g_lon = ((ch - 38) + 10) * 100 # 10 - 99 degrees
        elif ((offset and (ch >= 108)) and (ch <= 117)):
            g_lon = ((ch - 108) + 100) * 100 # 100 - 109 degrees
        elif ((offset and (ch >= 38)) and (ch <= 107)):
            g_lon = ((ch - 38) + 100) * 100 # 110 - 179 degrees
        else:
            raise ValueError("Invalid character 0x%x for MIC-E Longitude Degrees" % ch)
            return

        # Second character of information field is A->g_longitude minutes.
        # These are all printable characters.

        ch = ord(info[2])
        if ((ch >= 88) and (ch <= 97)):
            g_lon += (ch - 88)  # 0 - 9 minutes
        elif ((ch >= 38) and (ch <= 87)):
            g_lon += ((ch - 38) + 10)   # 10 - 59 minutes
        else:
            raise ValueError("Invalid character 0x%x for MIC-E Longitude Minutes" % ch)
            return

        # Third character of information field is longitude hundredths of minutes.
        # There are 100 possible values, from 0 to 99.
        # Note that the range includes 4 unprintable control characters and DEL.

        ch = ord(info[3])
        if ((ch >= 28) and (ch <= 127)):
            g_lon += ((ch - 28) + 0) / 100.0 # 0 - 99 hundredths of minutes
        else:
            raise ValueError("Invalid character 0x%x for MIC-E Longitude hundredths of Minutes" % ch)
            return

        # 6th character of destintation indicates east / west

        if (((dest[5] >= "0") and (dest[5] <= "9")) or (dest[5] == "L")):
	        # East
            self.lon = "%.2f%c" % (g_lon,"E")
        elif ((dest[5] >= "P") and (dest[5] <= "Z")):
            # West
            self.lon = "%.2f%c" % (g_lon,"W")
        else: 
            raise ValueError("Invalid MIC-E E/W encoding in 6th character of destination");	  

        # Message type from two 3-bit codes

        if (self.std_msg == 0 and self.cust_msg == 0):
            mic_e_status = "Emergency"
        elif (self.std_msg == 0 and self.cust_msg != 0):
            mic_e_status = cust_text[self.cust_msg]
        elif (self.std_msg != 0 and self.cust_msg == 0):
            mic_e_status = std_text[self.std_msg]
        else:
            mic_e_status = "Unknown MIC-E Message Type"
        self.status = mic_e_status

        # Speed and course from next 3 bytes
        
        n = ((ord(info[4]) - 28) * 10) + ((ord(info[5]) - 28) / 10)
        if (n >= 800): n -= 800
        self.speed = n * 1.852

        n = ((ord(info[5]) - 28) % 10) * 100 + (ord(info[6]) - 28)
        if (n >= 400): n -= 400

        if (n == 360):
            self.crs = 0
        else: 
            self.crs = n

        # An optional altitude is next
        # It is three base-91 digits followed by "}"
        
        self.alt = 0
        index = info.find("}",11,14)
        if (index > 0):
            self.alt = ((ord(info[index-3])-33)*91*91 + (ord(info[index-2])-33)*91 + (ord(info[index-1])-33) - 10000)
            self.info = info[index+1:]
        else:
            self.info = info[9:]
