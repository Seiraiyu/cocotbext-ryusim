# cocotbext-ryusim — Design

**Date:** 2026-09-23
**Status:** Draft for review
**Repo:** `Seiraiyu/cocotbext-ryusim` (not yet created on GitHub)

## 1. Goal

Ship RyuSim support for cocotb as a pure-Python package on PyPI, so that

```bash
pip install cocotb cocotbext-ryusim
```

gives a working `SIM=ryusim` in all three cocotb flows — Makefile, Python Runner, and pytest plugin — on **released** cocotb, with no fork, no C++ toolchain, and no compiled artifacts.

**Done means:** `cocotbext-ryusim` 0.1.0 is on PyPI, and its CI runs cocotb's full Verilog regression against the latest RyuSim release through the package, green.

## 2. Background

cocotb PR #5630 (RyuSim support) was closed on 2026-09-22 under a new maintainer policy: no more simulators in the cocotb repo; simulators should live in extension packages that depend on cocotb. Until now, RyuSim support has lived in the `Seiraiyu/cocotb` fork on branch `feat/ryusim-simulator-support`, which consumers install with `git+https` and must build from source.

Investigation established the facts this design rests on:

| Fact | Evidence |
|---|---|
| RyuSim needs no RyuSim-specific GPI code. | The fork's only C++ change defines `RYUSIM` at exactly the two sites `VERILATOR` is defined (`VpiCbHdl.cpp:112,148`). |
| The stock Verilator VPI library in cocotb **2.1.0** already has that behavior. | `v2.1.0:VpiCbHdl.cpp` carries `#ifndef VERILATOR` / `#ifdef VERILATOR` at the same sites. |
| cocotb 2.1.0 is the minimum. | 2.0.x has no pytest plugin and `runner.py` grew ~1000 lines by 2.1.0; RyuSimAlt's devcontainer already records that 2.0.x breaks. |
| Released 2.1.0 and current master are identical in everything the package touches. | `git diff v2.1.0 master` is empty across `runner.py`, `config.py`, `Makefile.inc` and all simulator makefiles. |
| cocotb's in-progress library rework is not scheduled for a release. | PR #5745 merged into `feature/library-refactor`, not master. |
| The fork's code is CI-proven on RyuSim 2.1.16. | Probe run 35814685258: full Verilog regression, `FAIL=0`, no RyuSim-specific guards. |

## 3. Decisions

| # | Decision | Choice | Why |
|---|---|---|---|
| D1 | Name | Distribution `cocotbext-ryusim`, import `cocotbext.ryusim` | cocotb's documented extension convention (`docs/source/extensions.rst`); matches the maintainers' own "extension package" framing. |
| D2 | cocotb dependency | `cocotb>=2.1,<2.2` | The package subclasses `Runner` and mutates internal registries. A cap turns a breaking cocotb release into an install-time conflict instead of a runtime failure. Raised per cocotb minor, after CI passes against it. |
| D3 | Python | `>=3.9` | Matches cocotb 2.1.0's `requires-python`. |
| D4 | Compiled code | None. Load stock `libcocotbvpi_verilator.so`. | See §2. Shipping `libcocotbvpi_ryusim.so` would mean subclassing C++ classes from `gpi_priv.h`, which cocotb does not install, and binding to its vtable layout. |
| D5 | Makefile flow | Drop-in `Makefile.sim` shim | See §5.1. |
| D6 | Flows shipped | Makefile, Runner, and pytest plugin | Full parity with the closed PR. |
| D7 | CI | Per-flow smoke tests on every push, plus cocotb's full Verilog regression | See §7. |
| D8 | License | BSD-3-Clause, keeping cocotb contributors' copyright notice alongside Seiraiyu's | The Runner class and `Makefile.ryusim` derive from cocotb (BSD-3-Clause). |
| D9 | Scope | Package through PyPI release only | See §9. |

## 4. Architecture

