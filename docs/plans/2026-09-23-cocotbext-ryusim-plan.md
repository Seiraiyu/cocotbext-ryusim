# cocotbext-ryusim Implementation Plan

**Goal:** Publish `cocotbext-ryusim` 0.1.0 to PyPI: a pure-Python package that adds `SIM=ryusim` to cocotb's Makefile, Runner and pytest flows on released cocotb 2.1, with CI running cocotb's full Verilog regression through it.

**Architecture:** The package supplies RyuSim build and run commands and adds `ryusim` to cocotb's internal registries. It never modifies cocotb's installed files, and it loads cocotb's stock `libcocotbvpi_verilator.so`, because RyuSim's VPI callback behavior matches Verilator's. Makefile users include a drop-in `Makefile.sim` that handles `SIM=ryusim` itself and passes every other `SIM` to cocotb.

**Tech Stack:** Python ≥3.9, cocotb 2.1.x, hatchling, pytest ≥8, GNU make, GitHub Actions, PyPI trusted publishing.

**Design:** [`2026-09-23-cocotbext-ryusim-design.md`](2026-09-23-cocotbext-ryusim-design.md) (approved). Section numbers (§) refer to it.

| Task | Description | Status | Tested | Pushed |
|------|-------------|--------|--------|--------|
| 1 | Dev environment: clean venv with cocotb 2.1.0, RyuSim, Icarus | done | yes | yes |
| 2 | Packaging scaffold | done | yes | yes |
| 3 | Smoke-test DUT and testbenches | done | yes | yes |
| 4 | `cocotbext-ryusim-config` CLI | done | yes | yes |
| 5 | Makefile flow: shim + `Makefile.ryusim` | done | yes | yes |
| 6 | Runner flow: `RyuSim(Runner)` + registration | done | yes | yes |
| 7 | pytest flow: plugin + load-order fix | done | yes | yes |
| 8 | CI workflow + local conformance run | done | yes | yes |
| 9 | README | done | yes | yes |
| 10 | Release workflow | done | yes | yes |
| 11 | Create GitHub repo, push, CI green (**ask the user first**) | done | yes | yes |
| 12 | Configure trusted publishing (**done by the user**) | pending | no | no |
| 13 | Tag v0.1.0, verify install from PyPI (**ask the user first**) | pending | no | no |

After each phase completes, also update the phase table in the design doc (§10).

---

## Read this first

- **Repo:** `~/cocotbext-ryusim`. It already has one commit (`099b018`, the design doc). Run every command from the repo root unless a step says otherwise.
- **Never use the system `cocotb`.** `~/.local/lib/python3.12/site-packages/cocotb` is the old Seiraiyu fork (`2.1.dev162+r609b4304`). It ships `libcocotbvpi_ryusim.so`, so any test run against it would pass for the wrong reason. Always activate `.venv` first, and Task 1 checks the version.
- **Source of ported code:** the fork branch `feat/ryusim-simulator-support` at commit `560b5227`, which is in `~/cocotb`. It is also on GitHub (`Seiraiyu/cocotb`).
- **Verified during planning:** every file in this plan except `Makefile.ryusim` execution and the RyuSim runs has been executed against PyPI `cocotb==2.1.0`. Specifically:
  - the shim forwards `SIM=icarus` to cocotb and passes, and routes `SIM=ryusim` into `Makefile.ryusim`;
  - the pytest plugin fix is accepted in both load orders, on pytest 8.4.2 and 9.1.1;
  - the Runner registers and resolves to `libcocotbvpi_verilator.so`;
  - the smoke DUT passes 3/3 on Icarus, and its timescale test fails when the unit is forced to 1 ps.
- **Commits** end with:
  ```
  Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01GvLuF9LuWe3VZrSgdjS1iX
  ```
  The `git commit -m` lines below show the subject only. Add these two trailers to each commit.

---

## Phase 1: Scaffold and Makefile flow

### Task 1: Dev environment

**Files:** none

**Step 1: Create the venv with released cocotb**

```bash
cd ~/cocotbext-ryusim
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install "cocotb==2.1.0" "pytest>=8"
```

**Step 2: Verify it's the real release, not the fork**

Run: `python -c "import cocotb, cocotb_tools.config as c; print(cocotb.__version__); print(c.lib_name_path('vpi','verilator'))"`
Expected: `2.1.0` on the first line, and a path ending in `.venv/lib/python3.X/site-packages/cocotb/libs/libcocotbvpi_verilator.so`. If it prints `2.1.dev…`, you are on the fork, so stop and fix the venv.

Run: `ls .venv/lib/python3*/site-packages/cocotb/libs/ | grep -c ryusim`
Expected: `0`

**Step 3: Install RyuSim**

```bash
curl -fsSL https://ryusim.seiraiyu.com/install.sh | bash
export PATH="$HOME/.ryusim/bin:$PATH"
```

The installer writes to `~/.ryusim` and does not need root. Its prerequisites, Clang ≥18 and CMake, are already present on this machine (`clang 18.1.3`).

Run: `ryusim --version`
Expected: a version of at least `2.1.16`. Versions older than 2.1.16 fail the coincident-trigger and packed-array cases in the conformance run.

**Step 4: Check Icarus is present**

Run: `iverilog -V 2>&1 | head -1`
Expected: `Icarus Verilog version …`. It is used to test the shim's handling of non-RyuSim `SIM` values. Install with `sudo apt-get install iverilog` if it's missing.

Nothing to commit. Keep `.venv` activated and `~/.ryusim/bin` on `PATH` for every later task.

---

### Task 2: Packaging scaffold

**Files:**
- Create: `.gitignore`
- Create: `LICENSE`
- Create: `pyproject.toml`
- Create: `README.md` (a placeholder; Task 9 writes the full one)
- Create: `src/cocotbext/ryusim/__init__.py`

**Step 1: Write the files**

`.gitignore`:
```gitignore
.venv/
__pycache__/
*.egg-info/
dist/
build/
sim_build/
results.xml
*.vcd
.pytest_cache/
```

