import random

import cocotb
from cocotb.binary import BinaryValue
from cocotb.decorators import coroutine
from cocotb.result import TestFailure
from cocotb.triggers import Timer, RisingEdge


def cocotbXHack():
    if hasattr(BinaryValue,"_resolve_to_0"):
        # cocotb <= 1.4.0
        BinaryValue._resolve_to_0     = BinaryValue._resolve_to_0  + BinaryValue._resolve_to_error
        BinaryValue._resolve_to_error = ""
    elif hasattr(cocotb.binary, "resolve_x_to"):
        # cocotb 1.5.0+
        cocotb.binary.resolve_x_to = "ZEROS"
        cocotb.binary._resolve_table = cocotb.binary._ResolveTable()

def log2Up(value):
    return value.bit_length()-1

def randInt(min,max):
    return random.randint(min, max)

def randBool():
    return bool(random.getrandbits(1))

def randBits(width):
    return random.getrandbits(width)

def randSignal(that):
    that <= random.getrandbits(len(that))

def randBoolSignal(that,prob):
    that <= (random.random() < prob)


@coroutine
def clockedWaitTrue(clk,that):
    while True:
        yield RisingEdge(clk)
        if that == True:
            break

def assertEquals(a, b, name):
    if int(a) != int(b):
        raise TestFailure("FAIL %s    %d != %d" % (name,int(a),int(b)))

def truncUInt(value, signal):
    if isinstance( signal, int ):
        return value & ((1 << signal)-1)
    else:
        return value & ((1 << len(signal)) - 1)

def truncSInt(value, signal):
    if isinstance( signal, int ):
        bitCount = signal
    else:
        bitCount = len(signal)
    masked = value & ((1 << bitCount)-1)
    if (masked & (1 << bitCount-1)) != 0:
        return - (1 << bitCount) + masked
    else:
        return masked


def setBit(v, index, x):
  mask = 1 << index
  v &= ~mask
  if x:
    v |= mask
  return v

def testBit(int_type, offset):
   mask = 1 << offset
   return (int_type & mask) != 0

def uint(signal):
    return signal.value.integer

def sint(signal):
    return signal.value.signed_integer


@cocotb.coroutine
def ClockDomainAsyncReset(clk,reset,period = 1000):
    if reset:
        reset <= 1
    clk <= 0
    yield Timer(period)
    if reset:
        reset <= 0
    while True:
        clk <= 0
        yield Timer(period/2)
        clk <= 1
        yield Timer(period/2)

@cocotb.coroutine
def SimulationTimeout(duration):
    yield Timer(duration)
    raise TestFailure("Simulation timeout")


import time
@cocotb.coroutine
def simulationSpeedPrinter(clk):
    counter = 0
    lastTime = time.time()
    while True:
        yield RisingEdge(clk)
        counter += 1
        thisTime = time.time()
        if thisTime - lastTime >= 1.0:
            lastTime = thisTime
            print("Sim speed : %f khz" %(counter/1000.0))
            counter = 0



class BoolRandomizer:
    def __init__(self):
        self.prob = 0.5
        self.counter = 0
        self.probLow = 0.1
        self.probHigh = 0.9

    def get(self):
        self.counter += 1
        if self.counter == 100:
            self.counter = 0
            self.prob = random.uniform(self.probLow, self.probHigh)
        return random.random() < self.prob



# class Stream:
#     def __init__(self,name,dut):
#         self.valid = getattr(dut, name + "_valid")
#         self.ready = getattr(dut, name + "_ready")
#         payloads = [a for a in dut if a._name.startswith(name + "_payload")]
#         if len(payloads) == 1 and payloads[0]._name == name + "_payload":
#             self.payload = payloads[0]



MyObject = type('MyObject', (object,), {})

