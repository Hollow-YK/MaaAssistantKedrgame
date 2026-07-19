from pathlib import Path

import json
import os
import re
import shutil
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
tools_dir = os.path.dirname(script_dir)
sys.path.append(tools_dir)

from configure import configure_ocr_model


def load_json_with_comments(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    text = re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)
    lines = []
    for line in text.split("\n"):
        in_string = False
        for i, ch in enumerate(line):
            if ch == '"' and (i == 0 or line[i - 1] != "\\"):
                in_string = not in_string
            elif (
                ch == "/" and i + 1 < len(line) and line[i + 1] == "/" and not in_string
            ):
                line = line[:i].rstrip()
                break
        lines.append(line)
    return json.loads("\n".join(lines))


working_dir = Path(__file__).parent.parent.parent
install_path = working_dir / "install-mfaa"
mfaa_path = working_dir / "MFAA"
version = len(sys.argv) > 1 and sys.argv[1] or "v0.0.1"

if len(sys.argv) < 4:
    print("Usage: python install_mfaa.py <version> <os> <arch>")
    print("Example: python install_mfaa.py v1.0.0 win x86_64")
    sys.exit(1)

os_name = sys.argv[2]
arch = sys.argv[3]


def get_dotnet_platform_tag():
    platform_tags = {
        ("win", "x86_64"): "win-x64",
        ("win", "aarch64"): "win-arm64",
        ("macos", "x86_64"): "osx-x64",
        ("macos", "aarch64"): "osx-arm64",
        ("linux", "x86_64"): "linux-x64",
        ("linux", "aarch64"): "linux-arm64",
    }

    platform_tag = platform_tags.get((os_name, arch))
    if platform_tag is None:
        raise ValueError(f"Unsupported target platform: {os_name}-{arch}")
    return platform_tag


def get_entrypoint_candidates():
    if os_name == "win":
        return ["MFAAvalonia.exe", "MFAAvalonia"]
    return ["MFAAvalonia", "MFAAvalonia.exe"]


def get_target_entrypoint_name():
    return "MAK.exe" if os_name == "win" else "MAK"


def find_mfaa_entrypoint():
    entrypoints = []
    for candidate in get_entrypoint_candidates():
        entrypoints.extend(
            path for path in mfaa_path.rglob(candidate) if path.is_file()
        )

    if len(entrypoints) != 1:
        raise FileNotFoundError(
            f"Expected exactly one MFAAvalonia entrypoint under {mfaa_path}, "
            f"found {len(entrypoints)}."
        )
    return entrypoints[0]


def install_mfaa_runtime():
    source_entrypoint = find_mfaa_entrypoint()
    runtime_dir = source_entrypoint.parent
    install_path.mkdir(parents=True, exist_ok=True)

    for source in runtime_dir.iterdir():
        destination = install_path / source.name
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination)

    packaged_entrypoint = install_path / source_entrypoint.name
    target_entrypoint = install_path / get_target_entrypoint_name()
    if not packaged_entrypoint.is_file():
        raise FileNotFoundError(
            f"MFAAvalonia entrypoint was not copied to package root: {packaged_entrypoint}"
        )
    packaged_entrypoint.rename(target_entrypoint)


def install_deps():
    deps_bin = working_dir / "deps" / "bin"
    if not deps_bin.exists():
        raise FileNotFoundError('Please download MaaFramework to "deps" first.')

    platform_tag = get_dotnet_platform_tag()
    shutil.copytree(
        deps_bin,
        install_path / "runtimes" / platform_tag / "native",
        ignore=shutil.ignore_patterns(
            "*MaaDbgControlUnit*",
            "*MaaThriftControlUnit*",
            "*MaaRpc*",
            "*MaaHttp*",
            "plugins",
            "*.node",
            "*MaaPiCli*",
        ),
        dirs_exist_ok=True,
    )
    shutil.copytree(
        working_dir / "deps" / "share" / "MaaAgentBinary",
        install_path / "libs" / "MaaAgentBinary",
        dirs_exist_ok=True,
    )
    shutil.copytree(
        deps_bin / "plugins",
        install_path / "plugins" / platform_tag,
        dirs_exist_ok=True,
    )


def install_resource():
    configure_ocr_model()

    shutil.copytree(
        working_dir / "assets" / "resource",
        install_path / "resource",
        dirs_exist_ok=True,
    )

    for resource_name in ["resource_bilibili", "resource_taptap"]:
        source = working_dir / "assets" / resource_name
        if source.exists():
            shutil.copytree(
                source,
                install_path / resource_name,
                dirs_exist_ok=True,
            )

    shutil.copy2(working_dir / "assets" / "interface.json", install_path)

    interface = load_json_with_comments(install_path / "interface.json")
    interface["version"] = version.lstrip("v")
    interface["title"] = f"MAK {version} | 雪松小助手"

    with open(install_path / "interface.json", "w", encoding="utf-8") as f:
        json.dump(interface, f, ensure_ascii=False, indent=4)


def install_chores():
    for file in ["README.md", "LICENSE", "requirements.txt"]:
        source = working_dir / file
        if source.exists():
            shutil.copy2(source, install_path)


def install_agent():
    shutil.copytree(
        working_dir / "agent",
        install_path / "agent",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        dirs_exist_ok=True,
    )

    interface = load_json_with_comments(install_path / "interface.json")
    child_exec = {
        "win": r"./python/python.exe",
        "macos": r"./python/bin/python3",
        "linux": r"python3",
    }[os_name]
    interface["agent"]["child_exec"] = child_exec
    interface["agent"]["child_args"] = ["-u", r"./agent/main.py"]

    with open(install_path / "interface.json", "w", encoding="utf-8") as f:
        json.dump(interface, f, ensure_ascii=False, indent=4)


def verify_package():
    platform_tag = get_dotnet_platform_tag()
    required_paths = [
        install_path / get_target_entrypoint_name(),
        install_path / "interface.json",
        install_path / "agent" / "main.py",
        install_path / "runtimes" / platform_tag / "native",
        install_path / "libs" / "MaaAgentBinary",
        install_path / "plugins" / platform_tag,
    ]
    missing_paths = [str(path) for path in required_paths if not path.exists()]
    if missing_paths:
        raise FileNotFoundError(
            "MFAA package is missing required paths:\n" + "\n".join(missing_paths)
        )


if __name__ == "__main__":
    install_mfaa_runtime()
    install_deps()
    install_resource()
    install_chores()
    install_agent()
    verify_package()

    print(f"Install MFAA to {install_path} successfully.")
