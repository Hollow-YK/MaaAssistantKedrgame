import json
import sys
import time
from typing import Any

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from maa.pipeline import JActionType, JClick


def strip_jsonc_comments(text: str) -> str:
    """移除 JSONC 注释（// 与 /* */），保留字符串/转义，并维持行号。

    agent 运行时无法引用 tools/ 下的实现，故此处自包含。
    """
    result = []
    state = 0  # 0=普通, 1=字符串内, 2=转义
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if state == 0:
            if ch == '"':
                result.append(ch)
                state = 1
                i += 1
            elif text.startswith("//", i):
                i += 2
                while i < n and text[i] != "\n":
                    i += 1
                if i < n:
                    result.append("\n")  # 保留换行以维持行号
                    i += 1
            elif text.startswith("/*", i):
                i += 2
                while i + 1 < n and not text.startswith("*/", i):
                    if text[i] == "\n":
                        result.append("\n")
                    i += 1
                i = min(i + 2, n)
            else:
                result.append(ch)
                i += 1
        elif state == 1:
            result.append(ch)
            if ch == "\\":
                state = 2
            elif ch == '"':
                state = 0
            i += 1
        else:  # state == 2（转义）
            result.append(ch)
            state = 1
            i += 1
    return "".join(result)


def parse_params(param: Any) -> dict[str, Any]:
    """解析 custom_action_param，支持 dict 或 JSON 字符串"""
    if param is None:
        return {}
    if isinstance(param, dict):
        return param
    if isinstance(param, str):
        try:
            parsed = json.loads(param)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    return {}


def log_message(message: str) -> None:
    """输出运行日志到 agent 通道。

    统一写 stderr 并带 ``level:消息`` 前缀：MFAAvalonia 解析 agent 的
    stderr 行（``level_short:message`` 约定），MXU 与 VSC 插件终端按原文
    显示两条流；stdout 裸 print 在 MFAAvalonia 下不可见。
    """
    print(f"info:{message}", file=sys.stderr)


# ---- 停止响应 ----
# 上层「停止任务」后 MaaTaskerStopping 立刻变 True，但框架只能在一个节点/一次
# run_task 结束时才检查停止标志；custom 自己的 while/for 循环和 time.sleep 不会
# 被打断，必须主动查询并尽快返回，否则要等整个循环跑完才真正停下。
#
# 轮询粒度对齐 MaaEnd（agent/go-service/autoecofarm/interruptiblesleep.go 的
# interruptibleSleepChunkMs = 250）：250ms 一次反向查询，停止延迟不超过约 0.3s，
# 同时避免 agent 模式下过于频繁的 RPC。对停止延迟敏感的短等待可自行减小该值。
STOP_POLL_INTERVAL = 0.25


def stop_requested(context: Context) -> bool:
    """上层是否已请求停止当前任务。

    在 custom 回调运行期间 tasker 仍处于 running，故停止请求会立即体现在
    ``context.tasker.stopping`` 上；查询失败时按“未停止”处理，避免探测本身
    把正常流程打断。
    """
    try:
        return bool(context.tasker.stopping)
    except Exception:
        return False


def interruptible_sleep(context: Context, seconds: float) -> bool:
    """可被停止请求打断的 sleep，返回 False 表示期间收到了停止请求。

    长等待应改用本函数而不是 ``time.sleep``：每 ``STOP_POLL_INTERVAL`` 秒
    查询一次停止标志，使停止延迟不再取决于等待时长本身。
    """
    deadline = time.monotonic() + max(0.0, seconds)
    while not stop_requested(context):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return True
        time.sleep(min(STOP_POLL_INTERVAL, remaining))
    return False


