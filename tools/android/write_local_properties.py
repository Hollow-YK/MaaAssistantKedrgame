#!/usr/bin/env python3
"""生成 MaaFwApp 的 local.properties。

MaaFwApp 通过 local.properties 的 pi.profile 找到打包配方，通过 sdk.dir
找到 Android SDK；build.debugAbi / build.releaseAbi 用来裁剪 ABI。

用法:
    python tools/android/write_local_properties.py --assemble debug
    python tools/android/write_local_properties.py --assemble release \
        --abi arm64-v8a --abi x86_64
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_APP_DIR = REPO_ROOT / "Android" / "MaaFwApp"
PROFILE = REPO_ROOT / "Android" / "profile.yaml"


def write(
    app_dir: Path,
    assemble: str,
    abis: list[str],
) -> Path:
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if not sdk:
        raise SystemExit(
            "未设置 ANDROID_HOME / ANDROID_SDK_ROOT。\n"
            "请先安装 Android SDK，并把环境变量指向 SDK 根目录。"
        )
    if not (app_dir / "gradlew").is_file():
        raise SystemExit(
            f"MaaFwApp 未就绪: {app_dir}（先执行 git submodule update --init --recursive）"
        )
    if not PROFILE.is_file():
        raise SystemExit(f"找不到打包配方: {PROFILE}")

    lines = [
        f"sdk.dir={Path(sdk).resolve().as_posix()}",
        f"pi.profile={PROFILE.resolve().as_posix()}",
    ]
    if abis:
        key = "build.debugAbi" if assemble == "debug" else "build.releaseAbi"
        lines.append(f"{key}={','.join(abis)}")

    target = app_dir / "local.properties"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[local.properties] {target}")
    for line in lines:
        print(f"  {line}")
    return target


def main() -> int:
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8")
            except AttributeError:
                pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-dir", type=Path, default=DEFAULT_APP_DIR)
    parser.add_argument("--assemble", choices=["debug", "release"], default="debug")
    parser.add_argument(
        "--abi",
        action="append",
        default=[],
        help="只打指定 ABI，可重复；不写则用 MaaFwApp 默认（两个 ABI）",
    )
    args = parser.parse_args()

    write(args.app_dir.resolve(), args.assemble, args.abi)
    return 0


if __name__ == "__main__":
    sys.exit(main())
