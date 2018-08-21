#! /usr/bin/env python
# -*- coding: utf-8 -*-

#    APRS terminal P3, ver 2.4
#    works with Python version 3.6

#    Hard Work Done By:
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

import sys, os

from PyQt5 import QtCore, QtGui, QtWebEngineWidgets, QtWidgets
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal

from datetime import datetime

import serial, re, bluetooth
import mice, ax25

import serial.tools.list_ports

# Bluetooth search
QStringList = list

class btThread(QThread):
    btErrSignal = pyqtSignal(str)
    mySignal = pyqtSignal(list)

    def __init__(self):
        QThread.__init__(self)

    def __del__(self):
        self.wait()

    def run(self):
        ret = []
        try:
            btDevices = bluetooth.discover_devices(lookup_names = True, flush_cache = True, duration = 8)
        except bluetooth.btcommon.BluetoothError as err: 
            self.btErrSignal.emit("Info: %s" % err.args)
            return
        except OSError: #No such device (if no bt adapters)
            self.btErrSignal.emit("Info: No adapters")
            return
        for addr, name in btDevices:
        #    for rfcomm in bluetooth.find_service(uuid="0003", address=addr):
        #        ret.append([name,rfcomm["host"],rfcomm["port"]])
            ret.append([name,addr,1])
        self.mySignal.emit(ret)

# Bluetooth read
class btRead(QThread):
    btReceived = pyqtSignal(bytes)

    def __init__(self,sock):
        QThread.__init__(self)
        self.sck = sock

    def __del__(self):
        self.wait()

    def run(self):
        val = self.sck.recv(1024)
        self.btReceived.emit(val)

# Serial read
class serRead(QThread):
    serialReceived = pyqtSignal(bytes)

    def __init__(self,ser1):
        QThread.__init__(self)
        self.ser = ser1

    def __del__(self):
        self.wait()

    def run(self):
        val = ""
        val = self.ser.read(1)
        self.serialReceived.emit(val)

