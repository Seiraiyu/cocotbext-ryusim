from pathlib import Path

import cocotb
import pytest
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, ReadOnly
from cocotb_tools._pytest.hdl import HDL

HERE = Path(__file__).parent


@pytest.fixture(name="dut_design")
def dut_design_fixture(hdl: HDL) -> HDL:
    hdl.toplevel = "dut"
    hdl.sources = (HERE / "dut.sv",)
    hdl.build()
    return hdl


@pytest.mark.cocotb_runner
@pytest.mark.cocotb_timescale(unit="1ns", precision="1ps")
def test_dut(dut_design: HDL) -> None:
    dut_design.test()


@cocotb.test()
async def counts(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await ClockCycles(dut.clk, 5)
    await ReadOnly()
    assert int(dut.count.value) >= 4