```
user's Makefile / runner script / pytest session
          │
          ▼
┌──────────────────────── cocotbext-ryusim ────────────────────────┐
│  Makefile.sim shim ──► Makefile.ryusim     (make flow)           │
│  RyuSim(Runner)    ──► SUPPORTED_RUNNERS   (runner flow)         │
│  pytest11 plugin   ──► _SIMULATORS         (pytest flow)         │
└──────────────────────────────┬───────────────────────────────────┘
                               │ `ryusim compile` + run with
                               │ --vpi-load libcocotbvpi_verilator.so
                               ▼
        stock cocotb 2.1.x (unmodified)  ◄──►  RyuSim binary
```

The package only adds entries to cocotb's registries and supplies build/run commands. It never modifies cocotb's installed files.

### 4.1 Layout

```
cocotbext-ryusim/
├── pyproject.toml
├── LICENSE
├── README.md
├── src/cocotbext/                  # implicit namespace package: no __init__.py
│   └── ryusim/
│       ├── __init__.py             # exports RyuSim; registers the runner on import
│       ├── runner.py               # class RyuSim(Runner)
│       ├── _pytest_plugin.py       # pytest11 entry point
│       ├── config.py               # `cocotbext-ryusim-config` CLI
│       └── makefiles/
│           ├── Makefile.sim        # the shim users include
│           └── Makefile.ryusim
├── tests/
│   ├── dut/                        # one tiny Verilog DUT shared by all smoke tests
│   ├── test_make_flow.py
│   ├── test_runner_flow.py
│   └── test_pytest_flow.py
├── .github/workflows/
│   ├── ci.yml
│   └── release.yml
└── docs/plans/
```

`src/cocotbext/` must not contain an `__init__.py`. Other `cocotbext-*` packages (such as `cocotbext-axi`) share the `cocotbext` namespace, and an `__init__.py` would shadow them.

### 4.2 `pyproject.toml` essentials

```toml
[project]
name = "cocotbext-ryusim"
requires-python = ">=3.9"
dependencies = ["cocotb>=2.1,<2.2"]
license = "BSD-3-Clause"

[project.scripts]
cocotbext-ryusim-config = "cocotbext.ryusim.config:main"

[project.entry-points.pytest11]
cocotbext_ryusim = "cocotbext.ryusim._pytest_plugin"
```

The makefiles ship as package data.

## 5. Components

### 5.1 Makefile flow

Stock cocotb resolves simulators only inside its own install directory:

```make
# cocotb Makefile.sim:96
include $(COCOTB_MAKEFILES_DIR)/simulators/Makefile.$(SIM_LOWERCASE)
```

So a third-party `Makefile.ryusim` cannot be reached through the standard include. Users change one line:

```make
# before
include $(shell cocotb-config --makefiles)/Makefile.sim
# after
include $(shell cocotbext-ryusim-config --makefiles)/Makefile.sim
```

**The shim (`makefiles/Makefile.sim`)**:

- If `SIM` is anything other than `ryusim`, it includes cocotb's own `Makefile.sim` and does nothing else. The same user Makefile keeps working unchanged for icarus, verilator and the rest.
- If `SIM=ryusim`, it reproduces the preamble of cocotb 2.1's `Makefile.sim`, in order:
  1. `.PHONY: all` and `all: sim`, declared **before** anything else, because the first target is make's default goal (the ordering bug fixed in fork commit 83702118).
  2. `PYTHON_BIN` resolved the same way cocotb does (`cocotb-config --python-bin`, falling back to `python3`).
  3. `COCOTB_TRUST_INERTIAL_WRITES ?= 1`, set **before** `Makefile.inc`, so that cocotb's own `?= 0` for unknown simulators does not win.
  4. `include` of cocotb's `Makefile.inc`, which defines `sim`, `regression` and `clean`.
  5. `include` of our `Makefile.ryusim`.

`make help` is not reproduced for `SIM=ryusim`. Add it if someone asks.

This preamble is the package's largest point of coupling to cocotb internals. It is pinned by D2, and every CI run exercises it.

**`Makefile.ryusim`** is ported from the fork (`feat/ryusim-simulator-support` @ 560b5227), with three changes:

- `--lib-name-path vpi ryusim` becomes `--lib-name-path vpi verilator`.
- The unused `RYUSIM_ROOT` and `RYUSIM_VPI_LIB` variables are removed.
- The copyright header credits both cocotb contributors and Seiraiyu.

