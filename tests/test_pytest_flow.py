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
