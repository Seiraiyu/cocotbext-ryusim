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