The timescale fix (`--timescale $(COCOTB_HDL_TIMEUNIT)/$(COCOTB_HDL_TIMEPRECISION)`) is kept.

**`cocotbext-ryusim-config`** supports `--makefiles` (prints the path to our makefiles directory) and `--version`. It has no other flags.

### 5.2 Runner flow

`runner.py` holds `RyuSim(Runner)`, ported from the fork's `cocotb_tools/runner.py`, with one change: `lib_name_path("vpi", "ryusim")` becomes `lib_name_path("vpi", "verilator")`.

The class keeps the fork's behavior:

- `hdl_toplevel` is required, and Verilog is the only accepted language.
- `timescale` is forwarded as `--timescale`.
- `COCOTB_TRUST_INERTIAL_WRITES=1` is set unless the user overrides it.
- cocotb's library directory is prepended to `LD_LIBRARY_PATH`.
- `pre_cmd` raises an error.

Importing `cocotbext.ryusim` performs:

```python
SUPPORTED_RUNNERS["ryusim"] = RyuSim
```

After that import, both `get_runner("ryusim")` and direct use of `RyuSim()` work.

### 5.3 pytest flow

A `pytest11` entry point loads `_pytest_plugin.py` automatically once the package is installed. The plugin imports `cocotbext.ryusim` (which registers the runner) and adds:

```python
_SIMULATORS["ryusim"] = "ryusim"   # cocotb_tools._pytest.hdl
```

**Known hazard, resolved in Phase 3.** cocotb's plugin builds the `--cocotb-simulator` choices from `_SIMULATORS` into a module-level tuple (`_OPTIONS`, `plugin.py:109`) when its module is imported. pytest does not guarantee the order in which plugins load. If cocotb's plugin is imported first, `ryusim` is missing from the choices and `--cocotb-simulator ryusim` is rejected.

Phase 3 must first reproduce this in both load orders. The planned fix is a `pytest_addoption(tryfirst=True)` hook in our plugin that replaces the `cocotb_simulator` entry in `_OPTIONS` with one that includes `ryusim`, before cocotb's own `pytest_addoption` registers the options. If that does not hold in both orders, Phase 3 stops and the design is revisited. It does not ship with a workaround.

**Auto-detection.** With `--cocotb-simulator auto` (the default), cocotb picks the first simulator in `_SIMULATORS` whose executable is on `PATH`. `ryusim` is appended last, so it is chosen only when no other supported simulator is installed. The README tells users to pass `--cocotb-simulator ryusim` explicitly.

## 6. Error handling

| Situation | Behavior |
|---|---|
| `ryusim` is not on `PATH` | Make: the existing `$(error Unable to locate command >ryusim<)`. Runner: `SystemExit("ERROR: ryusim executable not found!")`. Both are ported unchanged. |
| VHDL sources, or a non-Verilog toplevel | Make skips with a message, as cocotb does for other Verilog-only simulators. Runner raises `ValueError`, ported unchanged. |
| cocotb version outside `>=2.1,<2.2` | pip refuses to install. This is the intended failure mode. |
| A cocotb internal the package relies on has moved (`SUPPORTED_RUNNERS`, `_SIMULATORS`, `_OPTIONS`) | Fail at import with an error naming the missing symbol and the cocotb version it was built for. Never a silent fallback. |
| The unsupported-construct error in RyuSim | Passes through unchanged. RyuSim rejects unimplemented constructs at compile time. |

## 7. Testing

### 7.1 Smoke tests (every push)

One small Verilog DUT that exercises a clock, a timescale-sensitive `#` delay, and a VPI read and write. Three tests, one per flow:

- **`test_make_flow`** runs `make` with the shim and `SIM=ryusim` and checks the result. A second case runs the same Makefile with `SIM=icarus` and checks that forwarding to cocotb works.
- **`test_runner_flow`** covers `get_runner("ryusim")`, build and test, and checks that the timescale is honored.
- **`test_pytest_flow`** runs a pytest session with `--cocotb-simulator ryusim`, in **both** plugin load orders (see §5.3).

CI matrix: Python 3.9 and the newest Python that cocotb 2.1 supports, against the cocotb version at the cap floor and the latest release under the cap, on `ubuntu-24.04`. RyuSim is installed from `install.sh` at `latest`.

