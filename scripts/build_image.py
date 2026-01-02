#!/usr/bin/env python3
from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def run(cmd: list[str], *, cwd: Path) -> None:
    print("+", shlex.join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    load_env_file(root / ".env")

    image = os.environ.get("IMAGE", "drguptavivek/central-nginx-vg-base")
    tag = os.environ.get("TAG", "6.0.1")
    crs_tag = os.environ.get("CRS_TAG", "v4.21.0")
    platforms = os.environ.get("PLATFORMS", "linux/amd64,linux/arm64")
    push = os.environ.get("PUSH", "0")
    output_flag = "--push" if push == "1" else "--load"

    if output_flag == "--load" and "," in platforms:
        raise SystemExit(
            "Refusing to use --load with multiple platforms. "
            "Set PLATFORMS to a single platform (e.g. linux/arm64) or set PUSH=1."
        )

    cmd = [
        "docker",
        "buildx",
        "build",
        "--platform",
        platforms,
        "--build-arg",
        f"CRS_TAG={crs_tag}",
        "-f",
        str(root / "Dockerfile"),
        "-t",
        f"{image}:{tag}",
        output_flag,
        str(root),
    ]

    print(f"Building {image}:{tag}")
    print(f"Platforms: {platforms}")
    print(f"CRS_TAG: {crs_tag}")
    print(f"Output: {output_flag}")
    run(cmd, cwd=root)


if __name__ == "__main__":
    main()

