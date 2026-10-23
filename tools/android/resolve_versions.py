#!/usr/bin/env python3
"""解析 Android 出包要用的 MaaFramework / agent 内核版本。

来源链与 M9A / MaaKEDR 的 tools/android-packaging.mjs 同思路：

1. requirements.txt 的 maafw==X 是目标版本；
2. 去 MaaAgentCoreAndroid 找 *-maafwX 配对的 release；
3. 内核还没发布配对版本时，降级到不高于 X 的最高配对，并输出
   core_fallback=true（APK 内前后端仍同版本，只是比目标旧）；
4. client 侧 MaaFramework .so 取内核同一个 maafw 版本，保证 APK 内前后端一致。

用法:
    python tools/android/resolve_versions.py
    python tools/android/resolve_versions.py --github-output
    python tools/android/resolve_versions.py --offline
    python tools/android/resolve_versions.py \
        --framework v5.14.0 --core 3.13.15-maafw5.14.0
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from check_versions import (
    CORE_RE,
    DEFAULT_CORE,
    DEFAULT_FRAMEWORK,
    DEFAULT_REQUIREMENTS,
    compare_versions,
    normalize_version,
    read_pin,
    version_key,
)

CORE_REPO = os.environ.get("AGENT_CORE_REPO", "AliothMoon/MaaAgentCoreAndroid")
MAAFW_REPO = os.environ.get("MAAFW_REPO", "MaaXYZ/MaaFramework")
DEFAULT_API_BASE = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")


@dataclass(frozen=True)
class Resolution:
    maafw_tag: str
    core_tag: str
    maafw_version: str
    core_fallback: bool


def github_json(url: str, token: str) -> object:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "MAAK-android-packaging",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    if token:
        request.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:300]
        raise SystemExit(f"GitHub API {exc.code}: {url}\n{body}")
    except urllib.error.URLError as exc:
        raise SystemExit(f"无法访问 GitHub API: {url}\n{exc.reason}")


def list_releases(repo: str, token: str, api_base: str) -> list[dict]:
    releases: list[dict] = []
    for page in range(1, 6):
        url = f"{api_base}/repos/{repo}/releases?per_page=100&page={page}"
        batch = github_json(url, token)
        if not isinstance(batch, list):
            raise SystemExit(f"GitHub API 返回异常（{repo} page {page}）")
        releases.extend(item for item in batch if isinstance(item, dict))
        if len(batch) < 100:
            break
    return releases


def core_candidates(releases: list[dict]) -> list[tuple[str, str]]:
    """返回 [(normalized maafw 版本, core tag)]，跳过 draft。"""
    candidates: list[tuple[str, str]] = []
    for release in releases:
        if release.get("draft"):
            continue
        tag = str(release.get("tag_name", "")).strip()
        match = CORE_RE.match(tag)
        if match is None:
            continue
        candidates.append((normalize_version(match.group(2)), tag))
    return candidates


def select_core(candidates: list[tuple[str, str]], pin: str) -> tuple[str, str, bool]:
    exact = [item for item in candidates if item[0] == pin]
    if exact:
        version, tag = exact[0]
        return tag, version, False

    lower = [item for item in candidates if compare_versions(item[0], pin) < 0]
    if not lower:
        available = ", ".join(sorted({item[0] for item in candidates})) or "<none>"
        raise SystemExit(
            f"没有找到 maafw {pin} 的配对内核，也没有可降级的更旧版本。可用: {available}"
        )
    version, tag = max(lower, key=lambda item: version_key(item[0]))
    return tag, version, True


def select_framework(version: str, releases: list[dict]) -> str:
    for release in releases:
        if release.get("draft"):
            continue
        tag = str(release.get("tag_name", "")).strip()
        if normalize_version(tag) == version:
            return tag
    tag = f"v{version}"
    print(
        f"[resolve] WARN: MaaFramework release 里没有 {tag}，按约定直接使用该 tag",
        file=sys.stderr,
    )
    return tag


def _parse_core(core: str) -> str:
    match = CORE_RE.match(core.strip())
    if match is None:
        raise SystemExit(
            f"AGENT_CORE_TAG 格式应为 <CPython 版本>-maafw<MaaFW 版本>，实际: {core}"
        )
    return normalize_version(match.group(2))


def resolve(
    requirements: Path,
    *,
    framework: str = "",
    core: str = "",
    token: str = "",
    api_base: str = DEFAULT_API_BASE,
    offline: bool = False,
) -> Resolution:
    pin = normalize_version(read_pin(requirements))

    if framework or core:
        if not (framework and core):
            raise SystemExit("--framework 与 --core 必须同时提供，避免前后端版本错配")
        core_version = _parse_core(core)
        framework_version = normalize_version(framework)
        if framework_version != core_version:
            raise SystemExit(
                f"--framework {framework} 与 --core {core} 的 maafw 版本不一致"
            )
        return Resolution(
            maafw_tag=framework,
            core_tag=core,
            maafw_version=core_version,
            core_fallback=compare_versions(core_version, pin) < 0,
        )

    if offline:
        core_tag = os.environ.get("AGENT_CORE_TAG", DEFAULT_CORE)
        core_version = _parse_core(core_tag)
        framework_tag = os.environ.get("MAA_FRAMEWORK_VERSION", "") or f"v{core_version}"
        if normalize_version(framework_tag) != core_version:
            raise SystemExit(
                f"MAA_FRAMEWORK_VERSION={framework_tag} 与 AGENT_CORE_TAG={core_tag} 不一致"
            )
        if compare_versions(core_version, pin) != 0:
            print(
                f"[resolve] WARN: 离线模式使用 {core_version}，"
                f"与 requirements.txt 的 maafw {pin} 不同",
                file=sys.stderr,
            )
        return Resolution(
            maafw_tag=framework_tag,
            core_tag=core_tag,
            maafw_version=core_version,
            core_fallback=compare_versions(core_version, pin) < 0,
        )

    candidates = core_candidates(list_releases(CORE_REPO, token, api_base))
    core_tag, core_version, core_fallback = select_core(candidates, pin)
    maafw_tag = select_framework(
        core_version, list_releases(MAAFW_REPO, token, api_base)
    )
    return Resolution(
        maafw_tag=maafw_tag,
        core_tag=core_tag,
        maafw_version=core_version,
        core_fallback=core_fallback,
    )


def emit(resolution: Resolution, github_output: bool) -> None:
    lines = [
        f"maafw_tag={resolution.maafw_tag}",
        f"core_tag={resolution.core_tag}",
        f"maafw_version={resolution.maafw_version}",
        f"core_fallback={'true' if resolution.core_fallback else 'false'}",
    ]
    for line in lines:
        print(line)
    if github_output:
        output = os.environ.get("GITHUB_OUTPUT")
        if not output:
            raise SystemExit("--github-output 需要 GITHUB_OUTPUT 环境变量")
        with open(output, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


def main() -> int:
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8")
            except AttributeError:
                pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", type=Path, default=DEFAULT_REQUIREMENTS)
    parser.add_argument(
        "--framework",
        default="",
        help=f"覆盖 MaaFramework tag（与 --core 同时提供；默认 {DEFAULT_FRAMEWORK}）",
    )
    parser.add_argument(
        "--core",
        default="",
        help=f"覆盖 agent 内核 tag（与 --framework 同时提供；默认 {DEFAULT_CORE}）",
    )
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", ""),
        help="GitHub token，避免 CI 触发 API 限流",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="不访问 GitHub API，改用环境变量 / 内置默认版本",
    )
    parser.add_argument(
        "--github-output",
        action="store_true",
        help="把 key=value 追加到 $GITHUB_OUTPUT",
    )
    args = parser.parse_args()

    resolution = resolve(
        args.requirements.resolve(),
        framework=args.framework,
        core=args.core,
        token=args.token,
        api_base=args.api_base.rstrip("/"),
        offline=args.offline,
    )
    emit(resolution, args.github_output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
