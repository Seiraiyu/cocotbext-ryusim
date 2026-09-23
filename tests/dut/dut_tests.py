import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, ReadOnly, RisingEdge, Timer
from cocotb.utils import get_sim_time


@cocotb.test()
async def counts(dut):
    """VPI read of a clocked register."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await ClockCycles(dut.clk, 5)
    await ReadOnly()
    assert int(dut.count.value) >= 4


@cocotb.test()
async def write_read(dut):
    """VPI write, then read back through combinational logic."""
    dut.data_in.value = 0xA5
    await Timer(1, unit="ns")
    assert int(dut.data_out.value) == 0xA5


@cocotb.test()
async def delay_honors_timescale(dut):
    """`always #5` must give a 10 ns period. A missing timescale gives 10 ps."""
    await RisingEdge(dut.tick)
    start = get_sim_time("ns")
    await RisingEdge(dut.tick)
    assert get_sim_time("ns") - start == 10
