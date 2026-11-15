from __future__ import annotations

import re

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from maa.pipeline import JActionType, JClick, JOCR, JRecognitionType

from ..general import interruptible_sleep, stop_requested
from ..sweep import AutoSweepManager


@AgentServer.custom_action("AutoSweep_Activity_1_Manager")
class AutoSweepActivity1Manager(AutoSweepManager):
    """耀斑活动-自动扫荡管理器：检查剩余挑战次数并开始满额扫荡。

    前置：AutoSweep_Activity_1_Stage_* 已完成选关，停留在关卡详情界面。

    本关不消耗体力，无需考虑体力；只要剩余次数 > 0 且已解锁扫荡，就直接将扫荡次数
    设为最大并点击开始。点击开始扫荡后本管理器即结束，后续的结算、领取物品、
    回到选关地图等均由 AutoSweep_Activity_1_StageLoop 跳板节点自动处理。

    流程：
      1. 等待关卡详情加载 + 解锁检查（复用 AutoSweepManager）
      2. OCR 读取剩余挑战次数（同 AutoBattle_Activity_1_Manager）；次数为 0 则点击关闭按钮回到地图
      3. 确保扫荡已解锁开启 → 次数直接设为最大 → 点击开始扫荡 → 结束
    """

    # 剩余挑战次数 OCR 区域（与 AutoBattle_Activity_1_Manager 一致）
    COUNT_ROI = [940, 120, 180, 30]
    COUNT_PATTERN = re.compile(r"(\d+)\s*/\s*(\d+)")
    COUNT_RETRY = 5
    COUNT_RETRY_INTERVAL = 1.0

    def _run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        if stop_requested(context):
            return CustomAction.RunResult(success=False)
        # ── 0. 等待关卡详情界面加载完成 + 解锁检查（复用 AutoSweepManager）──
        if not self._wait_stage_ready(context):
            if stop_requested(context):
                return CustomAction.RunResult(success=False)
            if self._check_unlock(context):
                context.run_task("AutoSweepFailed_lock")
            return CustomAction.RunResult(success=False)
        if self._check_unlock(context):
            context.run_task("AutoSweepFailed_lock")
            return CustomAction.RunResult(success=False)

        # ── 1. 检查剩余挑战次数；次数为 0 直接结束（交给跳板节点处理）──
        current, total = self._read_count(context)
        if stop_requested(context):
            return CustomAction.RunResult(success=False)
        if current is None:
            print("[AutoSweep_Activity_1_Manager] 未能识别剩余挑战次数，任务失败")
            return CustomAction.RunResult(success=False)
        print(f"[AutoSweep_Activity_1_Manager] 剩余挑战次数: {current}/{total}")
        if current <= 0:
            print("[AutoSweep_Activity_1_Manager] 挑战次数不足，点击关闭按钮回到地图")
            self._click_node(context, "UI_Combat_StageDetails_Close")
            return CustomAction.RunResult(success=True)

        # ── 2. 确保扫荡已解锁并开启 ──
        if not self._ensure_sweep_enabled(context):
            return CustomAction.RunResult(success=False)

        # ── 3. 次数直接设为最大（本关不消耗体力，无需考虑体力）──
        if stop_requested(context):
            return CustomAction.RunResult(success=False)
        context.run_task("AutoSweep_Click_Sweep_max")
        context.run_task("AutoSweep_Click_Sweep_max")

        # ── 4. 点击开始扫荡后结束；不走 AutoSweep_Click_Start2 的 next（活动关特殊逻辑），
        #    结算/领取/回地图由 AutoSweep_Activity_1_StageLoop 自动处理 ──
        if stop_requested(context):
            return CustomAction.RunResult(success=False)
        context.run_task("AutoSweep_Click_Start")
        self._click_node(context, "AutoSweep_Click_Start2")
        if stop_requested(context):
            return CustomAction.RunResult(success=False)
        return CustomAction.RunResult(success=True)

    def _read_count(self, context: Context) -> tuple[int | None, int | None]:
        """OCR 读取剩余挑战次数，返回 (current, total)；识别不到返回 (None, None)"""
        for _ in range(self.COUNT_RETRY):
            if stop_requested(context):
                return None, None
            image = self._screencap(context)
            detail = context.run_recognition_direct(
                JRecognitionType.OCR,
                JOCR(roi=self.COUNT_ROI),
                image,
            )
            if detail and detail.hit:
                for result in detail.all_results:
                    text = getattr(result, "text", "") or ""
                    m = self.COUNT_PATTERN.search(text)
                    if m:
                        return int(m.group(1)), int(m.group(2))
            if not interruptible_sleep(context, self.COUNT_RETRY_INTERVAL):
                return None, None
        return None, None

    def _click_node(
        self,
        context: Context,
        node_name: str,
        attempts: int = 5,
        interval: float = 0.5,
    ) -> bool:
        """识别指定节点并点击其中心，返回是否成功点击"""
        for _ in range(attempts):
            if stop_requested(context):
                return False
            image = self._screencap(context)
            detail = context.run_recognition(node_name, image)
            if detail and detail.hit and detail.box:
                context.run_action_direct(
                    JActionType.Click,
                    JClick(),
                    tuple(detail.box),
                    "",
                )
                return True
            if not interruptible_sleep(context, interval):
                return False
        return False
