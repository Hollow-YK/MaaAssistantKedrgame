# -*- coding: utf-8 -*-

import os
import sys
import subprocess
from pathlib import Path

# utf-8
sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

# 获取当前main.py路径并设置上级目录为工作目录
current_file_path = os.path.abspath(__file__)
current_script_dir = os.path.dirname(current_file_path)
project_root_dir = os.path.dirname(current_script_dir)

# 更改CWD到项目根目录
if os.getcwd() != project_root_dir:
    os.chdir(project_root_dir)
print(f"set cwd: {os.getcwd()}")

# 将脚本自身的目录添加到sys.path
if current_script_dir not in sys.path:
    sys.path.insert(0, current_script_dir)

VENV_NAME = ".venv"
VENV_DIR = Path(project_root_dir) / VENV_NAME


# -----
# region 虚拟环境
# -----


def _is_running_in_our_venv():
    in_venv = sys.prefix != sys.base_prefix
    if in_venv:
        print(f"当前在虚拟环境中运行: {sys.prefix}")
    else:
        print(f"当前不在虚拟环境中，使用系统Python: {sys.prefix}")
    return in_venv


def _has_venv_module():
    try:
        import venv  # noqa: F401
        return True
    except ImportError:
        return False


def ensure_venv_and_relaunch_if_needed():
    print(f"检测到系统: {sys.platform}。当前Python解释器: {sys.executable}")

    if _is_running_in_our_venv():
        print(f"已在目标虚拟环境 ({VENV_DIR}) 中运行。")
        return

    # embeddable Python 无 venv 模块，直接就地装依赖跑
    if not _has_venv_module():
        print("当前 Python 不含 venv 模块，跳过虚拟环境，直接就地安装依赖")
        return

    if not VENV_DIR.exists():
        print(f"正在 {VENV_DIR} 创建虚拟环境...")
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", str(VENV_DIR)],
                check=True,
                capture_output=True,
            )
            print("创建成功")
        except subprocess.CalledProcessError as e:
            print(
                f"创建失败: {e.stderr.decode(errors='ignore') if e.stderr else e.stdout.decode(errors='ignore')}"
            )
            print("正在退出")
            sys.exit(1)
        except FileNotFoundError:
            print(
                f"命令 '{sys.executable} -m venv' 未找到。请确保 'venv' 模块可用。"
            )
            print("无法在没有虚拟环境的情况下继续。正在退出。")
            sys.exit(1)

    if sys.platform.startswith("win"):
        python_in_venv = VENV_DIR / "Scripts" / "python.exe"
    else:
        python3_path = VENV_DIR / "bin" / "python3"
        python_path = VENV_DIR / "bin" / "python"
        if python3_path.exists():
            python_in_venv = python3_path
        elif python_path.exists():
            python_in_venv = python_path
        else:
            python_in_venv = python3_path

    if not python_in_venv.exists():
        print(f"在虚拟环境 {python_in_venv} 中未找到Python解释器。")
        print("虚拟环境创建可能失败或虚拟环境结构异常。")
        sys.exit(1)

    print("正在使用虚拟环境Python重新启动")

    try:
        script_abs = current_file_path
        args = sys.argv[1:]
        cmd = [str(python_in_venv), str(script_abs)] + args
        print(f"执行命令: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            cwd=os.getcwd(),
            env=os.environ.copy(),
            check=False,
        )
        sys.exit(result.returncode)

    except Exception as e:
        print(f"在虚拟环境中重新启动脚本失败: {e}")
        sys.exit(1)


# -----
# region 依赖安装
# -----


def install_requirements(req_file="requirements.txt"):
    req_path = Path(project_root_dir) / req_file
    if not req_path.exists():
        print(f"{req_file} 文件不存在于 {req_path.resolve()}")
        return True

    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-r",
        str(req_path),
    ]

    print(f"安装依赖: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=project_root_dir)
    if result.returncode != 0:
        print("警告: 依赖安装失败")
        return False
    print("依赖安装完成")
    return True


def check_and_install_dependencies():
    print("开始安装/更新依赖")
    install_requirements()


# -----
# region 核心业务
# -----


def agent():
    try:
        from maa.agent.agent_server import AgentServer
        from maa.toolkit import Toolkit

        import my_action  # noqa: F401
        import my_reco   # noqa: F401

        Toolkit.init_option("./")

        if len(sys.argv) < 2:
            print("Usage: python main.py <socket_id>")
            print("socket_id is provided by AgentIdentifier.")
            sys.exit(1)

        socket_id = sys.argv[-1]
        print(f"socket_id: {socket_id}")

        AgentServer.start_up(socket_id)
        print("AgentServer启动")
        AgentServer.join()
        AgentServer.shut_down()
        print("AgentServer关闭")

    except ImportError as e:
        print(f"导入模块失败: {e}")
        print("考虑重新配置环境")
        sys.exit(1)
    except Exception as e:
        print(f"agent运行过程中发生异常: {e}")
        raise


# -----
# region 程序入口
# -----


def main():
    ensure_venv_and_relaunch_if_needed()
    check_and_install_dependencies()
    agent()


if __name__ == "__main__":
    main()
