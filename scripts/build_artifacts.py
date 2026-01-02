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

    dockerfile = os.environ.get("MODULES_DOCKERFILE", str(root / "Dockerfile.modules"))
    platforms_raw = os.environ.get("PLATFORMS", "linux/arm64 linux/amd64")
    platforms = [p for p in platforms_raw.split() if p]

    print(f"Using Dockerfile.modules: {dockerfile}")
    print(f"Platforms: {', '.join(platforms)}")

    for platform in platforms:
        if not platform.startswith("linux/"):
            raise SystemExit(f"Unsupported platform '{platform}'. Expected like 'linux/amd64'.")
        arch = platform.split("/", 1)[1]
        print(f"\n== {platform} ==")

        out_headers = root / "vg-modules" / f"linux-{arch}" / "out-headers-more"
        out_modsec = root / "vg-modules" / f"linux-{arch}" / "out-modsecurity"
        out_headers.mkdir(parents=True, exist_ok=True)
        out_modsec.mkdir(parents=True, exist_ok=True)

        run(
            [
                "docker",
                "buildx",
                "build",
                "--no-cache",
                "--platform",
                platform,
                "-f",
                dockerfile,
                "--target",
                "out-headers-more",
                "--output",
                f"type=local,dest={out_headers}",
                str(root),
            ],
            cwd=root,
        )

        run(
            [
                "docker",
                "buildx",
                "build",
                "--no-cache",
                "--platform",
                platform,
                "-f",
                dockerfile,
                "--target",
                "out-modsecurity",
                "--output",
                f"type=local,dest={out_modsec}",
                str(root),
            ],
            cwd=root,
        )

    print(f"\nArtifacts exported under {root / 'vg-modules'}")


if __name__ == "__main__":
    main()

