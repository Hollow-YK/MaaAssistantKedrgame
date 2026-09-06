from __future__ import annotations

import traceback
from typing import Any

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

from .general import log_message, parse_params

# agent 进程由 MaaFW 按任务逐次启动，进程内仅存在单一 tasker；
# 此模块级变量天然限定在单次任务生命周期内，无跨任务干扰风险。
_remaining: int | None = None


def _to_int(value: Any) -> int | None:
    """转换为 int；bool 与非数值返回 None"""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


@AgentServer.custom_action("InitPVPBattleCount")
class InitPVPBattleCount(CustomAction):
    """
    参数：
    - target_count: 剩余战斗次数（必填，整数或可转换为整数的字符串）
    """

    def run(self, context: Context, argv: CustomAction.RunArg) -> CustomAction.RunResult:
        try:
            return self._run(context, argv)
        except Exception:
            # 异常必须显式返回失败，否则会被 ctypes 静默忽略导致误判成功
            traceback.print_exc()
            return CustomAction.RunResult(success=False)

    def _run(self, context: Context, argv: CustomAction.RunArg) -> CustomAction.RunResult:
        params = parse_params(argv.custom_action_param)

        target = _to_int(params.get("target_count"))
        if target is None:
            log_message(f"[PVP] InitPVPBattleCount: target_count 必须是整数，得到: {params.get('target_count')!r}")
            return CustomAction.RunResult(success=False)

        global _remaining
        _remaining = target
        log_message(f"[PVP] 剩余战斗次数: {target}")
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("CheckPVPBattleCount")
class CheckPVPBattleCount(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> CustomAction.RunResult:
        try:
            return self._run(context, argv)
        except Exception:
            # 异常必须显式返回失败，否则会被 ctypes 静默忽略导致误判成功
            traceback.print_exc()
            return CustomAction.RunResult(success=False)

    def _run(self, context: Context, argv: CustomAction.RunArg) -> CustomAction.RunResult:
        global _remaining
        if _remaining is None:
            log_message("[PVP] CheckPVPBattleCount: remaining 未初始化，请先调用 InitPVPBattleCount")
            return CustomAction.RunResult(success=False)

        _remaining -= 1

        if _remaining <= 0:
            log_message("[PVP] 战斗次数已用完，返回主界面")
            _remaining = None
            context.override_pipeline(
                {
                    # 用完：回主页结束任务（提示走 agent 日志，不弹窗）
                    "PVP_Do:CheckBattleCount": {
                        "next": ["PVP_Click:MainMenu"]
                    },
                }
            )
            return CustomAction.RunResult(success=True)

        log_message(f"[PVP] 剩余战斗次数: {_remaining}")
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("PVP_Log")
class PVPLog(CustomAction):
    """输出 PVP 任务日志到 agent 通道（VSC 插件终端 / MXU / MFAAvalonia 面板）。

    参数：
    - content: 要输出的内容（必填）

    仅通过 agent stderr（``info:`` 前缀格式）输出，不产生 focus 通知；本动作负责
    agent 日志通道的可见性（PVP 不使用弹窗提示）。
    """

    def run(self, context: Context, argv: CustomAction.RunArg) -> CustomAction.RunResult:
        try:
            params = parse_params(argv.custom_action_param)
            content = params.get("content")
            if not content:
                log_message("[PVP_Log] 缺少 content 参数")
                return CustomAction.RunResult(success=False)
            log_message(content)
            return CustomAction.RunResult(success=True)
        except Exception:
            # 异常必须显式返回失败，否则会被 ctypes 静默忽略导致误判成功
            traceback.print_exc()
            return CustomAction.RunResult(success=False)
