#!/usr/bin/env python3
"""Dependency-light repository integrity checker."""
from __future__ import annotations

import ast
import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def check_python() -> int:
    files = list(ROOT.rglob("*.py"))
    for path in files:
        ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    return len(files)


def check_xml() -> int:
    files = list(ROOT.rglob("package.xml"))
    for path in files:
        ET.parse(path)
    return len(files)


def check_yaml() -> int:
    files = list((ROOT / "config").rglob("*.yaml")) + list((ROOT / "training/configs").rglob("*.yaml")) + list((ROOT / "ros2_ws/src/smartcar_bringup/config").rglob("*.yaml"))
    for path in files:
        with path.open("r", encoding="utf-8") as stream:
            yaml.safe_load(stream)
    return len(files)


def check_models() -> int:
    count = 0
    for line in (ROOT / "models/SHA256SUMS").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        digest = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        if digest != expected:
            raise RuntimeError(f"Checksum mismatch: {relative}")
        count += 1
    return count


def main() -> None:
    print(f"python={check_python()} xml={check_xml()} yaml={check_yaml()} models={check_models()}")
    print("project integrity: OK")


if __name__ == "__main__":
    main()

