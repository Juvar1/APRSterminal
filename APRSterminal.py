#! /usr/bin/python
# -*- coding: utf-8 -*-

#    APRS terminal, ver 2.1

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
from PyQt4.QtCore import Qt, QTimer, QThread, SIGNAL

from datetime import datetime

import bluetooth, serial, re
import ax25, mice

import serial.tools.list_ports

# Bluetooth search
class btThread(QThread):
    def __init__(self):
        QThread.__init__(self)

    def __del__(self):
        self.wait()

    def run(self):
        ret = []
        try:
            btDevices = bluetooth.discover_devices(lookup_names = True, flush_cache = True, duration = 8)
        except bluetooth.btcommon.BluetoothError, arg:
            self.emit(SIGNAL("btErrSignal"),"Info: %s" % arg)
            return
        for addr, name in btDevices:
        #    for rfcomm in bluetooth.find_service(uuid="0003", address=addr):
        #        ret.append([name,rfcomm["host"],rfcomm["port"]])
            ret.append([name,addr,1])
        self.emit(SIGNAL("mySignal"), ret)

# Bluetooth read
class btRead(QThread):
    def __init__(self,sock):
        QThread.__init__(self)
        self.sck = sock

    def __del__(self):
        self.wait()

    def run(self):
        val = self.sck.recv(1024)
        self.emit(SIGNAL("btReceived"),val)

# Serial read
class serRead(QThread):
    def __init__(self,ser1):
        QThread.__init__(self)
        self.ser = ser1

    def __del__(self):
        self.wait()

    def run(self):
        val = self.ser.read(1)
        self.emit(SIGNAL("serialReceived"),val)

