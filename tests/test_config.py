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
