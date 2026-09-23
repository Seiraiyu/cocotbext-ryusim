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
