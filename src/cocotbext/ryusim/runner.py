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
