#!/usr/bin/env python3
"""校验 Android 出包的版本对齐与 MaaFwApp 子模块状态。

APK 里的 client 原生库（jniLibs）与 agent 内核自带的 Python 绑定必须同版本，
否则前后端协议可能不一致；requirements.txt 的 maafw 钉版是目标版本。内核还没
发布配对版本时，允许降级到不高于目标版本的最近配对（由 resolve_versions.py
决定，对应 --allow-core-fallback），此时 APK 内前后端仍然一致。

MaaFwApp 以 submodule 固定在具体 commit（gitlink），构建前还要确认 submodule
已初始化、检出的 commit 与索引一致、且没有未提交的修改。

用法:
    python tools/android/check_versions.py
    python tools/android/check_versions.py \
        --framework v5.14.0 --core 3.13.15-maafw5.14.0
    python tools/android/check_versions.py --allow-core-fallback
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REQUIREMENTS = REPO_ROOT / "requirements.txt"
DEFAULT_FRAMEWORK = os.environ.get("MAA_FRAMEWORK_VERSION", "v5.14.0")
DEFAULT_CORE = os.environ.get("AGENT_CORE_TAG", "3.13.15-maafw5.14.0")
MAAFWAPP_PATH = "Android/MaaFwApp"

PIN_RE = re.compile(r"^\s*maafw\s*==\s*([^\s;#]+)", re.MULTILINE)
CORE_RE = re.compile(r"^(\d[\w.]*)-maafw([A-Za-z0-9][A-Za-z0-9.+-]*)$")


def normalize_version(text: str) -> str:
    """把 v5.14.0 / 5.14.0 / 5.15.0-beta.1 / 5.15.0b1 归一到同一 key。"""
    value = text.strip().lower().removeprefix("v")
    match = re.match(r"^(\d+(?:\.\d+)*)(.*)$", value)
    if match is None:
        return value
    release, suffix = match.groups()
    suffix = suffix.lstrip("-._")
    suffix = re.sub(r"^(alpha|a)[-_.]?", "a", suffix)
    suffix = re.sub(r"^(beta|b)[-_.]?", "b", suffix)
    suffix = re.sub(r"^(preview|pre|rc|c)[-_.]?", "rc", suffix)
    # 5.15.0-beta.1 与 5.15.0b1 是同一个版本，统一去掉预发布号前的分隔符
    suffix = re.sub(r"^([a-z]+)[-_.]?(\d+)$", r"\1\2", suffix)
    return release + suffix


def version_key(normalized: str) -> tuple[tuple[int, ...], int, str]:
    """把 normalize_version 的结果转成可比较的 key。

    正式版排在同一个 release 的预发布版之后；预发布后缀按 (alpha, beta, rc)
    排序，再比数字，避免 b2 > b10 这种字符串比较错误。
    """
    match = re.match(r"^(\d+(?:\.\d+)*)(.*)$", normalized)
    if match is None:
        return ((), 0, normalized)
    release, suffix = match.groups()
    release_key = tuple(int(part) for part in release.split("."))
    if not suffix:
        return (release_key, 1, "")
    prefix = re.match(r"^[a-z]+", suffix)
    rank = {"a": 0, "b": 1, "rc": 2}.get(prefix.group(0), 3) if prefix else 3
    number = re.search(r"\d+", suffix)
    return (release_key, 0, f"{rank:02d}{int(number.group(0)) if number else 0:08d}")


def compare_versions(left: str, right: str) -> int:
    """比较两个 normalize_version 后的版本，返回 -1 / 0 / 1。"""
    left_key = version_key(left)
    right_key = version_key(right)
    # release 段补齐到相同长度，避免 5.14 与 5.14.0 被判为不同
    width = max(len(left_key[0]), len(right_key[0]))
    left_release = left_key[0] + (0,) * (width - len(left_key[0]))
    right_release = right_key[0] + (0,) * (width - len(right_key[0]))
    if left_release != right_release:
        return 1 if left_release > right_release else -1
    if left_key[1:] != right_key[1:]:
        return 1 if left_key[1:] > right_key[1:] else -1
    return 0


def read_pin(requirements: Path) -> str:
    if not requirements.is_file():
        raise SystemExit(f"requirements.txt 不存在: {requirements}")
    match = PIN_RE.search(requirements.read_text(encoding="utf-8"))
    if match is None:
        raise SystemExit(
            f"{requirements} 里没有 maafw==X 钉版；Android 出包需要精确版本才能配对内核"
        )
    return match.group(1)


def check_maafwapp(repo_root: Path, expected_ref: str = "") -> str:
    """确认 MaaFwApp 子模块已初始化、固定在索引记录的 commit 且没有改动。"""
    path = repo_root / MAAFWAPP_PATH
    if not (path / "build.gradle.kts").is_file():
        raise SystemExit(
            f"MaaFwApp 子模块未初始化: {path}\n"
            "请先执行: git submodule update --init --recursive"
        )

    result = subprocess.run(
        ["git", "-C", str(repo_root), "submodule", "status", "--", MAAFWAPP_PATH],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise SystemExit(f"无法读取 MaaFwApp 子模块状态: {result.stderr.strip()}")

    # 保留行首的状态字符（空格 = 正常，- = 未初始化，+ = 与索引不一致）
    line = result.stdout.rstrip("\r\n")
    match = re.match(r"^([ +\-U])([0-9a-f]{40})\s", line)
    if match is None:
        raise SystemExit(f"MaaFwApp 子模块状态异常: {line or '<empty>'}")
    state, sha = match.groups()

    if state == "-":
        raise SystemExit(
            f"MaaFwApp 子模块未检出（{sha}）。\n"
            "请先执行: git submodule update --init --recursive"
        )
    if state == "+":
        raise SystemExit(
            "MaaFwApp 子模块检出的 commit 与索引不一致（可能被切到了别的版本）。\n"
            "请执行: git submodule update -- Android/MaaFwApp"
        )
    if state == "U":
        raise SystemExit("MaaFwApp 子模块存在冲突，请先解决后再出包。")
    if expected_ref and sha != expected_ref:
        raise SystemExit(
            f"MaaFwApp 子模块 commit 与声明的 MAAFWAPP_REF 不一致：\n"
            f"  期望: {expected_ref}\n  实际: {sha}"
        )

    dirty = subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "status",
            "--porcelain",
            "--untracked-files=no",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if dirty.stdout.strip():
        raise SystemExit(
            "MaaFwApp 子模块有未提交的修改，出包不可复现：\n" + dirty.stdout.strip()
        )

    version = line.split("(", 1)[1].rstrip(")") if "(" in line else "unknown"
    print(f"[versions] MaaFwApp        : {sha} ({version})")
    return sha


def check(
    requirements: Path,
    framework: str,
    core: str,
    *,
    maafwapp_ref: str = "",
    allow_core_fallback: bool = False,
    repo_root: Path = REPO_ROOT,
) -> None:
    pin = read_pin(requirements)
    core_match = CORE_RE.match(core.strip())
    if core_match is None:
        raise SystemExit(
            f"AGENT_CORE_TAG 格式应为 <CPython 版本>-maafw<MaaFW 版本>，实际: {core}"
        )
    core_maafw = core_match.group(2)

    expected = normalize_version(pin)
    actual_framework = normalize_version(framework)
    actual_core = normalize_version(core_maafw)

    print("[versions] requirements.txt : maafw==" + pin)
    print("[versions] MaaFramework     : " + framework)
    print("[versions] agent core       : " + core)
    print("[versions] normalized       : " + expected)
    check_maafwapp(repo_root, maafwapp_ref)

    problems: list[str] = []
    # APK 内部一致性优先：client .so 必须与内核绑定同版本
    if actual_framework != actual_core:
        problems.append(
            f"MaaFramework={framework} 与 agent 内核 {core} 的 maafw 版本不一致"
        )
    if actual_core != expected:
        if allow_core_fallback and compare_versions(actual_core, expected) < 0:
            print(
                f"[versions] WARN: 内核尚未发布 maafw {pin} 的配对版本，"
                f"降级使用 {core_maafw}（APK 内前后端仍同版本）"
            )
        else:
            problems.append(
                f"AGENT_CORE_TAG={core} 的内核绑定（{core_maafw}）与 requirements.txt 的 "
                f"maafw=={pin} 不一致"
            )

    if problems:
        raise SystemExit(
            "[versions] 版本未对齐：\n  - "
            + "\n  - ".join(problems)
            + "\n请检查 tools/android/resolve_versions.py 的解析结果，或同步 "
            "requirements.txt 与 MaaFramework / 内核版本。"
        )
    print("[versions] OK：版本一致")


def main() -> int:
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8")
            except AttributeError:
                pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", type=Path, default=DEFAULT_REQUIREMENTS)
    parser.add_argument("--framework", default=DEFAULT_FRAMEWORK)
    parser.add_argument("--core", default=DEFAULT_CORE)
    parser.add_argument(
        "--maafwapp-ref",
        default=os.environ.get("MAAFWAPP_REF", ""),
        help="额外断言 MaaFwApp 子模块的 commit（默认取 MAAFWAPP_REF）",
    )
    parser.add_argument(
        "--allow-core-fallback",
        action="store_true",
        help="允许内核版本低于 requirements.txt 的 maafw 钉版（由版本解析器决定）",
    )
    args = parser.parse_args()

    check(
        args.requirements.resolve(),
        args.framework,
        args.core,
        maafwapp_ref=args.maafwapp_ref,
        allow_core_fallback=args.allow_core_fallback,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