### 7.2 Conformance (every push to `main`, and weekly)

This job runs cocotb's full Verilog regression through the package:

1. Install the cocotb wheel from PyPI at the version under test, then install this package.
2. Check out cocotb's repository at the matching tag. Only its `tests/` directory is used.
3. Copy `Makefile.ryusim` into the **installed** cocotb's `makefiles/simulators/` directory. This is acceptable on a throwaway CI runner, even though §5.1 rejects it for users. cocotb's test Makefiles use the stock include, so this is the only way they can find RyuSim.
4. Run the regression with `SIM=ryusim TOPLEVEL_LANG=verilog`. This calls make directly, because cocotb's `noxfile.py` hard-codes its list of simulators.

This job tests RyuSim running on stock cocotb through the stock Verilator VPI library. The smoke tests cover the shim, so the two jobs prove different things. The weekly run catches new RyuSim releases. RyuSim's own CI continues to test RyuSim builds, which is a separate axis.

## 8. Release

- **Versioning:** independent semver, starting at `0.1.0`. A release that raises the cocotb cap is a minor version bump.
- **Publishing:** `release.yml` runs on a `v*` tag, builds the sdist and wheel, and publishes to PyPI with trusted publishing (OIDC). No API tokens are stored.
- **Pre-release:** publish to TestPyPI first, then install into a clean virtualenv and run the smoke tests against the published artifact before tagging the real release.

## 9. Out of scope

- **Migrating consumers.** taxi-on-ryusim, RyuSim-Validation, Ryusim-Fuzz, subaya-platform and the RyuSimAlt devcontainer all pin the fork today. Migrating them is planned separately. The known steps, recorded here so they aren't lost:
  - Change `requirements.txt` from `cocotb @ git+…@feat/ryusim-simulator-support` to `cocotb cocotbext-ryusim`.
  - Change the include line in about 207 testbench Makefiles (163 in taxi-on-ryusim, 44 in RyuSim-Validation). This is a mechanical `sed`.
  - Remove the C++ toolchain from the Dockerfiles, since it was only there to build the fork.
  - **Prerequisite for taxi-on-ryusim:** its `Seiraiyu/cocotb-test` fork calls `lib_name_path("vpi", "ryusim")`, and that library does not exist in stock cocotb. It must change to `"verilator"` and gain the timescale fix before taxi moves off the cocotb fork, or it breaks.
- **The `Seiraiyu/cocotb-test` fork itself.** Whether to upstream it to `themperek/cocotb-test` is a separate decision.
- **Upstream contributions to cocotb:** extension hooks for third-party makefiles and runners, or turning the `VERILATOR` define into a runtime flag. Both were invited by the maintainers. Neither is needed here.
- **The ryusim.com getting-started page,** which currently points users at the fork.
- **Retiring the fork,** which happens after migration.

## 10. Phases

| Phase | Description | Status | Tested | Pushed |
|-------|-------------|--------|--------|--------|
| 1 | Scaffold (`pyproject.toml`, LICENSE, namespace layout), shared smoke DUT, Makefile flow: shim, `Makefile.ryusim`, `cocotbext-ryusim-config`, `test_make_flow` including the SIM=icarus forwarding case | done | yes | no |
| 2 | Runner flow: `RyuSim(Runner)`, registration on import, symbol-check error, `test_runner_flow` | pending | no | no |
| 3 | pytest flow: reproduce the `_OPTIONS` load-order hazard in both orders, then the `pytest11` plugin and fix, `test_pytest_flow` in both orders. Stop and revisit if the fix doesn't hold. | pending | no | no |
| 4 | CI: `ci.yml` with the smoke matrix and the conformance job (§7.2) | pending | no | no |
| 5 | README: install, the one-line include change, Runner and pytest usage, the explicit `--cocotb-simulator ryusim` note, the unsupported-construct list, and the cocotb version policy | pending | no | no |
| 6 | Release: create `Seiraiyu/cocotbext-ryusim` on GitHub, configure trusted publishing, run the TestPyPI dry run, publish `0.1.0` | pending | no | no |
