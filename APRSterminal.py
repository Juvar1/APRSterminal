#! /usr/bin/python
# -*- coding: utf-8 -*-

# APRS terminal

import wx
import wx.xrc
import wx.richtext
import serial
import ax25
import mice
import time

# set serial port settings here

PORT = "/dev/rfcomm13"
BAUD = 115200

class MyFrame(wx.Frame):

    def __init__(self):
        wx.Frame.__init__(self, parent=None, id = wx.ID_ANY, title = u"APRS Terminal", pos = wx.DefaultPosition, size = wx.Size(500,400), style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL)
        bSizer1 = wx.BoxSizer(wx.VERTICAL) 
        self.rtc = wx.richtext.RichTextCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.TE_READONLY|wx.VSCROLL|wx.HSCROLL|wx.NO_BORDER|wx.WANTS_CHARS)
        self.rtc.SetBackgroundColour(wx.Colour(80,80,80))
        bSizer1.Add(self.rtc, 1, wx.EXPAND |wx.ALL, 5)
        self.SetSizer(bSizer1)
        self.Layout()
        self.Centre(wx.BOTH)
        self.timer = wx.Timer(self)
        
class MyApp(wx.App):

    def OnInit(self):
        self.frame = MyFrame()
        
        self.rtc = self.frame.rtc
        
        self.Bind(wx.EVT_TIMER, self.update, self.frame.timer)
        self.frame.timer.Start(5000)
        
        self.SetTopWindow(self.frame)
        self.frame.Show()

        self.rtc.BeginAlignment(wx.TEXT_ALIGNMENT_CENTRE)
        self.rtc.BeginFontSize(14)
        self.rtc.BeginTextColour((0,240,0))
        self.rtc.WriteText("Welcome to using APRS Terminal!\n")
        self.rtc.BeginAlignment(wx.TEXT_ALIGNMENT_CENTRE)
        self.rtc.BeginFontSize(8)
        self.rtc.BeginTextColour((255,255,255))
        self.rtc.WriteText("Version 1.0\n")
        self.rtc.BeginAlignment(wx.TEXT_ALIGNMENT_LEFT)
        self.rtc.BeginFontSize(10)

        readSerial(self)
        return True
  
    def OnClose(self, e):
        ser.close()
        self.frame.Destroy()

    def update(self, event):
        readSerial(self)

try:
    ser = serial.Serial(PORT, BAUD)
except IOError:
    print("Cannot open serial port")
    exit()

def readSerial(self):
    aprsResult = ""
    msg = False
    while ser.inWaiting():
        value = ser.read()
        if (value == b"\xc0"): # FEND, frame start/end char (KISS protocol)
            msg = not msg
            if (msg == False):
                data = ax25.Ax25(aprsResult)
                self.rtc.SetInsertionPointEnd()
                #self.rtc.SetInsertionPoint(self.rtc.GetLastPosition())
                self.rtc.BeginTextColour((240,240,0))
                self.rtc.WriteText("\n%s\n" % time.ctime())
                self.rtc.WriteText("\tDestination: ")
                self.rtc.BeginTextColour((240,240,240))
                self.rtc.WriteText("%s\n" % data.dst)
                self.rtc.BeginTextColour((240,240,0))
                self.rtc.WriteText("\tSource: ")
                self.rtc.BeginTextColour((240,240,240))
                self.rtc.WriteText("%s\n" % data.src)
                items = ""
                for item in data.rpt: items += item+","
                self.rtc.BeginTextColour((240,240,0))
                self.rtc.WriteText("\tRepeaters: ")
                self.rtc.BeginTextColour((240,240,240))
                self.rtc.WriteText("%s\n" % items)
                if (data.info[0] == "'" or data.info[0] == "`"):
                    decode = mice.Mice(data.dst,data.info)
                    self.rtc.BeginTextColour((240,240,0))
                    self.rtc.WriteText("\tMIC-E: ")
                    self.rtc.BeginTextColour((240,240,240))
                    self.rtc.WriteText("lat: %g, lon: %g, speed: %ikm/h, course: %i, alt: %im, status: %s, info: %s\n" % (decode.lat, decode.lon, decode.speed, decode.crs, decode.alt, decode.status, decode.info))
                else:
                    self.rtc.BeginTextColour((240,240,0))
                    self.rtc.WriteText("\tInfo: ")
                    self.rtc.BeginTextColour((240,240,240))
                    self.rtc.WriteText("%s\n" % data.info)
                aprsResult = ""
                self.rtc.ShowPosition(self.rtc.GetCaretPosition())
        elif (msg == True):
            aprsResult += value

app = MyApp(False)
app.MainLoop()