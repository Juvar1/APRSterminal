#! /usr/bin/python
# -*- coding: utf-8 -*-

#    APRS terminal, ver 2.0

#    Copyright (C) 2018 Juvar, Juha-Pekka Varjonen, OH1FWW

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

#    APRS symbols from http://www.aprs.org/symbols.html

import sys
from PyQt4 import QtGui, QtCore, QtWebKit
from PyQt4.QtCore import Qt, QTimer

import serial, time, re
import ax25, mice

# set serial port settings here

PORT = "/dev/rfcomm15"
BAUD = 115200

class Main(QtGui.QMainWindow):

    def __init__(self, parent = None):
        QtGui.QMainWindow.__init__(self,parent)

        self.initUI()

    def initUI(self):

        self.splitter = QtGui.QSplitter(Qt.Vertical,self)
        self.text = QtWebKit.QWebView()
        self.html = QtWebKit.QWebView()
        self.splitter.addWidget(self.html)
        self.splitter.addWidget(self.text)
        self.setCentralWidget(self.splitter)

        # x and y coordinates on the screen, width, height
        self.setGeometry(100,100,800,600)
        self.setWindowTitle("APRS Terminal")
        self.splitter.setSizes([((600/100)*70),((600/100)*30)])

        self.html.load(QtCore.QUrl("leaflet.html"))
        self.html.show()
        self.text.load(QtCore.QUrl("text.html"))
        self.text.show()

        try:
            self.ser = serial.Serial(PORT, BAUD)
        except IOError:
            print("Cannot open serial port")
            sys.exit()

        self.timer = QTimer()
        self.timer.timeout.connect(self.readSerial)
        self.timer.start(5000)

    def readSerial(self):
        aprsResult = ""
        msg = False
        while self.ser.inWaiting():
            value = self.ser.read()
            if (value == b"\xc0"): # FEND, frame start/end char (KISS protocol)
                msg = not msg
                if (msg == False):
                    data = ax25.Ax25(aprsResult)
                    self.node = {}
                    self.node["time"] = currentTime = time.ctime()
                    self.node["src"] = data.src
                    self.node["dst"] = data.dst
                    self.node["rpt"] = data.rpt
                    test = re.search(r"^(.).*(\d{4}\.\d\d[NS])(.)(\d{5}\.\d\d[EW])(.).*",data.info)
                    #Mic-E format
                    if (data.info[0] == "'" or data.info[0] == "`"):
                        decode = mice.Mice(data.dst,data.info)
                        self.node["symb"] = decode.symbol
                        self.node["lat"] = decode.lat.zfill(8)
                        self.node["lon"] = decode.lon.zfill(9)
                        content = "lat: %s, lon: %s, speed: %ikm/h, course: %i, alt: %im, status: %s, info: %s" % (decode.lat.zfill(8), decode.lon.zfill(9), decode.speed, decode.crs, decode.alt, decode.status, decode.info)
                        self.node["info"] = ["Mic-E",content]

                        #! or =, lat=8, table, long=9, code, comment
                        #! or =, lat=8, table, long=9, code, ext=7, comment
                        #! or =, lat=8, table, long=9, code, ext=7, data=8, comment
                        #! or =, table, lat=4, long=4, code, ext=2, type, comment
                        #/ or @, time=7, table, lat=4, long=4, code, ext=2, type, comment
                        #/ or @, time=7, lat=8, table, long=9, code, comment
                        #/ or @, time=7, lat=8, table, long=9, code, ext=7, comment
                        #/ or @, time=7, lat=8, table, long=9, code, ext=7, data=8, comment
                        #;, name=9, * ,time=7, lat=8, table, long=9, code, wind=7,...
                        #;, name=9,*or_,time=7,lat=8, table, long=9, code, ext=7 
                        #;, name=9,*or_,time=7,comp pos data=13,
                    elif test:
                        self.node["symb"] = test.group(3)+test.group(5)
                        self.node["lat"] = test.group(2)
                        self.node["lon"] = test.group(4)
                        if (data.info[0] == ";"):
                            self.node["info"] = ["Object",("name: %s, time: %s, lat: %s, lon: %s, info: %s" % (data.info[1:10].rstrip(),self.formatTime(data.info[11:18]),test.group(2),test.group(4),data.info))]
                        elif (data.info[0] == "!" or data.info[0] == "="):
                            self.node["info"] = ["Position","lat: %s, lon: %s, info: %s" % (test.group(2),test.group(4),data.info)]
                        elif (data.info[0] == "#" or data.info[0] == "*"):
                            self.node["info"] = ["Peet Bros U-II Weather Station",data.info]
                        elif (data.info[0] == "$"):
                            self.node["info"] = ["Raw GPS data or Ultimeter 2000",data.info]
                        elif (data.info[0] == "\%"):
                            self.node["info"] = ["Agrelo DFJr / MicroFinder",data.info]
                        elif (data.info[0] == ")"):
                            self.node["info"] = ["Item",data.info]
                        elif (data.info[0] == ","):
                            self.node["info"] = ["Invalid or test data",data.info]
                        elif (data.info[0] == "/" or data.info[0] == "@"):
                            self.node["info"] = ["Position","time: %s, lat: %s, lon: %s, info: %s" % (self.formatTime(data.info[1:8]),test.group(2),test.group(4),data.info)]
                        elif (data.info[0] == "<"):
                            self.node["info"] = ["Station capabilities",data.info]
                        elif (data.info[0] == ">"):
                            self.node["info"] = ["Status",data.info]
                        elif (data.info[0] == "?"):
                            self.node["info"] = ["Query",data.info]
                        elif (data.info[0] == "_"):
                            self.node["info"] = ["Weather report",data.info]
                        elif (data.info[0] == "{"):
                            self.node["info"] = ["User-defined format",data.info]
                        elif (data.info[0] == "}"):
                            self.node["info"] = ["Third-party format",data.info]
                        else:
                            self.node["info"] = ["Unknown format",data.info]
                    else: # compressed formats
                        self.node["lat"] = "0000.00N"
                        self.node["lon"] = "00000.00E"
                        if (data.info[0] == ";"):
                            self.node["symb"] = data.info[18]+data.info[27]
                            lat,lon = self.base91(data.info[19:23],data.info[23:27])
                            self.node["lat"] = lat
                            self.node["lon"] = lon
                            self.node["info"] = ["Object","name: %s, time: %s, lat: %s, lon: %s, info: %s" % (data.info[1:10].rstrip(),self.formatTime(data.info[11:18]),lat,lon,data.info)]
                        elif (data.info[0] == "!" or data.info[0] == "="):
                            self.node["symb"] = data.info[1]+data.info[10]
                            lat,lon = self.base91(data.info[2:6],data.info[6:10])
                            self.node["lat"] = lat
                            self.node["lon"] = lon
                            self.node["info"] = ["Position","lat: %s, lon: %s, info: %s" % (lat,lon,data.info)]
                        elif (data.info[0] == "/" or data.info[0] == "@"):
                            self.node["symb"] = data.info[8]+data.info[17]
                            lat,lon = self.base91(data.info[9:13],data.info[13:17])
                            self.node["lat"] = lat
                            self.node["lon"] = lon
                            self.node["info"] = ["Position","time: %s, lat: %s lon: %s info: %s" % (self.formatTime(data.info[1:8]),lat,lon,data.info)]
                        elif (data.info[0] == "T"):
                            self.node["info"] = ["Telemetry",data.info]
                        else:
                            self.node["info"] = ["Unknown format",data.info]
                    self.addText()
                    self.addToMap()
                    aprsResult = ""
            elif (msg == True):
                aprsResult += value

    def ddToGPS(self,dec):
        #decimal decrees to GPS coordinates
        degrees = int(dec)
        minutes = 60.0*(dec-degrees)
        return "%s%.2f" % (degrees,minutes)

    def base91(self,lat,lon): # does not convert accurate TODO
        lat = 90.0-((ord(lat[0])-33.0)*91.0**3 + (ord(lat[1])-33.0)*91.0**2 + (ord(lat[2])-33.0)*91.0 + ord(lat[3])-33.0) / 380926.0
        lon = -180.0+((ord(lon[0])-33.0)*91.0**3 + (ord(lon[1])-33.0)*91.0**2 + (ord(lon[2])-33.0)*91.0 + ord(lon[3])-33.0) / 190463.0
        if lat < 0: NS = "S"
        else: NS = "N"
        if lon < 0: EW = "W"
        else: EW = "E"
        return (self.ddToGPS(abs(lat))+NS).zfill(8), (self.ddToGPS(abs(lon))+EW).zfill(9)

    def formatTime(self,tme):
        #decode APRS time
        if(tme[-1] == "z"): return "%s' day %s:%s UTC" % (tme[0:2],tme[2:4],tme[4:6])
        if(tme[-1] == "/"): return "%s' day %s:%s Local" % (tme[0:2],tme[2:4],tme[4:6])
        if(tme[-1] == "h"): return "%s:%s.%s UTC" % (tme[0:2],tme[2:4],tme[4:6])

    def addText(self):
        frame = self.text.page().mainFrame()
        frame.evaluateJavaScript("addText(%s);" % self.node)

    def addToMap(self):
        # add to JSON list
        #with open("buffer.json", mode='r') as nodesjson:
        #    nodesPython = json.load(nodesjson)
        #    LEN = 5 # maximum length of buffer (actually +1, TODO)
        #    if len(nodesPython) > LEN:
        #        newNodesPython = json.loads("[]")
        #        # take only last ones
        #        for pos in range(len(nodesPython)-LEN,len(nodesPython)):
        #            newNodesPython.append(nodesPython[pos])
        #        nodesPython = newNodesPython
        #with open("buffer.json", mode='w') as nodesjson:
        #    nodesPython.append(self.node)
        #    json.dump(nodesPython, nodesjson)
        # add to map
        frame1 = self.html.page().mainFrame()
        frame1.evaluateJavaScript("addNode(\"%s\",\"%s\",\"%s\",\"%s\");" % (self.node["lat"],self.node["lon"],self.node["symb"],self.node["src"]))

    def closeEvent(self, event):
        self.ser.close()
        event.accept()

def main():

    app = QtGui.QApplication(sys.argv)
    main = Main()
    main.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()