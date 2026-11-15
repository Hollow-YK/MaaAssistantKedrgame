"""任务生命周期状态清理。

对齐 MaaEnd 的 ``runStateResetSink``：custom 可能在任务被停止时来不及走到收尾
分支，模块级状态会残留到下一次运行。这里在 tasker 任务结束（成功或失败/停止）
时统一清理。
"""

from maa.agent.agent_server import AgentServer
from maa.event_sink import NotificationType
from maa.tasker import Tasker, TaskerEventSink

from ..action import pvp


@AgentServer.tasker_sink()
class StateResetSink(TaskerEventSink):
    """任务结束时清理跨任务模块状态。"""

    def on_tasker_task(
        self,
        tasker: Tasker,
        noti_type: NotificationType,
        detail: TaskerEventSink.TaskerTaskDetail,
    ) -> None:
        if noti_type not in (NotificationType.Succeeded, NotificationType.Failed):
            return
        pvp.reset_remaining(int(detail.task_id))