`LICENSE`:
```text
Copyright cocotb contributors
Copyright (c) 2013 Potential Ventures Ltd
Copyright (c) 2013 SolarFlare Communications Inc
Copyright (c) 2026 Seiraiyu
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

`pyproject.toml`. The `pytest11` entry point is **deliberately absent** here and is added in Task 7. pytest loads every installed `pytest11` entry point on every run, so declaring one before its module exists would break this package's own test runs in Tasks 4–6.
```toml
[build-system]
requires = ["hatchling>=1.27"]
build-backend = "hatchling.build"

[project]
name = "cocotbext-ryusim"
version = "0.1.0"
description = "RyuSim simulator support for cocotb"
readme = "README.md"
requires-python = ">=3.9"
license = "BSD-3-Clause"
license-files = ["LICENSE"]
authors = [{ name = "Seiraiyu" }]
dependencies = ["cocotb>=2.1,<2.2"]
classifiers = [
    "Framework :: cocotb",
    "Operating System :: POSIX :: Linux",
    "Programming Language :: Python :: 3",
    "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
]

[project.optional-dependencies]
test = ["pytest>=8"]

[project.urls]
Homepage = "https://github.com/Seiraiyu/cocotbext-ryusim"
Issues = "https://github.com/Seiraiyu/cocotbext-ryusim/issues"

[project.scripts]
cocotbext-ryusim-config = "cocotbext.ryusim.config:main"

