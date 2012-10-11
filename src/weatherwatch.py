#! /usr/bin/env python

import serial
import array

TTY = "/dev/ttyS1"

wind_tag = "Anometer"
rain_tag = "Rain Gauge"
mushroom_tag = "Outdoor Thermomenter, Hygrometer"
minute_tag = "Minute"
indoor_tag = "Indoor Temp, Baro and Higro Gauge"

class Decoder:
    
    def __init__(self):     
        self.ser = serial.Serial(port=TTY, baudrate=9600, bytesize=8, parity='N')
        self.handlers = {0: self._doWind, # wind
                         1: self._doRain, # rain
                         2: self._doTH,
                         3: self._doMushroom, # Mushroom - Outdoor Thermo-Hygrometer 
                         4: self._doT,
                         5: self._doTHB,
                         6: self._doIndoorTempBaro, # Indoor Temp Baro
                         14: self._doMinute, # Minute
                         15: self._doClock} # Clock
    
    #@log()
    def _doWind(self, code):
        len = 8 # rain frame + checksum
        frame = self._getFrame(len)
        if not self._cksum(code, frame):
            print "Cheksum failed"
            return
        
        self._testBattery(frame[0] & 0x40, wind_tag)
        
        # wind thresholds
        avrover = False
        gustover = False
        if frame[0] & 0x20: avrover = True # average over
        if frame[0] & 0x10: gustover = True # gust over
        
        # wind direction
        dir = self._decodeBCD(frame[1])
        dir += self._decodeBCD(frame[2] & 0xf) * 100
        
        # gust speed
        gustspeed = self._decodeBCD(frame[2] & 0xf0) / 100.0
        gustspeed += self._decodeBCD(frame[3])
        
        # avarage speed
        avrspeed = self._decodeBCD(frame[4]) / 10.0
        avrspeed += self._decodeBCD(frame[5] & 0xf) * 10.0
        
        # windchil 
        chillnodata = False
        chillover = False
        chillsign = False
        if (frame[5] & 0x20): chillnodata = True
        if (frame[5] & 0x40): chillover = True
        if (frame[5] & 0x80): chillsign = True
        windchill = self._decodeBCD(frame[6]);
        if chillsign: windchill *= -1.0;
        
        self._printMeasurements(["Wind:", avrover, gustover, dir, gustspeed, avrspeed, windchill])
        
    def _doRain(self, code):
        len = 13 # rain frame + checksum
        frame = self._getFrame(len)
        if not self._cksum(code, frame):
            print "Cheksum failed"
            return
        self._testBattery(frame[0] & 0x40, rain_tag)
         
        # current rain
        currentRain = self._decodeBCD(frame[1])
        currentRain += self._decodeBCD(frame[2] & 0xf) * 100.0
        
        # toatal rain
        totalRain = (self._decodeBCD(frame[2] & 0xf0)) / 100.0
        totalRain += self._decodeBCD(frame[3])
        totalRain += self._decodeBCD(frame[4]) * 100.0
        
        yesterdayRain = self._decodeBCD(frame[5])
        yesterdayRain += self._decodeBCD(frame[6]) * 100.0
        
        # total start date
        totalStartdate = "%02d%02d%02d%02d%02d" % (self._decodeBCD(frame[11]),
                                                   self._decodeBCD(frame[10]),
                                                   self._decodeBCD(frame[9]),
                                                   self._decodeBCD(frame[8]),
                                                   self._decodeBCD(frame[7])
                                                   )
        rateover = False
        if (frame[0] & 0x10): rateover = True
        totalover = False
        if (frame[0] & 0x20): totalover = True
        yesterdayover = False
        if (frame[0] & 0x80): yesterdayover = True
        
        self._printMeasurements(["Rain", currentRain, totalRain, yesterdayRain, totalStartdate, rateover, totalover])
     
        
    def _doTH(self, code):
        """ """
    
    def _doMushroom(self, code):
        """ Mushroom - Outdoor Thermo-Hygrometer """
        
        len = 6 
        frame = self._getFrame(len)
        if not self._cksum(code, frame):
            print "Cheksum failed"
            return
        self._testBattery(frame[0] & 0x40, mushroom_tag)
        
        # temperature
        temp = self._decodeBCD(frame[1]) * 0.1
        temp += self._decodeBCD(frame[2] & 0x3f) * 10.0
        # humidity
        hum = self._decodeBCD(frame[3]) 
        # dewpoint
        dew = self._decodeBCD(frame[4]) * 100
        
        overunder = False
        if (frame[0] & 0x40): overunder = True
        sign = False
        if (frame[0] & 0x80): sign = True
        if sign: temp *= -1
        
        dewunder = False
        if (frame[0] & 0x10): dewunder = True 
        
        self._printMeasurements(["OTH", temp, hum, dewunder, dew])
       
        
    def _doT(self, code):
        """ """
        
    def _doTHB(self, code):
        """ """
        
    def _doIndoorTempBaro(self, code):
        len = 11
        frame = self._getFrame(len)
        if not self._cksum(code, frame):
            print "Cheksum failed"
            return
        self._testBattery(frame[0] & 0x40, indoor_tag)
        
        minute = "%02d" % self._decodeBCD(frame[0] & 0x7f)
        
        self._printMeasurements(["Minute", minute])
        
        
    def _doMinute(self, code):
        """ read minute value"""
        
        len = 1
        frame = self._getFrame(len)
        if not self._cksum(code, frame):
            print "Cheksum failed"
            return
        self._testBattery(frame[0] & 0x80, minute_tag)
        
        minute = "%02d" % self._decodeBCD(frame[0] & 0x7f)
        
        self._printMeasurements(["Minute", minute])
                                 
    def _doClock(self, code):
        """ """
    
    def _readByte(self):    
        data = array.array('B', self.ser.read())
        return data[0]
    
    def _getFrame(self, len):
        return array.array('B', self.ser.read(len))

    def getStart(self):
        """ read the byte stream until a 0xff0xff pair is found"""
    
        # start reading the data stream looking for the first header byte
        while self._readByte() != 0xff:
            print "."
            continue
        # expect the next header byte
        if self._readByte() == 0xff:
            return
        else:
            self.getStart()
            
    def decode(self):
        """ decode the packet """
        deviceCode = self._readByte()
        self.handlers[deviceCode](deviceCode)
        
    def _cksum(self, code, frame):
        """ calculate checksum """
        sum = code
        for f in frame:
            sum =+ f
        csum = sum & 0xff
        return csum == frame[-1]
    
    def _decodeBCD(self, bcd):
        """ decode binary coded decimal"""
        r = (bcd & 0xf)
        r += ((bcd & 0xf0) >> 4) * 10
        return(r);
        
    def _testBattery(self, test, device):
        """ low battery indicator for device"""
        if test: print Device + " battery low"
        
    def _printMeasurements(self, vals):
        for v in vals:
            print str(v) + " ",
        print
        
    def log(self):
        print "hohoh"
        
def main():
    """ gather data"""
    dec = Decoder()
    while True:
        dec.getStart()
        dec.decode()


            
             

if __name__ == "__main__":
    main()
