import shutil
from pathlib import Path

from cocotb_tools.check_results import get_results
from cocotb_tools.runner import get_runner

import cocotbext.ryusim

DUT = Path(__file__).parent / "dut"


def test_get_runner_returns_ryusim():
    assert isinstance(get_runner("ryusim"), cocotbext.ryusim.RyuSim)


def test_build_and_test(tmp_path):
    work = tmp_path / "dut"
    shutil.copytree(DUT, work)
    runner = get_runner("ryusim")
    runner.build(
        sources=[work / "dut.sv"],
        hdl_toplevel="dut",
        build_dir=tmp_path / "build",
        timescale=("1ns", "1ps"),
        always=True,
    )
    results = runner.test(
        hdl_toplevel="dut",
        test_module="dut_tests",
        test_dir=work,
        build_dir=tmp_path / "build",
    )
    assert get_results(results) == (3, 0)
