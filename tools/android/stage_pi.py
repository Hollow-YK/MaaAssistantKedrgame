#!/usr/bin/env python3
"""把仓库里的 PI 整理成 MaaFwApp 可直接打包的目录。

MaaFwApp 要求 interface.json 位于 PI 根目录，而本仓库的 PI 根是 assets/，
agent/ 又在仓库根。Android/profile.yaml 的 assets 指向 Android/pi，本脚本
负责生成它：

    Android/pi/
    ├── interface.json          ← assets/interface.json
    ├── resource/               ← assets/resource/
    ├── resource_bilibili/      ← assets/resource_bilibili/
    ├── resource_taptap/        ← assets/resource_taptap/
    ├── agent/                  ← agent/
    └── LICENSE                 ← LICENSE

用法:
    python tools/android/stage_pi.py
    python tools/android/stage_pi.py --dest Android/pi
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DEST = REPO_ROOT / "Android" / "pi"

# 本地开发产物 / 子模块，不随 APK 分发
IGNORE = shutil.ignore_patterns(
    "__pycache__",
    "*.pyc",
    ".venv",
    ".git",
    "MaaCommonAssets",
)

OCR_FILES = ("rec.onnx", "det.onnx", "keys.txt")


def _remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _has_ocr_model(directory: Path) -> bool:
    return all((directory / name).is_file() for name in OCR_FILES)


def _copy_ocr_model(dest: Path) -> None:
    """OCR 模型在 .gitignore 里，CI 需要从 MaaCommonAssets 子模块补。"""
    ocr_dest = dest / "resource" / "model" / "ocr"
    if _has_ocr_model(ocr_dest):
        print(f"[stage] 使用已存在的 OCR 模型: {ocr_dest}")
        return

    source = REPO_ROOT / "assets" / "MaaCommonAssets" / "OCR" / "ppocr_v6" / "small"
    if not _has_ocr_model(source):
        raise SystemExit(
            "找不到 OCR 模型：assets/resource/model/ocr 不完整，"
            "且 assets/MaaCommonAssets 子模块未检出。\n"
            "请先执行：git submodule update --init --recursive"
        )
    shutil.copytree(source, ocr_dest, dirs_exist_ok=True)
    print(f"[stage] 已从 MaaCommonAssets 复制 OCR 模型: {source} -> {ocr_dest}")


def stage(dest: Path) -> None:
    assets = REPO_ROOT / "assets"
    agent = REPO_ROOT / "agent"

    if not (assets / "interface.json").is_file():
        raise SystemExit(f"找不到 PI 入口: {assets / 'interface.json'}")
    if not (agent / "main.py").is_file():
        raise SystemExit(f"找不到 agent 入口: {agent / 'main.py'}")

    _remove(dest)
    dest.mkdir(parents=True)

    shutil.copytree(assets, dest, dirs_exist_ok=True, ignore=IGNORE)
    shutil.copytree(agent, dest / "agent", dirs_exist_ok=True, ignore=IGNORE)

    license_file = REPO_ROOT / "LICENSE"
    if license_file.is_file():
        shutil.copy2(license_file, dest / "LICENSE")

    # assets/config/maa_pi_config.json 是桌面端本机配置（含 adb 路径、设备地址），
    # 不能进 APK；MaaFwApp 运行时会自己生成配置。
    _remove(dest / "config")

    _copy_ocr_model(dest)

    files = [path for path in dest.rglob("*") if path.is_file()]
    size_mb = sum(path.stat().st_size for path in files) / 1048576
    print(f"[stage] PI 已就绪: {dest} ({len(files)} 个文件, {size_mb:.1f} MB)")


def main() -> int:
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8")
            except AttributeError:
                pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dest",
        type=Path,
        default=DEFAULT_DEST,
        help=f"输出目录，默认 {DEFAULT_DEST}",
    )
    args = parser.parse_args()
    stage(args.dest.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
