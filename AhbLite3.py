import random

import cocotb
from cocotb.result import TestFailure
from cocotb.triggers import RisingEdge, Edge

from cocotblib.misc import log2Up, BoolRandomizer, assertEquals


def AhbLite3MasterIdle(ahb):
    ahb.HADDR <= 0
    ahb.HWRITE <= 0
    ahb.HSIZE <= 0
    ahb.HBURST <= 0
    ahb.HPROT <= 0
    ahb.HTRANS <= 0
    ahb.HMASTLOCK <= 0
    ahb.HWDATA <= 0



class AhbLite3Transaction:
    def __init__(self):
        self.HADDR     = 0
        self.HWRITE    = 0
        self.HSIZE     = 0
        self.HBURST    = 0
        self.HPROT     = 0
        self.HTRANS    = 0
        self.HMASTLOCK = 0
        self.HWDATA    = 0

class AhbLite3TraficGenerator:
    def __init__(self,addressWidth,dataWidth):
        self.addressWidth = addressWidth
        self.dataWidth = dataWidth
    def genRandomAddress(self):
        return random.randint(0,(1 << self.addressWidth)-1)

    def getTransactions(self):
        if random.random() < 0.8:
            trans = AhbLite3Transaction()
            return [trans]
        else:
            OneKiB = 1 << 10 # this pesky 1 KiB wall a burst must not cross
            hSize = random.randint(0,log2Up(self.dataWidth//8))
            bytesPerBeat = 1 << hSize
            maxBurst = 5 if hSize == 7 else 7 # a full-width 1024 bit bus can only burst up to 8 beats for not crossing a 1 KiB boundary
            burst = random.randint(0,maxBurst)
            write = random.random() < 0.5
            prot = random.randint(0,15)
            address = self.genRandomAddress() & ~(bytesPerBeat-1)

            incrUnspecified = burst == 1
            incrFixed = burst != 1 and burst & 1 == 1
            wrapFixed = burst & 1 == 0

            if incrUnspecified:
                maxBeats = (OneKiB - (address % OneKiB)) // bytesPerBeat
                burstBeats = random.randint(1,maxBeats)
            else:
                burstCase = burst >> 1
                burstBeats = [1,4,8,16][burstCase]

            burstBytes = bytesPerBeat*burstBeats

            while incrFixed and ((address % OneKiB) + burstBytes) > OneKiB:
                address = address - bytesPerBeat

            addressBase = address - address % burstBytes # for wrapFixed bursts

            buffer = []
            for beat in range(burstBeats):
                if beat > 0:
                    busyProp = random.random() - 0.8
                    for busyBeat in range(int(busyProp/0.05)):
                        trans = AhbLite3Transaction()
                        trans.HWRITE = write
                        trans.HSIZE = hSize
                        trans.HBURST = burst
                        trans.HPROT = prot
                        trans.HADDR = address
                        trans.HTRANS = 1 # BUSY
                        trans.HWDATA = random.randint(0,(1 << self.dataWidth)-1)
                        buffer.append(trans)
                trans = AhbLite3Transaction()
                trans.HWRITE = write
                trans.HSIZE = hSize
                trans.HBURST = burst
                trans.HPROT = prot
                trans.HADDR = address
                trans.HTRANS = 2 if beat == 0 else 3 # first beat is NONSEQ, others are SEQ
                trans.HWDATA = random.randint(0,(1 << self.dataWidth)-1)
                address += bytesPerBeat
                if wrapFixed and (address == addressBase + burstBytes):
                    address = addressBase
                buffer.append(trans)
            return buffer

class AhbLite3MasterDriver:
    def __init__(self,ahb,transactor,clk,reset):
        self.ahb = ahb
        self.clk = clk
        self.reset = reset
        self.transactor = transactor
        cocotb.fork(self.stim())

    @cocotb.coroutine
    def stim(self):
        ahb = self.ahb
        ahb.HADDR     <= 0
        ahb.HWRITE    <= 0
        ahb.HSIZE     <= 0
        ahb.HBURST    <= 0
        ahb.HPROT     <= 0
        ahb.HTRANS    <= 0
        ahb.HMASTLOCK <= 0
        ahb.HWDATA    <= 0
        HWDATAbuffer = 0
        while True:
            for trans in self.transactor.getTransactions():
                yield RisingEdge(self.clk)
                while int(self.ahb.HREADY) == 0:
                    yield RisingEdge(self.clk)

                ahb.HADDR <= trans.HADDR
                ahb.HWRITE <= trans.HWRITE
                ahb.HSIZE <= trans.HSIZE
                ahb.HBURST <= trans.HBURST
                ahb.HPROT <= trans.HPROT
                ahb.HTRANS <= trans.HTRANS
                ahb.HMASTLOCK <= trans.HMASTLOCK
                ahb.HWDATA <= HWDATAbuffer
                HWDATAbuffer = trans.HWDATA

class AhbLite3Terminaison:
    def __init__(self,ahb,clk,reset):
        self.ahb = ahb
        self.clk = clk
        self.reset = reset
        self.randomHREADY = True
        cocotb.fork(self.stim())
        cocotb.fork(self.combEvent())

    @cocotb.coroutine
    def stim(self):
        randomizer = BoolRandomizer()
        self.ahb.HREADY <= 1
        self.ahb.HSEL <= 1
        while True:
            yield RisingEdge(self.clk)
            self.randomHREADY = randomizer.get()
            self.doComb()

    @cocotb.coroutine
    def combEvent(self):
        while True:
            yield Edge(self.ahb.HREADYOUT)
            self.doComb()

    def doComb(self):
        self.ahb.HREADY <= (self.randomHREADY and (int(self.ahb.HREADYOUT) == 1))


class AhbLite3MasterReadChecker:
    def __init__(self,ahb,buffer,clk,reset):
        self.ahb = ahb
        self.clk = clk
        self.reset = reset
        self.buffer = buffer
        self.counter = 0
        cocotb.fork(self.stim())

    @cocotb.coroutine
    def stim(self):
        ahb = self.ahb
        readIncoming = False
        while True:
            yield RisingEdge(self.clk)
            if int(self.ahb.HREADY) == 1:
                if readIncoming:
                    if self.buffer.empty():
                        raise TestFailure("Empty buffer ??? ")

                    bufferData = self.buffer.get()
                    for i in range(byteOffset,byteOffset + size):
                        assertEquals((int(ahb.HRDATA) >> (i*8)) & 0xFF,(bufferData >> (i*8)) & 0xFF,"AHB master read checker faild %x "  %(int(ahb.HADDR)) )

                    self.counter += 1
                    # cocotb.log.info("POP " + str(self.buffer.qsize()))

                readIncoming = int(ahb.HTRANS) >= 2 and int(ahb.HWRITE) == 0
                size = 1 << int(ahb.HSIZE)
                byteOffset = int(ahb.HADDR) % (len(ahb.HWDATA) // 8)



class AhbLite3SlaveMemory:
    def __init__(self,ahb,base,size,clk,reset):
        self.ahb = ahb
        self.clk = clk
        self.reset = reset
        self.base = base
        self.size = size
        self.ram = bytearray(b'\x00' * size)

        cocotb.fork(self.stim())
        cocotb.fork(self.stimReady())

    @cocotb.coroutine
    def stimReady(self):
        randomizer = BoolRandomizer()
        self.ahb.HREADYOUT <= 1
        busy = False
        while True:
            yield RisingEdge(self.clk)
            if int(self.ahb.HREADY) == 1:
                busyNew = int(self.ahb.HTRANS) >= 2
            else:
                busyNew = busy
            if (busy or busyNew) and int(self.ahb.HREADYOUT) == 0 and int(self.ahb.HREADY) == 1:
                raise TestFailure("HREADYOUT == 0 but HREADY == 1 ??? " + self.ahb.HREADY._name)
            busy = busyNew
            if (busy):
                self.ahb.HREADYOUT <= randomizer.get() # make some random delay for NONSEQ and SEQ requests
            else:
                self.ahb.HREADYOUT <= 1 # IDLE and BUSY require 0 WS

    @cocotb.coroutine
    def stim(self):
        ahb = self.ahb
        ahb.HREADYOUT <= 1
        ahb.HRESP     <= 0
        ahb.HRDATA    <= 0
        valid = 0
        while True:
            yield RisingEdge(self.clk)
            while int(self.ahb.HREADY) == 0:
                yield RisingEdge(self.clk)

            if valid == 1:
                if trans >= 2:
                    if write == 1:
                        for idx in range(size):
                            self.ram[address-self.base  + idx] = (int(ahb.HWDATA) >> (8*(addressOffset + idx))) & 0xFF
                            # print("write %x with %x" % (address + idx,(int(ahb.HWDATA) >> (8*(addressOffset + idx))) & 0xFF))

            valid = int(ahb.HSEL)
            trans = int(ahb.HTRANS)
            write = int(ahb.HWRITE)
            size = 1 << int(ahb.HSIZE)
            address = int(ahb.HADDR)
            addressOffset = address % (len(ahb.HWDATA)//8)

            ahb.HRDATA <= 0
            if valid == 1:
                if trans >= 2:
                    if write == 0:
                        data = 0
                        for idx in range(size):
                            data |= self.ram[address-self.base + idx] << (8*(addressOffset + idx))
                            # print("read %x with %x" % (address + idx, self.ram[address-self.base + idx]))
                        # print(str(data))
                        ahb.HRDATA <= int(data)
