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
