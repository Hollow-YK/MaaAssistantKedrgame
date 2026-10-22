#!/usr/bin/env python3
"""本地一键构建 Android APK（MaaFwApp 外壳）。

流程：
  1. 校验 requirements / MaaFramework / agent 内核版本，以及 MaaFwApp 子模块
  2. 生成 Android/pi（stage_pi.py）
  3. 铺 MaaFramework Android .so（MaaFwApp/scripts/setup_maa_framework.py）
  4. 构建 agent Python 运行时（MaaFwApp/scripts/build_agent_bundle.py）
  5. 写 local.properties
  6. 执行 Gradle assembleDebug / assembleRelease

前置条件：
  - MaaFwApp 子模块已初始化（git submodule update --init --recursive）
  - JDK 17+（Gradle 9.4 需要；CI 用 25）
  - Android SDK（设置 ANDROID_HOME 或 ANDROID_SDK_ROOT）
  - Android NDK + CMake 3.22.1（CI 用 29.0.13113456；本机可用 BUILD_NDK_VERSION 覆盖）
  - Python 3.13+（与 MaaAgentCoreAndroid 的 CPython 版本无关，仅用于构建脚本）

用法：
    python tools/android/build_apk.py --assemble debug
    python tools/android/build_apk.py --assemble release --abi arm64-v8a --abi x86_64
    python tools/android/build_apk.py --assemble release --resolve-versions

release 签名读取环境变量 KEYSTORE_PATH / KEYSTORE_PASSWORD / KEY_ALIAS /
KEY_PASSWORD；未提供时 MaaFwApp 会打出未签名包。
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

# 以脚本方式运行（python tools/android/build_apk.py）时，Python 会把本目录放进
# sys.path，因此可以直接导入同目录的辅助脚本。
from check_versions import check as check_versions
from resolve_versions import resolve as resolve_versions
from stage_pi import DEFAULT_DEST as DEFAULT_PI_DIR
from stage_pi import stage as stage_pi
from write_local_properties import write as write_local_properties

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = REPO_ROOT / "Android" / "MaaFwApp"
AGENT_DIST = REPO_ROOT / "Android" / "agent-dist"
ANDROID_REQUIREMENTS = REPO_ROOT / "Android" / "requirements-android.txt"
REQUIREMENTS = REPO_ROOT / "requirements.txt"

DEFAULT_MAAFW_TAG = os.environ.get("MAA_FRAMEWORK_VERSION", "v5.14.0")
DEFAULT_CORE_TAG = os.environ.get("AGENT_CORE_TAG", "3.13.15-maafw5.14.0")


def run(command: list[str], cwd: Path) -> None:
    printable = " ".join(shlex.quote(str(part)) for part in command)
    print(f"[run] (cd {cwd}) {printable}")
    subprocess.run([str(part) for part in command], cwd=str(cwd), check=True)


def default_abis(assemble: str) -> list[str]:
    # debug 只出 arm64，省一半下载 / 编译时间；release 出双 ABI 通用包。
    return ["arm64-v8a"] if assemble == "debug" else ["arm64-v8a", "x86_64"]


def build(args: argparse.Namespace) -> int:
    abis = args.abi or default_abis(args.assemble)

    if not (APP_DIR / "build.gradle.kts").is_file():
        raise SystemExit(
            f"MaaFwApp 子模块未初始化: {APP_DIR}\n"
            "请先执行: git submodule update --init --recursive"
        )

    maafw_tag = args.maafw_tag
    core_tag = args.core_tag
    core_fallback = args.allow_core_fallback
    if args.resolve_versions:
        resolution = resolve_versions(
            REQUIREMENTS,
            token=os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", ""),
            api_base=os.environ.get("GITHUB_API_URL", "https://api.github.com"),
        )
        maafw_tag = resolution.maafw_tag
        core_tag = resolution.core_tag
        core_fallback = core_fallback or resolution.core_fallback
        print(
            f"[versions] resolved: MaaFramework={maafw_tag} "
            f"core={core_tag} fallback={str(resolution.core_fallback).lower()}"
        )

    check_versions(
        REQUIREMENTS,
        maafw_tag,
        core_tag,
        maafwapp_ref=args.maafwapp_ref,
        allow_core_fallback=core_fallback,
    )

    if args.check_only:
        print("[done] 仅校验版本与子模块，不构建")
        return 0

    if not args.skip_stage:
        stage_pi(DEFAULT_PI_DIR)
    if not (DEFAULT_PI_DIR / "interface.json").is_file():
        raise SystemExit(
            f"PI 暂存目录不完整: {DEFAULT_PI_DIR}（先运行 tools/android/stage_pi.py）"
        )

    if not args.skip_framework:
        setup = APP_DIR / "scripts" / "setup_maa_framework.py"
        if not setup.is_file():
            raise SystemExit(f"找不到 {setup}")
        for abi in abis:
            run(
                [
                    sys.executable,
                    str(setup),
                    "--tag",
                    maafw_tag,
                    "--abi",
                    abi,
                ],
                cwd=APP_DIR,
            )

    if not args.skip_agent:
        bundle_script = APP_DIR / "scripts" / "build_agent_bundle.py"
        if not bundle_script.is_file():
            raise SystemExit(f"找不到 {bundle_script}")
        if not ANDROID_REQUIREMENTS.is_file():
            raise SystemExit(f"找不到 {ANDROID_REQUIREMENTS}")

        # 配方里的 agent.abi 缺省为 "*"，会打包 agent-dist 下所有 ABI。
        # 切换 debug/release 时清掉上一次留下的其它 ABI，避免 debug 包带上
        # 没有对应 jniLibs 的运行时。
        if AGENT_DIST.is_dir():
            stale = [
                child
                for child in AGENT_DIST.iterdir()
                if child.is_dir() and child.name not in abis
            ]
            for child in stale:
                print(f"[agent] 清理不属于本次 ABI 的运行时: {child}")
                shutil.rmtree(child)

        command = [
            sys.executable,
            str(bundle_script),
            "--out",
            str(AGENT_DIST),
            "--core-tag",
            core_tag,
            "--requirements",
            str(ANDROID_REQUIREMENTS),
        ]
        for abi in abis:
            command += ["--abi", abi]
        run(command, cwd=APP_DIR)

    write_local_properties(APP_DIR, args.assemble, abis)

    gradlew = APP_DIR / ("gradlew.bat" if os.name == "nt" else "gradlew")
    if not gradlew.is_file():
        raise SystemExit(f"找不到 Gradle wrapper: {gradlew}")
    task = "assembleDebug" if args.assemble == "debug" else "assembleRelease"
    if os.name == "nt":
        gradle_command = ["cmd", "/c", str(gradlew), "clean", task]
    else:
        gradlew.chmod(gradlew.stat().st_mode | 0o111)
        gradle_command = [str(gradlew), "clean", task]
    run(gradle_command, cwd=APP_DIR)

    apk_dir = APP_DIR / "app" / "build" / "outputs" / "apk" / args.assemble
    apks = sorted(apk_dir.glob("*.apk"))
    if not apks:
        raise SystemExit(f"Gradle 完成但没有找到 APK: {apk_dir}")
    print("[done] 产物:")
    for apk in apks:
        print(f"  {apk}  ({apk.stat().st_size / 1048576:.1f} MB)")
    return 0


def main() -> int:
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8")
            except AttributeError:
                pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assemble", choices=["debug", "release"], default="debug")
    parser.add_argument(
        "--abi",
        action="append",
        default=[],
        help="只构建指定 ABI，可重复；默认 debug=arm64-v8a，release=arm64-v8a + x86_64",
    )
    parser.add_argument("--maafw-tag", default=DEFAULT_MAAFW_TAG)
    parser.add_argument("--core-tag", default=DEFAULT_CORE_TAG)
    parser.add_argument(
        "--maafwapp-ref",
        default=os.environ.get("MAAFWAPP_REF", ""),
        help="额外断言 MaaFwApp 子模块 commit（默认取 MAAFWAPP_REF）",
    )
    parser.add_argument(
        "--resolve-versions",
        action="store_true",
        help="用 resolve_versions.py 从 requirements.txt 解析 MaaFramework / 内核版本",
    )
    parser.add_argument(
        "--allow-core-fallback",
        action="store_true",
        help="允许内核版本低于 requirements.txt 的 maafw 钉版",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="只做版本 / 子模块校验，不执行构建",
    )
    parser.add_argument("--skip-stage", action="store_true", help="跳过 Android/pi 生成")
    parser.add_argument(
        "--skip-framework", action="store_true", help="跳过 MaaFramework .so 铺设"
    )
    parser.add_argument(
        "--skip-agent", action="store_true", help="跳过 agent Python 运行时构建"
    )
    args = parser.parse_args()

    return build(args)


if __name__ == "__main__":
    sys.exit(main())
