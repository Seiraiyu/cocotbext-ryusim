import shutil
import subprocess
from pathlib import Path

from cocotb_tools.check_results import get_results

DUT = Path(__file__).parent / "dut"

MAKEFILE = """\
TOPLEVEL_LANG = verilog
VERILOG_SOURCES = $(CURDIR)/dut.sv
COCOTB_TOPLEVEL = dut
COCOTB_TEST_MODULES = dut_tests
include $(shell cocotbext-ryusim-config --makefiles)/Makefile.sim
"""


def _make(tmp_path: Path, sim: str) -> tuple[int, int]:
    work = tmp_path / sim
    shutil.copytree(DUT, work)
    (work / "Makefile").write_text(MAKEFILE)
    proc = subprocess.run(
        ["make", f"SIM={sim}"], cwd=work, capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stdout[-4000:] + proc.stderr[-4000:]
    return get_results(work / "results.xml")


def test_ryusim(tmp_path):
    assert _make(tmp_path, "ryusim") == (3, 0)


def test_other_sims_forwarded_to_cocotb(tmp_path):
    # The same user Makefile must keep working for every other simulator.
    assert _make(tmp_path, "icarus") == (3, 0)
