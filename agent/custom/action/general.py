import json
import sys
from typing import Any

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction


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