@AgentServer.custom_action("ClickAndSleep")
class ClickAndSleep(CustomAction):
    """点击本节点的识别框，然后做可被停止请求打断的固定时长等待。

    等价于 pipeline 的 ``Click`` + ``post_delay``，但等待可中断；用于带
    ``[JumpBack]`` 等必须保持原节点结构的场景（拆成独立 sleep 节点会改变跳回目标）。

    Examples:
        ``custom_action_param``::

            {
                "duration_ms": 7000
            }
    """

    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        params = parse_params(argv.custom_action_param)
        raw = params.get(
            "duration_ms", params.get("durationMs", params.get("duration", 0))
        )
        try:
            duration_ms = max(0, int(raw))
        except (TypeError, ValueError):
            log_message(f"[ClickAndSleep] duration_ms 必须是整数，得到: {raw!r}")
            return CustomAction.RunResult(success=False)

        box = argv.box
        if box is None or box.w <= 0 or box.h <= 0:
            log_message("[ClickAndSleep] 识别框为空，无法点击")
            return CustomAction.RunResult(success=False)

        if stop_requested(context):
            return CustomAction.RunResult(success=True)

        detail = context.run_action_direct(
            JActionType.Click,
            JClick(),
            (box.x, box.y, box.w, box.h),
            "",
        )
        if detail is None or not detail.success:
            log_message("[ClickAndSleep] 点击失败")
            return CustomAction.RunResult(success=False)

        if not interruptible_sleep(context, duration_ms / 1000.0):
            log_message("[ClickAndSleep] 收到停止请求，提前结束等待")
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("InterruptibleSleep")
class InterruptibleSleep(CustomAction):
    """可被停止请求打断的固定时长等待。

    pipeline 的 ``pre_delay`` / ``post_delay`` 是框架内不可中断的 sleep：停止请求
    落在等待中间时，只能等整段等待结束。长等待应改用本动作，停止时最多等一个
    ``STOP_POLL_INTERVAL`` 就返回。

    Examples:
        ``custom_action_param``::

            {
                "duration_ms": 7000
            }
    """

    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        params = parse_params(argv.custom_action_param)
        raw = params.get(
            "duration_ms", params.get("durationMs", params.get("duration", 0))
        )
        try:
            duration_ms = max(0, int(raw))
        except (TypeError, ValueError):
            log_message(f"[InterruptibleSleep] duration_ms 必须是整数，得到: {raw!r}")
            return CustomAction.RunResult(success=False)

        if not interruptible_sleep(context, duration_ms / 1000.0):
            log_message("[InterruptibleSleep] 收到停止请求，提前结束等待")
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("DisableNode")
class DisableNode(CustomAction):
    """Disable one pipeline node at runtime.

    Examples:
        `custom_action_param`::

            {
                "node_name": "NodeName"
            }
    """

    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        params = parse_params(argv.custom_action_param)
        node_name = params.get("node_name")
        if not node_name:
            return CustomAction.RunResult(success=False)

        context.override_pipeline({node_name: {"enabled": False}})
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("NodeOverride")
class NodeOverride(CustomAction):
    """Pass a pipeline override object directly to context.override_pipeline().

    Examples:
        `custom_action_param`::

            {
                "NodeName": {
                    "enabled": false,
                    "timeout": 1000
                }
            }
    """

    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        pipeline_override = parse_params(argv.custom_action_param)
        if pipeline_override:
            context.override_pipeline(pipeline_override)
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("ResetCount")
class ResetCount(CustomAction):
    """Clear hit counters for one or more nodes.

    Examples:
        `custom_action_param`::

            {
                "nodes": ["NodeA", "NodeB"],
                "strict": false
            }
    """

    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        params = parse_params(argv.custom_action_param)

        nodes = params.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            return CustomAction.RunResult(success=False)

        strict = params.get("strict", False)
        has_failure = False
        for node_name in nodes:
            if not isinstance(node_name, str) or not node_name:
                has_failure = True
                continue
            if not context.clear_hit_count(node_name):
                has_failure = True

        return CustomAction.RunResult(success=not (strict and has_failure))


@AgentServer.custom_action("SubTask")
class SubTask(CustomAction):
    """Run sub tasks in order from a custom action node.

    Examples:
        `custom_action_param`::

            {
                "sub": ["TaskA", "TaskB"],
                "continue": false,
                "strict": true
            }
    """

    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        params = parse_params(argv.custom_action_param)

        tasks = params.get("sub")
        if not isinstance(tasks, list) or not tasks:
            return CustomAction.RunResult(success=False)

        continue_on_failure = bool(params.get("continue", False))
        strict = bool(params.get("strict", True))
        has_failure = False

        for task_name in tasks:
            if stop_requested(context):
                log_message("[SubTask] 收到停止请求，中断剩余子任务")
                return CustomAction.RunResult(success=False)
            if not isinstance(task_name, str) or not task_name:
                has_failure = True
                if not continue_on_failure:
                    break
                continue

            task_detail = context.run_task(task_name)
            if task_detail and task_detail.status.failed:
                has_failure = True
                if not continue_on_failure:
                    break

        return CustomAction.RunResult(success=not (has_failure and strict))