[tool.hatch.build.targets.wheel]
packages = ["src/cocotbext"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`README.md`:
```markdown
# cocotbext-ryusim

RyuSim simulator support for cocotb. Documentation follows.
```

`src/cocotbext/ryusim/__init__.py` (Task 6 replaces this):
```python
"""RyuSim simulator support for cocotb."""
```

Do **not** create `src/cocotbext/__init__.py`. `cocotbext` is a namespace package that other extensions such as `cocotbext-axi` share, and an `__init__.py` would hide them.

**Step 2: Install editable and verify**

Run: `pip install -e ".[test]" && python -c "import cocotbext.ryusim; print(cocotbext.ryusim.__doc__)"`
Expected: `RyuSim simulator support for cocotb.`

**Step 3: Verify the wheel layout**

Run: `pip install build && python -m build --wheel && python -m zipfile -l dist/*.whl | awk '{print $1}' | grep cocotbext`
Expected: `cocotbext/ryusim/__init__.py` is listed, and there is **no** `cocotbext/__init__.py`.

Run: `rm -rf dist`

**Step 4: Commit**

```bash
git add .gitignore LICENSE pyproject.toml README.md src/
git commit -m "build: package scaffold"
```

---

### Task 3: Smoke-test DUT and testbenches

These are shared test data. Their filenames deliberately don't match pytest's `test_*.py` / `*_test.py` patterns, so this package's own pytest run never collects them.

**Files:**
- Create: `tests/dut/dut.sv`
- Create: `tests/dut/dut_tests.py` (cocotb tests, used by the Makefile and Runner flows)
- Create: `tests/dut/pt_case.py` (a pytest-flow case, copied to `test_pt_dut.py` at run time)

**Step 1: Write the files**

`tests/dut/dut.sv`:
```systemverilog
// Smoke-test DUT. Deliberately has NO `timescale directive: the unit must
// come from COCOTB_HDL_TIMEUNIT on the compile line, which is what the
// RyuSim timescale fix provides.
module dut (
    input  logic       clk,
    input  logic [7:0] data_in,
    output logic [7:0] data_out,
    output logic [7:0] count,
    output logic       tick
);
  assign data_out = data_in;

  initial begin
    count = 0;
    tick = 0;
  end

  // Free-running: period is 10 time units, i.e. 10 ns at the default 1ns unit.
  always #5 tick = ~tick;

  always @(posedge clk) count <= count + 1;
endmodule
```

`tests/dut/dut_tests.py`:
```python
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
```

`tests/dut/pt_case.py`. It imports from `cocotb_tools._pytest.hdl`: in cocotb 2.1.0 the module is `_pytest`, **not** the `cocotb_tools.pytest` that cocotb's documentation shows.
```python
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
```

**Step 2: Sanity-check the DUT on Icarus through stock cocotb**

This proves the test data is correct before any package code exists.

```bash
W=$(mktemp -d) && cp tests/dut/dut.sv tests/dut/dut_tests.py "$W"/
cat > "$W/Makefile" <<'EOF'
TOPLEVEL_LANG = verilog
VERILOG_SOURCES = $(CURDIR)/dut.sv
COCOTB_TOPLEVEL = dut
COCOTB_TEST_MODULES = dut_tests
include $(shell cocotb-config --makefiles)/Makefile.sim
EOF
make -C "$W" SIM=icarus 2>&1 | grep "TESTS="
```
Expected: `** TESTS=3 PASS=3 FAIL=0 SKIP=0 …`

Negative control. This proves the timescale test can actually fail:

Run: `rm -rf "$W"/sim_build "$W"/results.xml && make -C "$W" SIM=icarus COCOTB_HDL_TIMEUNIT=1ps 2>&1 | grep "TESTS="`
Expected: `** TESTS=3 PASS=2 FAIL=1 SKIP=0 …`, with the failure in `delay_honors_timescale`.

**Step 3: Confirm pytest won't collect the data files**

Run: `pytest --co -q 2>&1 | tail -1`
Expected: `no tests collected …`

**Step 4: Commit**

```bash
git add tests/dut
git commit -m "test: smoke-test DUT and testbenches"
```

---

### Task 4: `cocotbext-ryusim-config` CLI

**Files:**
- Create: `src/cocotbext/ryusim/config.py`
- Test: `tests/test_config.py`

**Step 1: Write the failing test**

`tests/test_config.py`:
```python
import subprocess
from pathlib import Path

import cocotbext.ryusim


def _config(*args: str) -> str:
    return subprocess.run(
        ["cocotbext-ryusim-config", *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def test_makefiles_is_package_makefiles_dir():
    package_dir = Path(cocotbext.ryusim.__file__).parent
    assert Path(_config("--makefiles")) == package_dir / "makefiles"


def test_version():
    assert _config("--version") == "0.1.0"
```

**Step 2: Run the test, verify failure**

Run: `pytest tests/test_config.py -q`
Expected: 2 failures, each a `subprocess.CalledProcessError … returned non-zero exit status 1`. The console script was registered in Task 2 but its module doesn't exist yet. Running `cocotbext-ryusim-config --version` by hand shows the underlying `ModuleNotFoundError: No module named 'cocotbext.ryusim.config'`.

**Step 3: Implement**

`src/cocotbext/ryusim/config.py`:
```python
"""``cocotbext-ryusim-config``: locate this package's makefiles."""

from __future__ import annotations

import argparse
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path


def makefiles_dir() -> Path:
    return Path(str(files("cocotbext.ryusim") / "makefiles"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cocotbext-ryusim-config")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--makefiles",
        action="store_true",
        help="print the directory containing Makefile.sim",
    )
    group.add_argument("--version", action="store_true", help="print the version")
    args = parser.parse_args(argv)
    print(makefiles_dir() if args.makefiles else version("cocotbext-ryusim"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Step 4: Run the test, verify pass**

Run: `pytest tests/test_config.py -q`
Expected: `2 passed`

**Step 5: Commit**

```bash
git add src/cocotbext/ryusim/config.py tests/test_config.py
git commit -m "feat: cocotbext-ryusim-config CLI"
```

---

### Task 5: Makefile flow

**Files:**
- Create: `src/cocotbext/ryusim/makefiles/Makefile.sim`
- Create: `src/cocotbext/ryusim/makefiles/simulators/Makefile.ryusim` (ported from the fork)
- Test: `tests/test_make_flow.py`

**Step 1: Write the failing test**

`tests/test_make_flow.py`. It uses `$(CURDIR)`, not `$(PWD)`: `PWD` is inherited from the parent process and is **not** updated by `subprocess.run(cwd=…)`, so `$(PWD)` would point at the wrong directory.
```python
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
```

These tests have no `skipif`. If RyuSim or Icarus is missing they fail loudly rather than passing silently, which is intended.

**Step 2: Run the test, verify failure**

Run: `pytest tests/test_make_flow.py -q`
Expected: 2 failures. The output contains `No such file or directory` for `…/makefiles/Makefile.sim`.

**Step 3: Implement the shim**

`src/cocotbext/ryusim/makefiles/Makefile.sim`:
```make
# Copyright (c) 2026 Seiraiyu
# SPDX-License-Identifier: BSD-3-Clause
#
# Drop-in replacement for cocotb's Makefile.sim that adds SIM=ryusim.
# Every other SIM is handed to cocotb's own Makefile.sim unchanged.
#
#   include $(shell cocotbext-ryusim-config --makefiles)/Makefile.sim

COCOTBEXT_RYUSIM_MAKEFILES_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

SIM ?= icarus

ifneq ($(shell echo $(SIM) | tr A-Z a-z),ryusim)

include $(shell cocotb-config --makefiles)/Makefile.sim

else

# Mirrors the preamble of cocotb 2.1's Makefile.sim. The first target is make's
# default goal, so "all: sim" must come before Makefile.inc defines any target.
.PHONY: all
all: sim

PYTHON_BIN_RES := $(shell cocotb-config --python-bin 2>>/dev/null; echo $$?)
PYTHON_BIN_RC := $(lastword $(PYTHON_BIN_RES))
PYTHON_BIN := $(strip $(subst $(PYTHON_BIN_RC)QQQQ,,$(PYTHON_BIN_RES)QQQQ))
ifneq ($(PYTHON_BIN_RC),0)
    PYTHON_BIN := python3
endif

# Must precede Makefile.inc, which defaults unknown simulators to 0.
COCOTB_TRUST_INERTIAL_WRITES ?= 1

include $(shell $(PYTHON_BIN) -m cocotb_tools.config --makefiles)/Makefile.inc
include $(COCOTBEXT_RYUSIM_MAKEFILES_DIR)/simulators/Makefile.ryusim

endif
```

`COCOTBEXT_RYUSIM_MAKEFILES_DIR` must be the first assignment in the file. `$(lastword $(MAKEFILE_LIST))` names this file only until the next `include`.

**Step 4: Port `Makefile.ryusim` from the fork**

This is ported by script rather than retyped, so that the recipe lines keep their literal TAB characters. Each replacement asserts that it matched.

```bash
mkdir -p src/cocotbext/ryusim/makefiles/simulators
git -C ~/cocotb show 560b5227:src/cocotb_tools/makefiles/simulators/Makefile.ryusim > /tmp/Makefile.ryusim.fork
python3 - <<'EOF'
src = open("/tmp/Makefile.ryusim.fork").read()
edits = [
    (   # 1. credit both copyright holders
        "# Copyright cocotb contributors\n",
        "# Copyright cocotb contributors\n# Copyright (c) 2026 Seiraiyu\n",
    ),
    (   # 2. drop unused variables
        "# RyuSim root (for locating libryusim_vpi.so)\n"
        "RYUSIM_ROOT ?= $(shell dirname $(shell dirname $(CMD)))\n"
        "RYUSIM_VPI_LIB ?= $(RYUSIM_ROOT)/lib/libryusim_vpi.so\n\n",
        "",
    ),
    (   # 3. load cocotb's stock Verilator VPI library
        "# cocotb library paths\n",
        "# cocotb library paths. RyuSim's VPI callback semantics match Verilator's,\n"
        "# so cocotb's stock Verilator VPI library is loaded as-is.\n",
    ),
    (
        "--lib-name-path vpi ryusim)",
        "--lib-name-path vpi verilator)",
    ),
]
for old, new in edits:
    assert src.count(old) == 1, f"expected exactly one match for: {old!r}"
    src = src.replace(old, new)
open("src/cocotbext/ryusim/makefiles/simulators/Makefile.ryusim", "w").write(src)
print("ported")
EOF
```
Expected: `ported`

Run: `diff /tmp/Makefile.ryusim.fork src/cocotbext/ryusim/makefiles/simulators/Makefile.ryusim`
Expected: exactly three hunks, and nothing else:
1. the added copyright line;
2. the removed `RYUSIM_ROOT`/`RYUSIM_VPI_LIB` block;
3. the expanded comment together with `vpi ryusim` → `vpi verilator`. These lines are adjacent, so `diff` merges them into one hunk.

Run: `grep -c $'^\t' src/cocotbext/ryusim/makefiles/simulators/Makefile.ryusim`
Expected: a number greater than 20. The recipe TABs are intact.

Run: `grep -n "timescale" src/cocotbext/ryusim/makefiles/simulators/Makefile.ryusim`
Expected: `COMPILE_ARGS += --timescale $(COCOTB_HDL_TIMEUNIT)/$(COCOTB_HDL_TIMEPRECISION)`. The fix carries over from the fork.

**Step 5: Run the test, verify pass**

Run: `pytest tests/test_make_flow.py -v`
Expected: `2 passed`. The RyuSim case runs under the shim and the Icarus case runs through cocotb's own `Makefile.sim`.

If `test_ryusim` fails at runtime and not at compile, check that `--vpi-load` in the output points at `libcocotbvpi_verilator.so`.

**Step 6: Confirm the makefiles ship in the wheel**

Run: `python -m build --wheel && python -m zipfile -l dist/*.whl | awk '{print $1}' | grep makefiles; rm -rf dist`
Expected: `cocotbext/ryusim/makefiles/Makefile.sim` and `cocotbext/ryusim/makefiles/simulators/Makefile.ryusim`.

**Step 7: Commit**

```bash
git add src/cocotbext/ryusim/makefiles tests/test_make_flow.py
git commit -m "feat: Makefile flow via drop-in Makefile.sim shim"
```

Phase 1 is done. Update the design doc's phase table: row 1 becomes done / tested yes.

---

## Phase 2: Runner flow

### Task 6: `RyuSim(Runner)` and registration

**Files:**
- Create: `src/cocotbext/ryusim/runner.py`
- Modify: `src/cocotbext/ryusim/__init__.py` (replace it entirely)
- Test: `tests/test_runner_flow.py`

**Step 1: Write the failing test**

`tests/test_runner_flow.py`. It copies the DUT to `tmp_path` so that simulator output never lands in the source tree.
```python
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
```

**Step 2: Run the test, verify failure**

Run: `pytest tests/test_runner_flow.py -q`
Expected: 2 failures. The first is `AttributeError: module 'cocotbext.ryusim' has no attribute 'RyuSim'`, or `ValueError` from `get_runner` naming the supported simulators.

**Step 3: Implement**

`src/cocotbext/ryusim/runner.py`. This is ported from the fork's `cocotb_tools/runner.py` with one functional change: `_test_command` loads the `verilator` VPI library.
```python
# Copyright cocotb contributors
# Copyright (c) 2026 Seiraiyu
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""Python Runner for RyuSim, derived from cocotb_tools.runner."""

from __future__ import annotations

import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path

import cocotb_tools.config
from cocotb_tools.runner import (
    PathLike,
    Runner,
    Verilog,
    _Command,
    as_sv_literal,
    outdated,
)


class RyuSim(Runner):
    """Implementation of :class:`~cocotb_tools.runner.Runner` for RyuSim.

    * ``hdl_toplevel`` argument to :meth:`.build` is *required*.
    * Only supports Verilog/SystemVerilog (no VHDL).
    * Does not support the ``pre_cmd`` argument to :meth:`.test`.
    """

    supported_gpi_interfaces = {"verilog": ["vpi"]}

    def _simulator_in_path(self) -> None:
        if shutil.which("ryusim") is None:
            raise SystemExit("ERROR: ryusim executable not found!")

    def _get_include_options(self, includes: Sequence[PathLike]) -> _Command:
        return [f"-I{include}" for include in includes]

    def _get_define_options(self, defines: Mapping[str, object]) -> _Command:
        return [f"-D{name}={as_sv_literal(value)}" for name, value in defines.items()]

    def _get_parameter_options(self, parameters: Mapping[str, object]) -> _Command:
        # RyuSim's -G expects the raw SV value text (like Verilator); wrapping it
        # in an SV string literal would make ryusim read e.g. "8" as the string's
        # ASCII value rather than the integer 8.
        return [f"-G{name}={value}" for name, value in parameters.items()]

    @property
    def sim_file(self) -> Path:
        # ``sim_hdl_toplevel`` is only set by ``test()``; ``hdl_toplevel`` only by
        # ``build()``. Resolve whichever is available so ``sim_file`` works both in
        # the build path (``outdated()`` check) and the test-only path.
        toplevel = getattr(self, "sim_hdl_toplevel", None) or self.hdl_toplevel
        return self.build_dir / f"lib{toplevel}.so"

    def _use_external_viewer(self) -> bool:
        return True

    def _waves_file(self) -> str | None:
        # RyuSim's --trace-vcd always writes to trace.vcd in the run directory.
        return "trace.vcd"

    def _set_env_test(self) -> None:
        super()._set_env_test()
        if "COCOTB_TRUST_INERTIAL_WRITES" not in self.env:
            self.env["COCOTB_TRUST_INERTIAL_WRITES"] = "1"
        # The simulation model dlopens cocotb's VPI library via --vpi-load, which
        # in turn needs libgpi from the same directory.
        lib_dir = str(cocotb_tools.config.libs_dir)
        existing_ld_path = self.env.get("LD_LIBRARY_PATH", "")
        self.env["LD_LIBRARY_PATH"] = (
            f"{lib_dir}:{existing_ld_path}" if existing_ld_path else lib_dir
        )

    def _build_command(self) -> list[_Command]:
        if self.hdl_toplevel is None:
            raise ValueError("hdl_toplevel argument is required for all RyuSim builds")

        sources = self._sources + self._verilog_sources

        for source in sources:
            if source.tag is not Verilog:
                raise ValueError(
                    f"{type(self).__qualname__} only supports Verilog. "
                    f"{str(source.value)!r} cannot be compiled."
                )

        for arg in self._build_args:
            if arg.tag not in (Verilog, None):
                raise ValueError(
                    f"{type(self).__qualname__} only supports Verilog. "
                    f"build_args {arg.value!r} cannot be applied."
                )

        build_args = [arg.value for arg in self._build_args]
        if self.waves:
            build_args.append("--trace-vcd")

        cmds: list[_Command] = []
        if outdated(self.sim_file, (source.value for source in sources)) or self.always:
            cmds = [
                [
                    "ryusim",
                    "compile",
                    "--top",
                    self.hdl_toplevel,
                    "--Mdir",
                    str(self.build_dir),
                ]
                + (
                    ["--timescale", "{}/{}".format(*self.timescale)]
                    if self.timescale is not None
                    else []
                )
                + self._get_define_options(self.defines)
                + self._get_include_options(self.includes)
                + self._get_parameter_options(self.parameters)
                + build_args
                + [str(source_file.value) for source_file in sources]
            ]
        else:
            self.log.warning("Skipping compilation of %s", self.sim_file)

        return cmds

    def _test_command(self) -> list[_Command]:
        if self.pre_cmd is not None:
            raise RuntimeError("pre_cmd is not implemented for RyuSim.")

        # RyuSim's VPI callback semantics match Verilator's, so cocotb's stock
        # Verilator VPI library is used as-is. No RyuSim-specific build exists.
        return [
            [
                str(self.sim_file),
                "--vpi-load",
                cocotb_tools.config.lib_name_path("vpi", "verilator").as_posix(),
                *self.test_args,
                *self.plusargs,
            ]
        ]
```

`src/cocotbext/ryusim/__init__.py` (replaces the Task 2 version). A missing cocotb internal fails here with a message naming the version requirement, never silently (§6).
```python
"""RyuSim simulator support for cocotb."""

try:
    from cocotb_tools.runner import SUPPORTED_RUNNERS

    from cocotbext.ryusim.runner import RyuSim
except ImportError as e:
    raise ImportError(
        "cocotbext-ryusim requires cocotb>=2.1,<2.2, and a cocotb internal it "
        f"depends on is missing ({e}). Check the installed version with "
        "`pip show cocotb`."
    ) from e

SUPPORTED_RUNNERS["ryusim"] = RyuSim

__all__ = ["RyuSim"]
```

**Step 4: Run the test, verify pass**

Run: `pytest tests/test_runner_flow.py -v`
Expected: `2 passed`

**Step 5: Verify the version-mismatch error**

Run:
```bash
python - <<'EOF'
import cocotb_tools.runner as r
del r.SUPPORTED_RUNNERS
try:
    import cocotbext.ryusim
except ImportError as e:
    print("OK:", e)
EOF
```
Expected: `OK: cocotbext-ryusim requires cocotb>=2.1,<2.2, and a cocotb internal it depends on is missing (cannot import name 'SUPPORTED_RUNNERS' …`

**Step 6: Run the whole suite**

Run: `pytest -q`
Expected: `6 passed`

**Step 7: Commit**

```bash
git add src/cocotbext/ryusim/runner.py src/cocotbext/ryusim/__init__.py tests/test_runner_flow.py
git commit -m "feat: Runner flow with get_runner('ryusim') registration"
```

Phase 2 is done. Update the design doc's phase table: row 2.

---

## Phase 3: pytest flow

**Background for this phase (§5.3).** cocotb's plugin builds the `--cocotb-simulator` choices from `_SIMULATORS` into the module-level tuple `_OPTIONS` (`cocotb_tools/_pytest/plugin.py:109`). `pytest_addoption` is a **historic** hook: each plugin's implementation runs the moment that plugin registers. So:

- **If our plugin registers first:** adding `ryusim` to `_SIMULATORS` at import time is enough. cocotb builds its tuple afterwards.
- **If cocotb's plugin registers first** (the usual case, because cocotb's docs have users pass `-p cocotb_tools._pytest.plugin`, which loads during pre-parse, before `pytest11` entry points): `--cocotb-simulator` is already stored on pytest's parser with the old choices. Our `pytest_addoption` must extend the choices on that stored argument. `Argument.attrs()` returns the live dict, which is the argparse `Action.__dict__` on pytest 9.

Both paths were verified during planning on pytest 8.4.2 and 9.1.1. The design's stop condition is met, so no redesign is needed.

### Task 7: pytest plugin

**Files:**
- Create: `src/cocotbext/ryusim/_pytest_plugin.py`
- Modify: `pyproject.toml`: add the `pytest11` entry point
- Test: `tests/test_pytest_flow.py`

**Step 1: Write the failing test**

`tests/test_pytest_flow.py`:
```python
import os
import shutil
import subprocess
import sys
from pathlib import Path

DUT = Path(__file__).parent / "dut"


def _pytest(tmp_path: Path, plugin_args: list[str], env: dict[str, str] | None = None):
    shutil.copy(DUT / "dut.sv", tmp_path)
    shutil.copy(DUT / "pt_case.py", tmp_path / "test_pt_dut.py")
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *plugin_args,
         "--cocotb-simulator", "ryusim", "test_pt_dut.py"],
        cwd=tmp_path,
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
    )


def test_cocotb_plugin_registered_first(tmp_path):
    # The documented setup: cocotb's plugin via -p (registered during pre-parse),
    # ours via its pytest11 entry point afterwards.
    proc = _pytest(tmp_path, ["-p", "cocotb_tools._pytest.plugin"])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "1 passed cocotb runner" in proc.stdout


def test_our_plugin_registered_first(tmp_path):
    proc = _pytest(
        tmp_path,
        ["-p", "cocotbext.ryusim._pytest_plugin", "-p", "cocotb_tools._pytest.plugin"],
        env={"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "1 passed cocotb runner" in proc.stdout
```

**Step 2: Run the test, verify failure**

Run: `pytest tests/test_pytest_flow.py -q`
Expected: 2 failures.
- `test_cocotb_plugin_registered_first`: the output contains `argument --cocotb-simulator: invalid choice: 'ryusim'`.
- `test_our_plugin_registered_first`: the output contains `ImportError`/`ModuleNotFoundError` for `cocotbext.ryusim._pytest_plugin`.

**Step 3: Implement the plugin**

`src/cocotbext/ryusim/_pytest_plugin.py`:
```python
"""pytest plugin: makes ``--cocotb-simulator ryusim`` work with cocotb's plugin."""

from __future__ import annotations

from typing import Any

import cocotbext.ryusim  # noqa: F401  (registers the "ryusim" runner)

try:
    from cocotb_tools._pytest.hdl import _SIMULATORS
except ImportError as e:
    raise ImportError(
        "cocotbext-ryusim requires cocotb>=2.1,<2.2, and a cocotb internal it "
        f"depends on is missing ({e}). Check the installed version with "
        "`pip show cocotb`."
    ) from e

# If this module is imported before cocotb's plugin module, cocotb builds its
# --cocotb-simulator choices from _SIMULATORS and picks "ryusim" up directly.
# Appended last, so `--cocotb-simulator auto` only selects RyuSim when no other
# supported simulator is on PATH.
_SIMULATORS.setdefault("ryusim", "ryusim")


def pytest_addoption(parser: Any) -> None:
    # If cocotb's plugin registered first, its pytest_addoption (a historic hook,
    # run at registration) already stored --cocotb-simulator on the parser with
    # the old choices. Extend them on the stored argument.
    for group in parser._groups:
        for arg in group.options:
            if "--cocotb-simulator" in arg.names():
                attrs = arg.attrs()
                choices = attrs.get("choices")
                if choices is not None and "ryusim" not in choices:
                    attrs["choices"] = (*choices, "ryusim")
```

**Step 4: Register the entry point**

Add this to `pyproject.toml`, after the `[project.scripts]` table:
```toml
[project.entry-points.pytest11]
cocotbext_ryusim = "cocotbext.ryusim._pytest_plugin"
```

Entry points are read at install time, so reinstall:

Run: `pip install -e ".[test]"`

**Step 5: Run the test, verify pass**

Run: `pytest tests/test_pytest_flow.py -v`
Expected: `2 passed`

**Step 6: Confirm validation isn't loosened**

Run: `cd "$(mktemp -d)" && python -m pytest -q --co -p cocotb_tools._pytest.plugin --cocotb-simulator bogus 2>&1 | grep -o "invalid choice: 'bogus'"; cd -`
Expected: `invalid choice: 'bogus'`

**Step 7: Run the whole suite**

Run: `pytest -q`
Expected: `8 passed`

**Step 8: Commit**

```bash
git add src/cocotbext/ryusim/_pytest_plugin.py pyproject.toml tests/test_pytest_flow.py
git commit -m "feat: pytest plugin registering --cocotb-simulator ryusim"
```

Phase 3 is done. Update the design doc's phase table: row 3.

---

## Phase 4: CI

### Task 8: CI workflow and local conformance run

GitHub Actions can't run until the repo exists (Task 11). This task therefore writes the workflow and runs the **conformance job's commands locally**. Task 11 then proves the workflow itself on GitHub.

**Files:**
- Create: `.github/workflows/ci.yml`

**Step 1: Write the workflow**

`.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
  pull_request:
  schedule:
    - cron: "0 3 * * 1"  # weekly, Mondays 03:00 UTC: catches new RyuSim releases
  workflow_dispatch:

jobs:
  smoke:
    name: smoke (py${{ matrix.python }}, ${{ matrix.cocotb }})
    runs-on: ubuntu-24.04
    strategy:
      fail-fast: false
      matrix:
        python: ["3.9", "3.13"]
        cocotb: ["cocotb==2.1.0", "cocotb>=2.1,<2.2"]  # cap floor, newest under cap
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - name: Install toolchain, Icarus and RyuSim
        run: |
          sudo apt-get update
          sudo apt-get install -y --no-install-recommends clang cmake iverilog
          curl -fsSL https://ryusim.seiraiyu.com/install.sh | bash
          echo "$HOME/.ryusim/bin" >> "$GITHUB_PATH"
      - name: Install package
        run: |
          python -m pip install --upgrade pip
          pip install "${{ matrix.cocotb }}" -e ".[test]"
      - name: Versions
        run: |
          ryusim --version
          python -c "import cocotb; print('cocotb', cocotb.__version__)"
      - run: pytest -v

  conformance:
    # cocotb's full Verilog regression through this package (§7.2). It takes
    # about 10 minutes, so it runs on main and weekly, not on every PR.
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install toolchain and RyuSim
        run: |
          sudo apt-get update
          sudo apt-get install -y --no-install-recommends clang cmake
          curl -fsSL https://ryusim.seiraiyu.com/install.sh | bash
          echo "$HOME/.ryusim/bin" >> "$GITHUB_PATH"
      - name: Install cocotb and this package
        run: pip install "cocotb>=2.1,<2.2" .
      - name: Check out cocotb's test suite at the installed version
        run: |
          V=$(python -c "import cocotb; print(cocotb.__version__)")
          git clone --depth 1 --branch "v$V" https://github.com/cocotb/cocotb.git cocotb-src
      - name: Make RyuSim visible to cocotb's stock test Makefiles
        # CI-only: users never do this (§5.1). cocotb's test Makefiles use the
        # stock include, which only searches cocotb's own install dir.
        run: |
          cp "$(cocotbext-ryusim-config --makefiles)/simulators/Makefile.ryusim" \
             "$(cocotb-config --makefiles)/simulators/"
      - name: Run cocotb's Verilog regression
        working-directory: cocotb-src
        env:
          SIM: ryusim
          TOPLEVEL_LANG: verilog
          # Stock Makefile.inc doesn't know ryusim; our shim sets this for users.
          COCOTB_TRUST_INERTIAL_WRITES: "1"
        run: make -k test
```

**Step 2: Validate the YAML**

Run: `pip install pyyaml && python -c "import yaml; d=yaml.safe_load(open('.github/workflows/ci.yml')); print(sorted(d['jobs']))"`
Expected: `['conformance', 'smoke']`

**Step 3: Run the conformance job locally**

Use a separate throwaway venv, because the copy step writes into cocotb's install dir. **Never** run this against `.venv` or the system cocotb.

```bash
C=$(mktemp -d)
python3 -m venv "$C/venv" && . "$C/venv/bin/activate"
pip install --upgrade pip && pip install "cocotb>=2.1,<2.2" .
V=$(python -c "import cocotb; print(cocotb.__version__)")
git clone --depth 1 --branch "v$V" https://github.com/cocotb/cocotb.git "$C/cocotb-src"
cp "$(cocotbext-ryusim-config --makefiles)/simulators/Makefile.ryusim" "$(cocotb-config --makefiles)/simulators/"
cd "$C/cocotb-src"
SIM=ryusim TOPLEVEL_LANG=verilog COCOTB_TRUST_INERTIAL_WRITES=1 make -k test 2>&1 | tee "$C/conformance.log" | grep -E "Failed regression suite|TESTS=" | tail -20
echo "failed suites: $(grep -c 'Failed regression suite' "$C/conformance.log")"
deactivate; cd ~/cocotbext-ryusim; . .venv/bin/activate
```
Expected: `failed suites: 0`, and every `TESTS=` line shows `FAIL=0`. This matches probe run 35814685258 on the fork. It takes about 10 minutes.

If a suite fails, compare it against that probe. A failure that passed on the fork points at the package, most likely the `verilator` VPI library or a missing environment variable. Diagnose it before continuing; don't skip it.

**Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: smoke matrix and cocotb conformance regression"
```

Phase 4 is done, apart from the GitHub run, which happens in Task 11. Update the design doc's phase table: row 4 becomes tested yes (local).

---

## Phase 5: Documentation

### Task 9: README

**Files:**
- Modify: `README.md` (replace it entirely)

**Step 1: Write it**

`README.md`:
````markdown
# cocotbext-ryusim

[RyuSim](https://ryusim.com) simulator support for [cocotb](https://www.cocotb.org).

Adds `SIM=ryusim` to all three cocotb flows (Makefile, Python Runner and pytest)
on stock, released cocotb. Pure Python: no fork of cocotb, no C++ toolchain, no
compiled extension.

## Requirements

- cocotb **2.1.x**
- Python 3.9+
- Linux
- RyuSim on `PATH`: `curl -fsSL https://ryusim.com/install.sh | bash`

## Install

```bash
pip install cocotbext-ryusim
```

This installs a compatible cocotb alongside it.

## Makefile flow

Change one line in your testbench Makefile:

```make
# before
include $(shell cocotb-config --makefiles)/Makefile.sim
# after
include $(shell cocotbext-ryusim-config --makefiles)/Makefile.sim
```

Then run `make SIM=ryusim`. Any other `SIM` value is passed to cocotb's own
`Makefile.sim` unchanged, so the same Makefile still runs Icarus, Verilator and
the other simulators.

Standard cocotb variables work as usual (`COCOTB_TOPLEVEL`, `VERILOG_SOURCES`,
`COCOTB_HDL_TIMEUNIT`, `WAVES=1` and so on). Set `RYUSIM_BIN_DIR` to use a
`ryusim` that isn't on `PATH`. `make help` isn't available for `SIM=ryusim`.

## Python Runner

```python
import cocotbext.ryusim  # registers "ryusim"
from cocotb_tools.runner import get_runner

runner = get_runner("ryusim")
runner.build(sources=["dut.sv"], hdl_toplevel="dut", timescale=("1ns", "1ps"))
runner.test(hdl_toplevel="dut", test_module="test_dut")
```

You can also construct `cocotbext.ryusim.RyuSim()` directly. `hdl_toplevel` is
required, and `pre_cmd` is not supported.

## pytest

The plugin loads automatically once the package is installed. Select RyuSim
explicitly:

```bash
pytest -p cocotb_tools._pytest.plugin --cocotb-simulator ryusim
```

With `--cocotb-simulator auto`, cocotb picks the first supported simulator it
finds on `PATH`, and RyuSim comes last in that order. Pass `ryusim` explicitly
if other simulators are also installed.

## What RyuSim supports

Verilog and SystemVerilog through VPI. There is no VHDL support.

These parts of IEEE 1800-2023 are not implemented: switch-level modelling
(clause 28; gate-level support covers the basic gate primitives only),
user-defined primitives (29), `specify` blocks (30), timing checks (31), SDF
back-annotation (32), design configurations (33), and the VPI assertion,
coverage-control and data-read APIs (39–41).

RyuSim rejects anything it doesn't implement at compile time, so an unsupported
construct is always a compile error rather than a silent mis-simulation.

Inertial writes are trusted by default (`COCOTB_TRUST_INERTIAL_WRITES=1`), as
cocotb does for Verilator, GHDL and NVC.

## How it works

RyuSim's VPI callback behavior matches Verilator's, so this package loads
cocotb's own `libcocotbvpi_verilator.so`. It adds `ryusim` to cocotb's runner and
pytest registries, and ships the RyuSim makefile. It never modifies cocotb's
installed files.

## cocotb compatibility

This package relies on some cocotb internals, so it pins `cocotb>=2.1,<2.2`. A
new cocotb minor release gets a new cocotbext-ryusim release once CI passes
against it. Until then, pip keeps a compatible cocotb rather than breaking at
runtime. CI runs cocotb's full Verilog regression through this package.

## License

BSD-3-Clause. Portions are derived from cocotb, © cocotb contributors; see
[LICENSE](LICENSE).
````

**Step 2: Verify the README examples match the code**

Run: `grep -c "cocotbext-ryusim-config --makefiles" README.md tests/test_make_flow.py`
Expected: at least `1` for each file.

Run: `python -c "import cocotbext.ryusim as m; print(m.RyuSim.__name__)"`
Expected: `RyuSim`

**Step 3: Confirm the README renders as the PyPI long description**

Run: `python -m build && pip install twine && twine check dist/*; rm -rf dist`
Expected: `PASSED` for both the sdist and the wheel.

**Step 4: Commit**

```bash
git add README.md
git commit -m "docs: README"
```

Phase 5 is done. Update the design doc's phase table: row 5.

---

## Phase 6: Release

### Task 10: Release workflow

**Files:**
- Create: `.github/workflows/release.yml`

**Step 1: Write the workflow**

`.github/workflows/release.yml`. On a `v*` tag it builds, publishes to TestPyPI, installs the TestPyPI artifact into a clean environment, runs the smoke tests against it, and only then publishes to PyPI (§8).
```yaml
name: Release

on:
  push:
    tags: ["v*"]

jobs:
  build:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Tag matches package version
        run: |
          V=$(python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
          test "v$V" = "${GITHUB_REF_NAME}" || { echo "tag ${GITHUB_REF_NAME} != v$V"; exit 1; }
      - run: pip install build && python -m build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  testpypi:
    needs: build
    runs-on: ubuntu-24.04
    environment: testpypi
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://test.pypi.org/legacy/

  verify:
    needs: testpypi
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install toolchain, Icarus and RyuSim
        run: |
          sudo apt-get update
          sudo apt-get install -y --no-install-recommends clang cmake iverilog
          curl -fsSL https://ryusim.seiraiyu.com/install.sh | bash
          echo "$HOME/.ryusim/bin" >> "$GITHUB_PATH"
      - name: Install the published artifact from TestPyPI
        # Dependencies come from real PyPI first. Only this package is fetched
        # from TestPyPI, with --no-deps: anyone can upload to TestPyPI, and
        # mixing the indexes would let a planted "cocotb" there win on version.
        run: |
          V=${GITHUB_REF_NAME#v}
          pip install "cocotb>=2.1,<2.2" pytest
          for i in 1 2 3 4 5 6; do
            pip install --no-deps --index-url https://test.pypi.org/simple/ \
              "cocotbext-ryusim==$V" && break
            sleep 20  # TestPyPI's index can lag the upload
          done
          python -c "import cocotbext.ryusim"
      - name: Smoke tests against the installed artifact
        # Remove the source tree so tests import the installed wheel, not ./src.
        run: rm -rf src && pytest -v tests

  pypi:
    needs: verify
    runs-on: ubuntu-24.04
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
```

**Step 2: Validate the YAML**

Run: `python -c "import yaml; d=yaml.safe_load(open('.github/workflows/release.yml')); print(list(d['jobs']))"`
Expected: `['build', 'testpypi', 'verify', 'pypi']`

**Step 3: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: release to TestPyPI, verify, then PyPI"
```

---

### Task 11: Create the GitHub repo and push

> **Stop and ask the user before this task.** It creates a public repository under the `Seiraiyu` organization. Confirm the name and that it should be public.

**Step 1: Create and push**

Run: `gh repo create Seiraiyu/cocotbext-ryusim --public --description "RyuSim simulator support for cocotb" --source . --push`
Expected: the repo URL is printed, and `main` is pushed.

**Step 2: Watch CI**

Run: `gh run watch "$(gh run list --repo Seiraiyu/cocotbext-ryusim --workflow ci.yml --limit 1 --json databaseId --jq '.[0].databaseId')" --repo Seiraiyu/cocotbext-ryusim --exit-status`
Expected: all 4 `smoke` jobs and the `conformance` job succeed.

If a job fails, read the log with `gh run view <id> --repo Seiraiyu/cocotbext-ryusim --log-failed`. Fix the cause, commit, push, and watch again. Do not continue to Task 12 with a red CI.

**Step 3: Update the plan status**

Mark Tasks 1–11 as pushed in this plan's table, and rows 1–5 as pushed in the design doc's table. Commit and push.

---

### Task 12: Configure trusted publishing

> **The user does this, in a browser.** No tokens are created or stored. List these exact values for them and wait for confirmation.

1. **PyPI**, at https://pypi.org/manage/account/publishing/ → *Add a new pending publisher*:
   - PyPI project name: `cocotbext-ryusim`
   - Owner: `Seiraiyu`
   - Repository name: `cocotbext-ryusim`
   - Workflow name: `release.yml`
   - Environment name: `pypi`
2. **TestPyPI**, at https://test.pypi.org/manage/account/publishing/: the same values, except the environment name is `testpypi`.
3. **GitHub environments.** These can be run from the CLI:
   ```bash
   gh api -X PUT repos/Seiraiyu/cocotbext-ryusim/environments/testpypi
   gh api -X PUT repos/Seiraiyu/cocotbext-ryusim/environments/pypi
   ```
   Expected: JSON describing each environment.

---

### Task 13: Release v0.1.0

> **Stop and ask the user before this task.** Pushing the tag publishes to PyPI, and a PyPI version can never be re-uploaded, even if it's deleted.

**Step 1: Tag and push**

```bash
git tag -a v0.1.0 -m "cocotbext-ryusim 0.1.0"
git push origin v0.1.0
```

**Step 2: Watch the release**

Run: `gh run watch "$(gh run list --repo Seiraiyu/cocotbext-ryusim --workflow release.yml --limit 1 --json databaseId --jq '.[0].databaseId')" --repo Seiraiyu/cocotbext-ryusim --exit-status`
Expected: `build`, `testpypi`, `verify` and `pypi` all succeed.

**Step 3: Verify from real PyPI in a clean environment**

```bash
R=$(mktemp -d) && python3 -m venv "$R/v" && . "$R/v/bin/activate"
pip install cocotbext-ryusim
python -c "import cocotb, cocotbext.ryusim; print(cocotb.__version__, cocotbext.ryusim.RyuSim.__name__)"
cocotbext-ryusim-config --version
deactivate
```
Expected: `2.1.0 RyuSim` (or a newer 2.1.x), then `0.1.0`.

**Step 4: Close out**

Mark every task in this plan's table, and every row in the design doc's table, as done, tested and pushed. Commit and push.

Report to the user: the PyPI URL (https://pypi.org/project/cocotbext-ryusim/), the green CI run, and a reminder that consumer migration and the ryusim.com getting-started page are follow-up work (design §9).