class Main(QtGui.QMainWindow):

    def __init__(self, parent = None):
        #QtGui.QMainWindow.__init__(self,parent)
        super(Main, self).__init__(parent)

        self.initUI()

    def initUI(self):

        self.splitter = QtGui.QSplitter(Qt.Vertical,self)
        self.text = QtWebKit.QWebView()
        self.html = QtWebKit.QWebView()
        self.splitter.addWidget(self.html)
        self.splitter.addWidget(self.text)

        # create menubar
        #menubar = self.menuBar()
        #self.btMenu = menubar.addMenu("Bluetooth")
        #self.serialMenu = menubar.addMenu("Serial port")

        # x and y coordinates on the screen, width, height
        self.setGeometry(100,100,800,600)
        self.setWindowTitle("APRS Terminal")
        self.splitter.setSizes([((600/100)*70),((600/100)*30)])

        self.html.load(QtCore.QUrl("leaflet.html"))
        self.html.show()
        self.text.load(QtCore.QUrl("text.html"))
        self.text.show()

        #create tab system
        self.tab_widget = QtGui.QTabWidget(self)
        self.setCentralWidget(self.tab_widget)
        #create tabs
        self.tab1 = QtGui.QWidget()
        self.tab2 = QtGui.QWidget()
        self.tab_widget.addTab(self.tab1,"Map view")
        self.tab_widget.addTab(self.tab2,"Settings")
        #insert layout box
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.splitter)
        self.tab1.setLayout(layout)
        
        # create groupboxes
        groupBox1   = QtGui.QGroupBox("Bluetooth")
        groupBox2   = QtGui.QGroupBox("Serial")
        # create bluetooth groupbox content
        self.radio1 = QtGui.QRadioButton("Use Bluetooth")
        self.radio1.toggled.connect(self.radioChanged)
        self.button1     = QtGui.QPushButton("Search devices")
        self.button1.clicked.connect(self.btSearch)
        label1      = QtGui.QLabel("Found devices:")
        self.combo1 = QtGui.QComboBox()
        self.button3= QtGui.QPushButton("Connect")
        self.button3.clicked.connect(self.btConnect)
        self.info   = QtGui.QLabel("Info: Ready")
        layout3     = QtGui.QGridLayout()
        groupBox1.setLayout(layout3)
        layout3.addWidget(self.radio1,0,0)
        layout3.addWidget(self.button1,0,1)
        layout3.addWidget(label1,0,2)
        layout3.addWidget(self.combo1,0,3)
        layout3.addWidget(self.button3,0,4)
        layout3.addWidget(self.info,1,0,1,4)
        # create serial groupbox content
        self.radio2 = QtGui.QRadioButton("Use serial")
        self.radio2.toggled.connect(self.radioChanged)
        self.button2= QtGui.QPushButton("Search devices")
        self.button2.clicked.connect(self.serSearch)
        label2      = QtGui.QLabel("Found devices:")
        self.combo2 = QtGui.QComboBox()
        label3      = QtGui.QLabel("Baud rate:")
        self.combo3 = QtGui.QComboBox()
        self.combo3.addItems(["1200","2400","4800","9600","19200","38400","57600","115200"])
        self.button4= QtGui.QPushButton("Connect")
        self.button4.clicked.connect(self.serConnect)
        layout4     = QtGui.QHBoxLayout()
        groupBox2.setLayout(layout4)
        layout4.addWidget(self.radio2)
        layout4.addWidget(self.button2)
        layout4.addWidget(label2)
        layout4.addWidget(self.combo2)
        layout4.addWidget(label3)
        layout4.addWidget(self.combo3)
        layout4.addWidget(self.button4)
        # create spacer
        spacer1 = QtGui.QLabel()
        # connect radio buttons
        buttonGroup1 = QtGui.QButtonGroup(self)
        buttonGroup1.addButton(self.radio1)
        buttonGroup1.addButton(self.radio2)
        self.radio1.setChecked(True)
        # insert widget groups to tab
        tabLayout = QtGui.QGridLayout()
        tabLayout.addWidget(groupBox1,0,0)
        tabLayout.addWidget(groupBox2,1,0)
        tabLayout.addWidget(spacer1,2,0,3,0)
        self.tab2.setLayout(tabLayout)

        # update comboboxes
        #self.serSearch()
        #self.btSearch()
        self.combo1.setEnabled(False)
        self.button3.setEnabled(False)

        self.msg = False     #XXX
        self.aprsResult = "" #XXX
        self.nodes = {}

    def radioChanged(self):
        if (self.radio1.isChecked()):
            # enable bluetooth settings
            self.button1.setEnabled(True)
            if (self.combo1.count() > 0):
                self.combo1.setEnabled(True)
                self.button3.setEnabled(True)
            # disable serial settings
            self.button2.setEnabled(False)
            self.combo2.setEnabled(False)
            self.combo3.setEnabled(False)
            self.button4.setEnabled(False)
        if (self.radio2.isChecked()):
            # disable bluetooth settings
            self.button1.setEnabled(False)
            self.combo1.setEnabled(False)
            self.button3.setEnabled(False)
            # enable serial settings
            self.button2.setEnabled(True)
            if (self.combo2.count() > 0):
                self.button4.setEnabled(True)
                self.combo2.setEnabled(True)
                self.combo3.setEnabled(True)

    def btSearch(self):
        self.info.setText("Info: Searching devices...")
        # disable user inputs
        self.radio1.setEnabled(False)
        self.radio2.setEnabled(False)
        self.button1.setEnabled(False)
        self.combo1.setEnabled(False)
        self.button3.setEnabled(False)
        self.combo1.clear() # clear combobox
        self.myThread = btThread()
        self.connect(self.myThread, SIGNAL("mySignal"), self.btDevices)
        self.connect(self.myThread, SIGNAL("btErrSignal"), self.btErr)
        self.myThread.start()

    def btDevices(self,results):
        # enable user inputs
        self.radio1.setEnabled(True)
        self.radio2.setEnabled(True)
        self.button1.setEnabled(True)
        # print info
        if(len(results) > 0): 
            self.info.setText("Info: Found %d devices" % len(results))
            self.combo1.setEnabled(True)
            self.button3.setEnabled(True)
            # iterate results
            QStringList1 = QtCore.QStringList([])
            self.combo1.clear() # clear combobox
            for (name, host, port) in results:
                QStringList1.append(name)
            self.combo1.addItems(QStringList1)
        else: 
            self.info.setText("Info: No devices found")
        self.btDevicelist = results

    def btDisconnect(self):
        self.BT_UNCONNECT = True
        #try:
        # terminate thread
        #self.rcvBt.quit()
        #self.rcvBt.wait(1000)
        self.rcvBt.terminate()
        # close socket
        self.sock.shutdown(2) # socket.SHUT_RDWR = 2
        self.sock.close()
        #except AttributeError:
        #    pass # if this is first time to be there
        self.info.setText("Info: Disconnected")
        self.button3.setText("Connect")
        self.radio1.setEnabled(True)
        self.radio2.setEnabled(True)
        self.button1.setEnabled(True)
        self.combo1.setEnabled(True)
        self.button3.setEnabled(True)
        self.button3.clicked.disconnect(self.btDisconnect)
        self.button3.clicked.connect(self.btConnect)

    def btConnect(self):
        # retrieve host and port
        host = self.btDevicelist[self.combo1.currentIndex()][1]
        port = self.btDevicelist[self.combo1.currentIndex()][2]
        try:
            self.sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            self.sock.connect((host, port))
        except bluetooth.btcommon.BluetoothError, arg:
            self.info.setText("Info: %s" % arg)
            return
        self.button3.setText("Disconnect")
        self.info.setText("Info: Succesfully connected to host: %s and to port: %s" % (host,port))
        self.radio1.setEnabled(False)
        self.radio2.setEnabled(False)
        self.button1.setEnabled(False)
        self.combo1.setEnabled(False)
        self.button3.setEnabled(True)
        self.button3.clicked.disconnect(self.btConnect)
        self.button3.clicked.connect(self.btDisconnect)

        self.BT_UNCONNECT = False
        self.rcvBt = btRead(self.sock)
        self.connect(self.rcvBt, SIGNAL("btReceived"),self.translateData)
        self.connect(self.rcvBt, SIGNAL("finished()"), self.btDone)
        self.rcvBt.start()

    def btDone(self):
        if (not self.BT_UNCONNECT): 
            self.rcvBt.start() # restart thread immediately when finished

    def btErr(self,err):
        self.info.setText(err)
        self.radio1.setEnabled(True)
        self.radio2.setEnabled(True)
        self.button1.setEnabled(True)
        self.button3.setEnabled(False)

    def serSearch(self):
        self.combo2.clear() # clear combobox
        QStringList1 = QtCore.QStringList([])
        for value in serial.tools.list_ports.comports():
            QStringList1.append(str(value[0]))
        self.combo2.addItems(QStringList1)
        if (self.combo2.count() == 0):
            self.combo2.setEnabled(False)
            self.combo3.setEnabled(False)
            self.button4.setEnabled(False)
        else:
            self.combo2.setEnabled(True)
            self.combo3.setEnabled(True)
            self.button4.setEnabled(True)

    def serDisconnect(self):
        self.SER_UNCONNECT = True
        self.rcvSer.terminate()
        self.ser.close()
        self.button4.setText("Connect")
        self.radio1.setEnabled(True)
        self.radio2.setEnabled(True)
        self.button2.setEnabled(True)
        self.combo2.setEnabled(True)
        self.combo3.setEnabled(True)        
        self.button4.clicked.disconnect(self.serDisconnect)
        self.button4.clicked.connect(self.serConnect)

    def serConnect(self):
        baud = int(self.combo3.currentText())
        port = str(self.combo2.currentText())
        try:
            self.ser = serial.Serial(port, baud)
        except IOError,arg:
            print("Info: %s" % arg)
            return
        self.button4.setText("Disconnect")
        self.button4.clicked.disconnect(self.serConnect)
        self.button4.clicked.connect(self.serDisconnect)
        self.radio1.setEnabled(False)
        self.radio2.setEnabled(False)
        self.button2.setEnabled(False)
        self.combo2.setEnabled(False)
        self.combo3.setEnabled(False)        
        self.SER_UNCONNECT = False
        self.rcvSer = serRead(self.ser)
        self.connect(self.rcvSer, SIGNAL("serialReceived"),self.translateData)
        self.connect(self.rcvSer, SIGNAL("finished()"), self.serDone)
        self.rcvSer.start()

    def serDone(self):
        if (not self.SER_UNCONNECT):
            self.rcvSer.start() # restart thread immediately when finished        

    def translateData(self,val):
        #aprsResult = ""
        #msg = False
        for value in val:
            if (value == "\xc0"): # FEND, frame start/end char (KISS protocol)
                self.msg = not self.msg
                if (self.msg == False):
                    data = ax25.Ax25(self.aprsResult)
                    
                    if (data.info.__len__() == 0):
                        self.msg = True
                        break
                    
                    self.node = {}
                    self.node["time"] = datetime.now().strftime("%c") #time.ctime()
                    self.node["src"] = data.src
                    self.node["dst"] = data.dst
                    self.node["rpt"] = data.rpt
                    test = re.search(r"^(.).*(\d{4}\.\d\d[NS])(.)(\d{5}\.\d\d[EW])(.).*",data.info)
                    #Mic-E format
                    if (data.info[0] == "'" or data.info[0] == "`"):
                        self.node["id"] = self.node["src"]
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

                        self.node["id"] = self.node["src"]
                        for key in self.nodes:
                            oldlat = self.nodes[key]["lat"]
                            oldlon = self.nodes[key]["lon"]
                            if (key == self.node["src"]):
                                if ((self.node["lat"] != oldlat) or (self.node["lon"] != oldlon)):
                                    self.node["id"] = self.node["src"] + datetime.now().strftime("%H%M%S%f")

                        if (data.info[0] == ";"):
                            if (test.group(5) == "_"):
                                # weather report format
                                gust,temp,rain1h,rain24h,rainsm,humi,pres = self.decodeWeather(data.info)
                                self.node["info"] = ["Weather report",("name: %s, time: %s, lat: %s, lon: %s, wind: %sdeg. %im/s, gusts: %sm/s, temp: %sC, rain 1h: %smm, rain 24h: %smm, rain since midnight: %smm, humidity: %s%%, pressure: %smbar" % (data.info[1:10].rstrip(),self.formatTime(data.info[11:18]),test.group(2),test.group(4),data.info[37:40],(float(data.info[41:44])*0.447),gust,temp,rain1h,rain24h,rainsm,humi,pres))]
                            else:
                                # other objects
                                self.node["info"] = ["Object",("name: %s, time: %s, lat: %s, lon: %s, info: %s" % (data.info[1:10].rstrip(),self.formatTime(data.info[11:18]),test.group(2),test.group(4),data.info))]
                        elif (data.info[0] == "!" or data.info[0] == "="):
                            if (test.group(5) == "_"):
                                # weather report format
                                gust,temp,rain1h,rain24h,rainsm,humi,pres = self.decodeWeather(data.info)
                                self.node["info"] = ["Weather report",("lat: %s, lon: %s, wind: %sdeg. %im/s, gusts: %sm/s, temp: %sC, rain 1h: %smm, rain 24h: %smm, rain since midnight: %smm, humidity: %s%%, pressure: %smbar" % (test.group(2),test.group(4),data.info[20:23],(float(data.info[24:27])*0.447),gust,temp,rain1h,rain24h,rainsm,humi,pres))]
                            else:
                                # other objects
                                self.node["info"] = ["Position","lat: %s, lon: %s, info: %s" % (test.group(2),test.group(4),data.info[20:])]
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
                        elif (data.info[0] == r"<"):
                            self.node["info"] = ["Station capabilities",data.info]
                        elif (data.info[0] == r">"):
                            self.node["info"] = ["Status","time: %s, info: %s" % (self.formatTime(data.info[1:8]),data.info[8:])]
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
                        self.node["id"] = self.node["src"] + datetime.now().strftime("%H%M%S%f")
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
                            self.node["symb"] = "/0"
                            self.node["info"] = ["Telemetry",data.info]
                        else:
                            self.node["symb"] = "/0"
                            self.node["info"] = ["Unknown format",data.info]
                    self.addText()
                    self.addToMap()
                    self.aprsResult = ""
            elif (self.msg == True):
                self.aprsResult += value

    def decodeWeather(self,info):
        gust = re.search(r"g(\d{3})|.$",info).group(1)
        if (gust): gust = str("%i" % (float(gust) * 0.447)) # mph into m/s
        temp = re.search(r"t(\d{3})|.$",info).group(1)
        if (temp): temp = str("%.1f" % ((float(temp) - 32) / 1.8)) # fahrenheit into celsius
        rain1h = re.search(r"r(\d{3})|.$",info).group(1)
        if (rain1h): rain1h = str("%.1f" % (float(rain1h) * 0.254)) # hundredths of an inch into mm
        rain24h = re.search(r"p(\d{3})|.$",info).group(1)
        if (rain24h): rain24h = str("%.1f" % (float(rain24h) * 0.254)) # hundredths of an inch into mm
        rainsm = re.search(r"P(\d{3})|.$",info).group(1)
        if (rainsm): rainsm = str("%.1f" % (float(rainsm) * 0.254)) # hundredths of an inch into mm
        humi = re.search(r"h(\d{2})|.$",info).group(1) # what! this is already usable value...
        if (humi): humi = str("%s" % humi)
        pres = re.search(r"b(\d{5})|.$",info).group(1)
        if (pres): pres = str("%i" % (float(pres) / 10.0)) # tenths of millibar into millibar
        return gust,temp,rain1h,rain24h,rainsm,humi,pres

    def ddToGPS(self,dec):
        #decimal decrees to GPS coordinates
        degrees = int(dec)
        minutes = 60.0*(dec-degrees)
        return "%s%.2f" % (degrees,minutes)

    def base91(self,lat,lon):
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
        # add into JSON list
        #with open("buffer.json", mode='r') as nodesjson:
        #    nodesPython = json.load(nodesjson)
        #    LEN = 5 # maximum length of buffer (actually +1, TODO)
        #    if (len(nodesPython) > LEN):
        #        newNodesPython = json.loads("[]")
        #        # take only last ones
        #        for pos in range(len(nodesPython)-LEN,len(nodesPython)):
        #            newNodesPython.append(nodesPython[pos])
        #        nodesPython = newNodesPython
        #with open("buffer.json", mode='w') as nodesjson:
        #    nodesPython.append(self.node)
        #    json.dump(nodesPython, nodesjson)

        # if older than 0.5 hour then remove
        for key in list(self.nodes.keys()):
            timestamp = self.nodes[key]["time"]
            t1 = datetime.strptime(timestamp, "%c")
            t2 = datetime.now()
            diff = t2 - t1 # take timedelta value
            if (diff.seconds > 1800): #30 minutes
                del self.nodes[key]

        self.nodes[self.node["id"]] = self.node

        # add to map
        frame1 = self.html.page().mainFrame()
        frame1.evaluateJavaScript("makeNodeList(%s);" % self.nodes)

    def closeEvent(self, event):
        try:
            self.sock.close()
            if (self.ser.isOpen()): self.ser.close()
        except AttributeError:
            pass # if not defined yet
        event.accept()

def main():

    app = QtGui.QApplication(sys.argv)
    main = Main()
    main.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()