@cocotb.coroutine
def StreamRandomizer(streamName, onNew,handle, dut, clk):
    validRandomizer = BoolRandomizer()
    valid = getattr(dut, streamName + "_valid")
    ready = getattr(dut, streamName + "_ready")
    payloads = [a for a in dut if a._name.startswith(streamName + "_payload")]

    valid <= 0
    while True:
        yield RisingEdge(clk)
        if int(ready) == 1:
            valid <= 0

        if int(valid) == 0 or int(ready) == 1:
            if validRandomizer.get():
                valid <= 1
                for e in payloads:
                    randSignal(e)
                yield Timer(1)
                if len(payloads) == 1 and payloads[0]._name == streamName + "_payload":
                    payload = int(payloads[0])
                else:
                    payload = MyObject()
                    for e in payloads:
                        payload.__setattr__(e._name[len(streamName + "_payload_"):], int(e))
                if onNew:
                    onNew(payload,handle)

@cocotb.coroutine
def FlowRandomizer(streamName, onNew,handle, dut, clk):
    validRandomizer = BoolRandomizer()
    valid = getattr(dut, streamName + "_valid")
    payloads = [a for a in dut if a._name.startswith(streamName + "_payload")]

    valid <= 0
    while True:
        yield RisingEdge(clk)
        if validRandomizer.get():
            valid <= 1
            for e in payloads:
                randSignal(e)
            yield Timer(1)
            if len(payloads) == 1 and payloads[0]._name == streamName + "_payload":
                payload = int(payloads[0])
            else:
                payload = MyObject()
                for e in payloads:
                    payload.__setattr__(e._name[len(streamName + "_payload_"):], int(e))
            if onNew:
                onNew(payload,handle)
        else:
            valid <= 0

@cocotb.coroutine
def StreamReader(streamName, onTransaction, handle, dut, clk):
    validRandomizer = BoolRandomizer()
    valid = getattr(dut, streamName + "_valid")
    ready = getattr(dut, streamName + "_ready")
    payloads = [a for a in dut if a._name.startswith(streamName + "_payload")]

    ready <= 0
    while True:
        yield RisingEdge(clk)
        ready <= validRandomizer.get()
        if int(valid) == 1 and int(ready) == 1:
            if len(payloads) == 1 and payloads[0]._name == streamName + "_payload":
                payload = int(payloads[0])
            else:
                payload = MyObject()
                for e in payloads:
                    payload.__setattr__(e._name[len(streamName + "_payload_"):], int(e))

            if onTransaction:
                onTransaction(payload,handle)



class Bundle:
    def __init__(self,dut,name):
        self.nameToElement = {}
        self.elements = [a for a in dut if (a._name.lower().startswith(name.lower() + "_") and not a._name.lower().endswith("_readablebuffer"))]

        for e in [a for a in dut if a._name == name]:
            self.elements.append(e)

        for element in self.elements:
            # print("append " + element._name + " with name : " + element._name[len(name) + 1:])
            if len(name) == len(element._name):
                eName = "itself"
            else:
                eName = element._name[len(name) + 1:]

            if eName == "id":
                eName = "hid"
            self.nameToElement[eName] = element

    def __getattr__(self, name):
        if name not in self.nameToElement:
            for e in self.nameToElement:
                print(e)
        return self.nameToElement[name]



def readIHex(path, callback,context):
    with open(path) as f:
        offset = 0
        for line in f:
            if len(line) > 0:
                assert line[0] == ':'
                byteCount = int(line[1:3], 16)
                nextAddr = int(line[3:7], 16) + offset
                key = int(line[7:9], 16)
                if key == 0:
                    array = [int(line[9 + i * 2:11 + i * 2], 16) for i in range(0, byteCount)]
                    callback(nextAddr,array,context)
                elif key == 2:
                    offset = int(line[9:13], 16)
                else:
                    pass



@coroutine
def TriggerAndCond(trigger, cond):
    while(True):
        yield trigger
        if cond:
            break


@coroutine
def waitClockedCond(clk, cond):
    while(True):
        yield RisingEdge(clk)
        if cond():
            break



@coroutine
def TimerClk(clk, count):
    for i in range(count):
        yield RisingEdge(clk)