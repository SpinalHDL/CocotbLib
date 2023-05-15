import cocotb
from cocotb.triggers import RisingEdge, Event
from cocotb.decorators import coroutine

from .misc import Bundle


###############################################################################
# Flow
#
class Flow:

    #==========================================================================
    # Constructor
    #==========================================================================
    def __init__(self, dut, name):

        # interface
        self.valid = dut.__getattr__(name + "_valid")
        self.payload = Bundle(dut,name + "_payload")

        # Event
        self.event_valid = Event()


    #==========================================================================
    # Start to monitor the valid signal
    #==========================================================================
    def startMonitoringValid(self, clk):
        self.clk  = clk
        self.fork_valid = cocotb.start_soon(self.monitor_valid())


    #==========================================================================
    # Stop monitoring
    #==========================================================================
    def stopMonitoring(self):
        self.fork_valid.kill()


    #==========================================================================
    # Monitor the valid signal
    #==========================================================================
    @coroutine
    def monitor_valid(self):
        while True:
            yield RisingEdge(self.clk)
            if int(self.valid) == 1:
                self.event_valid.set( self.payload )
