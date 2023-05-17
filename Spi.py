import random

import cocotb
from cocotb.result import TestFailure, ReturnValue
from cocotb.triggers import RisingEdge, Edge, Timer
from cocotb.decorators import coroutine

from .TriState import TriStateOutput
from .misc import log2Up, BoolRandomizer, assertEquals, testBit


class SpiMaster:
    def __init__(self, dut, name):
        self.sclk = dut.__getattr__(name + "_sclk")
        self.mosi = dut.__getattr__(name + "_mosi")
        self.miso = dut.__getattr__(name + "_miso")
        self.ss = dut.__getattr__(name + "_ss")


class SpiSlave:
    def __init__(self, dut, name):
        self.sclk = dut.__getattr__(name + "_sclk")
        self.mosi = dut.__getattr__(name + "_mosi")
        self.miso = TriStateOutput(dut, name + "_miso")
        self.ss = dut.__getattr__(name + "_ss")


class SpiSlaveMaster:
    def __init__(self, spi):
        self.spi = spi
        self.cpol = False
        self.cpha = False
        self.baudPeriode = 1000
        self.dataWidth = 8

    def init(self, cpol, cpha, baudrate, dataWidth=8):
        self.spi.ss.value = True
        self.cpol = cpol
        self.cpha = cpha
        self.baudPeriode = baudrate
        self.dataWidth = dataWidth
        self.spi.sclk.value = cpol

    @coroutine
    def enable(self):
        self.spi.ss.value = False
        yield Timer(self.baudPeriode)

    @coroutine
    def disable(self):
        yield Timer(self.baudPeriode)
        self.spi.ss.value = True
        yield Timer(self.baudPeriode)

    @coroutine
    def exchange(self, masterData):
        buffer = ""
        if not self.cpha:
            for i in range(self.dataWidth):
                self.spi.mosi.value = testBit(masterData, self.dataWidth - 1 - i)
                yield Timer(self.baudPeriode >> 1)
                buffer = buffer + str(self.spi.miso.write) if bool(self.spi.miso.writeEnable) else "x"
                self.spi.sclk.value = (not self.cpol)
                yield Timer(self.baudPeriode >> 1)
                self.spi.sclk.value = (self.cpol)
        else:
            for i in range(self.dataWidth):
                self.spi.mosi.value = testBit(masterData, self.dataWidth - 1 - i)
                self.spi.sclk.value = (not self.cpol)
                yield Timer(self.baudPeriode >> 1)
                buffer = buffer + str(self.spi.miso.write) if bool(self.spi.miso.writeEnable) else "x"
                self.spi.sclk.value = (self.cpol)
                yield Timer(self.baudPeriode >> 1)

        raise ReturnValue(buffer)

    @coroutine
    def exchangeCheck(self, masterData, slaveData):
        c = self.exchange(masterData)
        yield c
        assert slaveData == int(c.retval, 2)