class Main(QtWidgets.QMainWindow):

    def __init__(self, parent = None):
        super(Main, self).__init__(parent)

        self.initUI()

    def initUI(self):

        self.splitter = QtWidgets.QSplitter(Qt.Vertical,self)
        self.text = QtWebEngineWidgets.QWebEngineView()
        self.html = QtWebEngineWidgets.QWebEngineView()
        self.splitter.addWidget(self.html)
        self.splitter.addWidget(self.text)

        # disable context menus
        self.html.setContextMenuPolicy(0)
        self.text.setContextMenuPolicy(0)

        # x and y coordinates on the screen, width, height
        self.setGeometry(100,100,800,600)
        self.setWindowTitle("APRS Terminal")
        self.splitter.setSizes([((600/100)*70),((600/100)*30)])

        path = os.path.dirname(os.path.abspath(__file__))

        self.html.load(QtCore.QUrl("file:///"+path+"/leaflet.html"))
        self.html.show()
        self.text.load(QtCore.QUrl("file:///"+path+"/text.html"))
        self.text.show()

        #create tab system
        self.tab_widget = QtWidgets.QTabWidget(self)
        self.setCentralWidget(self.tab_widget)
        #create tabs
        self.tab1 = QtWidgets.QWidget()
        self.tab2 = QtWidgets.QWidget()
        self.tab_widget.addTab(self.tab1,"Map view")
        self.tab_widget.addTab(self.tab2,"Settings")

        # create send related UI items
        lb1 = QtWidgets.QLabel("Destination")
        lb2 = QtWidgets.QLabel("ssid")
        lb3 = QtWidgets.QLabel("Source")
        lb4 = QtWidgets.QLabel("Path")
        lb5 = QtWidgets.QLabel("Message type")
        lb6 = QtWidgets.QLabel("Symbol")
        lb7 = QtWidgets.QLabel("Lat")
        lb8 = QtWidgets.QLabel("Lon")
        #lb9 = QtGui.QLabel("Message")
        lb10 = QtWidgets.QLabel("ssid")
        lb11 = QtWidgets.QLabel("ssid")
        lb12 = QtWidgets.QLabel("Table")
        self.edit1 = QtWidgets.QLineEdit()
        self.edit1.setMaxLength(6)
        self.edit1.setText("APRS")
        self.spin1 = QtWidgets.QSpinBox()
        self.spin1.setRange(0, 15)
        self.spin2 = QtWidgets.QSpinBox()
        self.spin2.setRange(0, 15)
        self.spin3 = QtWidgets.QSpinBox()
        self.spin3.setRange(0, 15)
        self.edit2 = QtWidgets.QLineEdit()
        self.edit2.setMaxLength(6)
        self.edit2.setPlaceholderText("Your call sign")
        self.edit3 = QtWidgets.QLineEdit()
        self.edit3.setText("WIDE2")
        self.edit3.setMaxLength(6)
        self.cmb1 = QtWidgets.QComboBox()
        self.cmb1.addItems(["position","status","message"])
        self.cmb1.currentIndexChanged.connect(self.changeMsgType)
        self.edit4 = QtWidgets.QLineEdit()
        self.edit4.setMaxLength(1)
        self.edit4.setMaximumWidth(50)
        self.edit5 = QtWidgets.QLineEdit()
        self.edit5.setMaxLength(8)
        self.edit5.setPlaceholderText("0000.00X")
        self.edit6 = QtWidgets.QLineEdit()
        self.edit6.setMaxLength(9)
        self.edit6.setPlaceholderText("00000.00X")
        self.edit7 = QtWidgets.QLineEdit()
        self.edit7.setPlaceholderText("Text message")
        self.edit8 = QtWidgets.QLineEdit()
        self.edit8.setMaxLength(1)
        self.edit8.setMaximumWidth(50)
        self.edit9 = QtWidgets.QLineEdit() # adressee
        self.edit9.setMaxLength(9)
        self.edit9.setPlaceholderText("Recp addr")
        bt1 = QtWidgets.QPushButton("Send")
        bt1.clicked.connect(self.sendMsg)

        sendSet = QtWidgets.QGridLayout()
        sendSet.addWidget(lb1,0,0)
        sendSet.addWidget(lb2,0,1)
        sendSet.addWidget(lb3,0,2)
        sendSet.addWidget(lb10,0,3)
        sendSet.addWidget(lb4,0,4)
        sendSet.addWidget(lb11,0,5)
        sendSet.addWidget(self.edit1,1,0)
        sendSet.addWidget(self.spin1,1,1)
        sendSet.addWidget(self.edit2,1,2)
        sendSet.addWidget(self.spin2,1,3)
        sendSet.addWidget(self.edit3,1,4)
        sendSet.addWidget(self.spin3,1,5)
        sendSet.addWidget(lb5,2,0)
        sendSet.addWidget(lb7,2,2)
        sendSet.addWidget(lb12,2,3)
        sendSet.addWidget(lb8,2,4)
        sendSet.addWidget(lb6,2,5)
        sendSet.addWidget(self.cmb1,3,0)
        sendSet.addWidget(self.edit5,3,2)
        sendSet.addWidget(self.edit4,3,3)
        sendSet.addWidget(self.edit6,3,4)
        sendSet.addWidget(self.edit8,3,5)
        
        sendl = QtWidgets.QHBoxLayout()
        sendl.setContentsMargins(0,0,0,0)
        #sendl.addWidget(lb9,1, Qt.AlignVCenter|Qt.AlignRight)
        sendl.addWidget(self.edit9,2)
        sendl.addWidget(self.edit7,10)
        sendl.addWidget(bt1,1)
        sendBox = QtWidgets.QFrame()
        sendBox.setLayout(sendl)

        #insert layout box
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.splitter)
        layout.addWidget(sendBox)
        self.tab1.setLayout(layout)
        
        # create groupboxes
        groupBox1   = QtWidgets.QGroupBox("Bluetooth")
        groupBox2   = QtWidgets.QGroupBox("Serial")
        groupBox3   = QtWidgets.QGroupBox("Station info")
        groupBox3.setLayout(sendSet)
        # create bluetooth groupbox content
        self.radio1 = QtWidgets.QRadioButton("Use Bluetooth")
        self.radio1.toggled.connect(self.radioChanged)
        self.button1= QtWidgets.QPushButton("Search devices")
        self.button1.clicked.connect(self.btSearch)
        label1      = QtWidgets.QLabel("Found devices:")
        self.combo1 = QtWidgets.QComboBox()
        self.button3= QtWidgets.QPushButton("Connect")
        self.button3.clicked.connect(self.btConnect)
        self.info   = QtWidgets.QLabel("Info: Ready")
        layout3     = QtWidgets.QGridLayout()
        groupBox1.setLayout(layout3)
        layout3.addWidget(self.radio1,0,0)
        layout3.addWidget(self.button1,0,1)
        layout3.addWidget(label1,0,2)
        layout3.addWidget(self.combo1,0,3)
        layout3.addWidget(self.button3,0,4)
        layout3.addWidget(self.info,1,0,1,4)
        # create serial groupbox content
        self.radio2 = QtWidgets.QRadioButton("Use serial")
        self.radio2.toggled.connect(self.radioChanged)
        self.button2= QtWidgets.QPushButton("Search devices")
        self.button2.clicked.connect(self.serSearch)
        label2      = QtWidgets.QLabel("Found devices:")
        self.combo2 = QtWidgets.QComboBox()
        label3      = QtWidgets.QLabel("Baud rate:")
        self.combo3 = QtWidgets.QComboBox()
        self.combo3.addItems(["1200","2400","4800","9600","19200","38400","57600","115200"])
        self.button4= QtWidgets.QPushButton("Connect")
        self.button4.clicked.connect(self.serConnect)
        layout4     = QtWidgets.QHBoxLayout()
        groupBox2.setLayout(layout4)
        layout4.addWidget(self.radio2)
        layout4.addWidget(self.button2)
        layout4.addWidget(label2)
        layout4.addWidget(self.combo2)
        layout4.addWidget(label3)
        layout4.addWidget(self.combo3)
        layout4.addWidget(self.button4)
        # create spacer
        spacer1 = QtWidgets.QLabel()
        # connect radio buttons
        buttonGroup1 = QtWidgets.QButtonGroup(self)
        buttonGroup1.addButton(self.radio1)
        buttonGroup1.addButton(self.radio2)
        self.radio1.setChecked(True)
        # insert widget groups to tab
        tabLayout = QtWidgets.QGridLayout()
        tabLayout.addWidget(groupBox1,0,0)
        tabLayout.addWidget(groupBox2,1,0)
        tabLayout.addWidget(groupBox3,2,0)
        tabLayout.addWidget(spacer1,3,0)
        self.tab2.setLayout(tabLayout)

        # update comboboxes
        #self.serSearch()
        #self.btSearch()
        self.combo1.setEnabled(False)
        self.button3.setEnabled(False)

        # initialize send box
        self.changeMsgType(0)

        # initialize connection status
        self.BT_CONNECT = False
        self.SER_CONNECT = False

        self.msg = False
        self.aprsResult = ""
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
        self.myThread.mySignal.connect(self.btDevices)
        self.myThread.btErrSignal.connect(self.btErr)
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
            QStringList1 = [] #QStringList() #[])
            self.combo1.clear() # clear combobox
            for (name, host, port) in results:
                QStringList1.append(name)
            self.combo1.addItems(QStringList1)
        else: 
            self.info.setText("Info: No devices found")
        self.btDevicelist = results

    def btDisconnect(self):
        self.BT_CONNECT = False
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
        except bluetooth.btcommon.BluetoothError as err: #, arg:
            self.info.setText("Info: %s" % err.args) #arg)
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

        self.BT_CONNECT = True
        self.rcvBt = btRead(self.sock)
        self.rcvBt.btReceived.connect(self.translateData)
        self.rcvBt.finished.connect(self.btDone)
        self.rcvBt.start()

    def btDone(self):
        if (self.BT_CONNECT): 
            self.rcvBt.start() # restart thread immediately when finished

    def btErr(self,err):
        self.info.setText(err)
        self.radio1.setEnabled(True)
        self.radio2.setEnabled(True)
        self.button1.setEnabled(True)
        self.button3.setEnabled(False)

    def serSearch(self):
        self.combo2.clear() # clear combobox
        QStringList1 = [] #QStringList([])
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
        self.SER_CONNECT = False
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
        except IOError as err: #,arg:
            print("Info: %s" % err.args) #arg)
            return
        self.button4.setText("Disconnect")
        self.button4.clicked.disconnect(self.serConnect)
        self.button4.clicked.connect(self.serDisconnect)
        self.radio1.setEnabled(False)
        self.radio2.setEnabled(False)
        self.button2.setEnabled(False)
        self.combo2.setEnabled(False)
        self.combo3.setEnabled(False)        
        self.SER_CONNECT = True
        self.rcvSer = serRead(self.ser)
        self.rcvSer.serialReceived.connect(self.translateData)
        self.rcvSer.finished.connect(self.serDone)
        self.rcvSer.start()

    def serDone(self):
        if (self.SER_CONNECT):
            self.rcvSer.start() # restart thread immediately when finished        

    def changeMsgType(self,index):
        if(index == 0): # position report
            self.edit7.setMaxLength(43)
            self.edit9.setVisible(False)
        elif(index == 1): # status report
            self.edit7.setMaxLength(62)
            self.edit9.setVisible(False)
        elif(index == 2): # message
            self.edit7.setMaxLength(67)
            self.edit9.setVisible(True)

    def encode(self,addr,cbit,ssid,ext):
        res = bytearray()
        for char in addr.upper().ljust(6):
            res.append(ord(char)<<1)
        last = 0b01100000 # reserved bits
        last += cbit << 7 # H or C bit
        last += ssid << 1
        last += ext
        res.append(last)
        return res

    def sendMsg(self):
        p1 = re.compile(r"[a-zA-Z0-9]{3,}")
        destField   = p1.match(self.edit1.text())
        sourceField = p1.match(self.edit2.text())
        repField    = p1.match(self.edit3.text())

        # table and symbol match
        table  = re.match(r".{1}",self.edit4.text())
        symbol = re.match(r".{1}",self.edit8.text())

        lat = re.match(r"\d{4}\.\d\d[NS]",self.edit5.text())
        lon = re.match(r"\d{5}\.\d\d[EW]",self.edit6.text())

        index = self.cmb1.currentIndex()

        if ((not destField) \
            or (not sourceField) \
            or (not repField) \
            or (not table and not index) \
            or (not symbol and not index) \
            or (not lat and not index) \
            or (not lon and not index)):
            reply = QtWidgets.QMessageBox.information(self,"Missing text","Please fill station information on settings page before sending anything.")
            return

        destField   = str(self.edit1.text())
        sourceField = str(self.edit2.text())
        repField    = str(self.edit3.text())

        test = re.match(r"[\|~]",self.edit7.text())
        if (test):
            reply = QtWidgets.QMessageBox.information(self,"Character not allowed","Message cannot contain '|' or '~' character")
            return
        
        # take text message and fix encode
        # python 2.7: QString != string
        # python 3  : QString does not exsist. It's a string.
        msgText = self.edit7.text()

        self.edit7.setText("")
        
        if (len(msgText) == 0): return;

        if (index == 0): # position report
            table  = str(self.edit4.text())
            symbol = str(self.edit8.text())
            lat = str(self.edit5.text())
            lon = str(self.edit6.text())
            send = "="+lat+table+lon+symbol+msgText
        elif (index == 1): # status report
            send = r">"+ msgText
        elif (index == 2): # message
            send = ":"+str(self.edit9.text()).upper().ljust(9)+":"+msgText

        msg = bytearray()
        msg.append(0xc0) #FEND
        msg.append(0)
        msg.extend(self.encode(destField,0,self.spin1.value(),0)) # destination
        msg.extend(self.encode(sourceField,0,self.spin2.value(),0)) # source
        msg.extend(self.encode(repField,0,self.spin3.value(),1)) # repeaters
        msg.append(0x03) # U frame
        msg.append(0xf0)
        msg.extend(send.encode("latin-1"))
        msg.append(0xc0) #FEND

        # Done by trial and error. Finally found working combination.
        temp = "".join(map(chr, msg))
        if(self.BT_CONNECT): self.sock.send(bytes(temp,"latin-1"))
        if(self.SER_CONNECT): self.ser.write(bytes(temp,"latin-1"))
        self.translateData(msg.decode("latin-1"), True)

    def translateData(self,val,own=False):
        for tempvalue in val:
            if (isinstance(tempvalue, int)): # devilish python3 resists normal operation
                value = chr(tempvalue)
            else:
                value = tempvalue
            if (ord(value) == 0xc0): # FEND, frame start/end char (KISS protocol)
                self.msg = not self.msg
                if (self.msg == False):
                    data = ax25.Ax25(self.aprsResult)

                    if (data.info.__len__() == 0):
                        self.msg = True
                        break

                    node = {}
                    node["time"] = datetime.now().strftime("%d %b, %H:%M")
                    node["src"] = data.src
                    node["id"] = node["src"]
                    node["dst"] = data.dst
                    node["rpt"] = data.rpt
                    test = re.search(r"^(.).*(\d{4}\.\d\d[NS])(.)(\d{5}\.\d\d[EW])(.).*",data.info)
                    #Mic-E format
                    if (data.info[0] == "'" or data.info[0] == "`"):
                        decode = mice.Mice(data.dst,data.info)
                        node["symb"] = decode.symbol
                        node["lat"] = decode.lat.zfill(8)
                        node["lon"] = decode.lon.zfill(9)
                        content = "lat: %s, lon: %s, speed: %ikm/h, course: %i, alt: %im, status: %s, info: %s" % (decode.lat.zfill(8), decode.lon.zfill(9), decode.speed, decode.crs, decode.alt, decode.status, decode.info)
                        node["info"] = ["Mic-E",content]
                    #other than Mic-E
                    elif test:
                        node["symb"] = test.group(3)+test.group(5)
                        node["lat"] = test.group(2)
                        node["lon"] = test.group(4)

                        if (data.info[0] == ";"):
                            node["id"] = data.info[1:10].rstrip()
                            if (test.group(5) == "_"):
                                # weather report format
                                gust,temp,rain1h,rain24h,rainsm,humi,pres = self.decodeWeather(data.info)
                                node["info"] = ["Weather report",("name: %s, time: %s, lat: %s, lon: %s, wind: %sdeg. %im/s, gusts: %sm/s, temp: %sC, rain 1h: %smm, rain 24h: %smm, rain since midnight: %smm, humidity: %s%%, pressure: %smbar" % (data.info[1:10].rstrip(),self.formatTime(data.info[11:18]),test.group(2),test.group(4),data.info[37:40],(float(data.info[41:44])*0.447),gust,temp,rain1h,rain24h,rainsm,humi,pres))]
                            else:
                                # other objects
                                node["info"] = ["Object",("name: %s, time: %s, lat: %s, lon: %s, info: %s" % (data.info[1:10].rstrip(),self.formatTime(data.info[11:18]),test.group(2),test.group(4),data.info))]
                        elif (data.info[0] == "!" or data.info[0] == "="):
                            if (test.group(5) == "_"):
                                # weather report format
                                gust,temp,rain1h,rain24h,rainsm,humi,pres = self.decodeWeather(data.info)
                                node["info"] = ["Weather report",("lat: %s, lon: %s, wind: %sdeg. %im/s, gusts: %sm/s, temp: %sC, rain 1h: %smm, rain 24h: %smm, rain since midnight: %smm, humidity: %s%%, pressure: %smbar" % (test.group(2),test.group(4),data.info[20:23],(float(data.info[24:27])*0.447),gust,temp,rain1h,rain24h,rainsm,humi,pres))]
                            else:
                                # other objects
                                node["info"] = ["Position","lat: %s, lon: %s, info: %s" % (test.group(2),test.group(4),data.info[20:])]
                        elif (data.info[0] == "#" or data.info[0] == "*"):
                            node["info"] = ["Peet Bros U-II Weather Station",data.info]
                        elif (data.info[0] == "$"):
                            node["info"] = ["Raw GPS data or Ultimeter 2000",data.info]
                        elif (data.info[0] == "\%"):
                            node["info"] = ["Agrelo DFJr / MicroFinder",data.info]
                        elif (data.info[0] == ")"):
                            node["info"] = ["Item",data.info]
                        elif (data.info[0] == ","):
                            node["info"] = ["Invalid or test data",data.info]
                        elif (data.info[0] == "/" or data.info[0] == "@"):
                            node["info"] = ["Position","time: %s, lat: %s, lon: %s, info: %s" % (self.formatTime(data.info[1:8]),test.group(2),test.group(4),data.info)]
                        elif (data.info[0] == r"<"):
                            node["info"] = ["Station capabilities",data.info]
                        elif (data.info[0] == "?"):
                            node["info"] = ["Query",data.info]
                        elif (data.info[0] == "_"):
                            node["info"] = ["Weather report",data.info]
                        elif (data.info[0] == "{"):
                            node["info"] = ["User-defined format",data.info]
                        elif (data.info[0] == "}"):
                            node["info"] = ["Third-party format",data.info]
                        else:
                            node["info"] = ["Unknown format",data.info]
                    else: # compressed/other formats
                        node["lat"] = "0000.00N"
                        node["lon"] = "00000.00W"
                        if (data.info[0] == ";"):
                            node["id"] = data.info[1:10].rstrip()
                            node["symb"] = data.info[18]+data.info[27]
                            lat,lon = self.base91(data.info[19:23],data.info[23:27])
                            node["lat"] = lat
                            node["lon"] = lon
                            node["info"] = ["Object","name: %s, time: %s, lat: %s, lon: %s, info: %s" % (data.info[1:10].rstrip(),self.formatTime(data.info[11:18]),lat,lon,data.info)]
                        elif (data.info[0] == "!" or data.info[0] == "="):
                            node["symb"] = data.info[1]+data.info[10]
                            lat,lon = self.base91(data.info[2:6],data.info[6:10])
                            node["lat"] = lat
                            node["lon"] = lon
                            node["info"] = ["Position","lat: %s, lon: %s, info: %s" % (lat,lon,data.info)]
                        elif (data.info[0] == "/" or data.info[0] == "@"):
                            node["symb"] = data.info[8]+data.info[17]
                            lat,lon = self.base91(data.info[9:13],data.info[13:17])
                            node["lat"] = lat
                            node["lon"] = lon
                            node["info"] = ["Position","time: %s, lat: %s lon: %s info: %s" % (self.formatTime(data.info[1:8]),lat,lon,data.info)]
                        elif (data.info[0] == r">"): # status report
                            node["symb"] = r"\."
                            timeFound = re.match(r"\d{6}[z]",data.info)
                            if(timeFound): 
                                node["info"] = ["Status","time: %s, status: %s" % (self.formatTime(data.info[1:8]),data.info[8:])]
                                node["status"] = data.info[8:]
                            else: 
                                node["info"] = ["Status", data.info[1:]]
                                node["status"] = data.info[1:]
                        elif (data.info[0] == ":"): # message
                            node["symb"] = r"\."
                            node["info"] = ["Message", "adressee: %s, message: %s" % (data.info[1:10].rstrip(),data.info[11:])]
                            node["message"] = "test"#data.info[11:]
                        elif (data.info[0] == "T"): # telemetry
                            node["symb"] = r"\."
                            node["info"] = ["Telemetry",data.info]
                        else:
                            node["symb"] = r"\."
                            node["info"] = ["Unknown format",data.info]
                    self.addTo(node,own)
                    self.aprsResult = ""
            elif (self.msg == True):
                self.aprsResult += value

    def decodeWeather(self,info):
        gust = re.search(r"g(\d{3})|.$",info).group(1)
        if (gust): gust = str("%i" % (float(gust) * 0.447)) # mph into m/s
        else: gust=""
        temp = re.search(r"t(\d{3})|.$",info).group(1)
        if (temp): temp = str("%.1f" % ((float(temp) - 32) / 1.8)) # fahrenheit into celsius
        else: temp=""
        rain1h = re.search(r"r(\d{3})|.$",info).group(1)
        if (rain1h): rain1h = str("%.1f" % (float(rain1h) * 0.254)) # hundredths of an inch into mm
        else: rain1h=""
        rain24h = re.search(r"p(\d{3})|.$",info).group(1)
        if (rain24h): rain24h = str("%.1f" % (float(rain24h) * 0.254)) # hundredths of an inch into mm
        else: rain24h=""
        rainsm = re.search(r"P(\d{3})|.$",info).group(1)
        if (rainsm): rainsm = str("%.1f" % (float(rainsm) * 0.254)) # hundredths of an inch into mm
        else: rainsm=""
        humi = re.search(r"h(\d{2})|.$",info).group(1) # what! this is already usable value...
        if (humi): humi = str("%s" % humi)
        else: humi=""
        pres = re.search(r"b(\d{5})|.$",info).group(1)
        if (pres): pres = str("%i" % (float(pres) / 10.0)) # tenths of millibar into millibar
        else: pres=""
        return gust,temp,rain1h,rain24h,rainsm,humi,pres

    def ddToGPS(self,dec):
        #decimal degrees to degrees and minutes
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

    def addTo(self,node,own=False):

        frame = self.text.page()
        frame.runJavaScript("addText(%s,%d);" % (node,own))

        # if older than 0.5 hour then remove
        for key in list(self.nodes.keys()):
            timestamp = self.nodes[key]["time"] # python3 only
            t1 = datetime.strptime(timestamp, "%d %b, %H:%M")
            t2 = datetime.now()
            diff = t2 - t1 # take timedelta value
            if (diff.seconds > 1800): #30 minutes
                del self.nodes[key]
        
        if node["id"] in self.nodes:
            self.nodes[node["id"]].update(node)
        else:
            self.nodes[node["id"]] = node

        # add to a map
        frame1 = self.html.page()
        frame1.runJavaScript("makeNodeList(%s);" % self.nodes)

    def closeEvent(self, event):
        try:
            self.sock.close()
            if (self.ser.isOpen()): self.ser.close()
        except AttributeError:
            pass # if not defined yet
        event.accept()

def main():
    del os.environ['QT_STYLE_OVERRIDE'] # remove stupid warning from startup
    app = QtWidgets.QApplication(sys.argv)
    main = Main()
    main.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
