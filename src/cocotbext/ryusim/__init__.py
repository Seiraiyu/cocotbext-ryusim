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
