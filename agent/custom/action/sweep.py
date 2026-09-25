from __future__ import annotations

import time
import traceback
from typing import Any

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from maa.pipeline import JActionType, JClick, JOCR, JRecognitionType

from .general import parse_params


@AgentServer.custom_action("AutoSweepManager")
class AutoSweepManager(CustomAction):
    """自动扫荡管理器：接管关卡详情后的扫荡循环控制。

    流程：
      1. 自动战斗可用性确认（未解锁则通知失败）
      2. 开启扫荡选项（OCR 识别"打开/关闭"）
      3. 设置单次扫荡次数并检查体力
      4. 点击开始（含保底体力确认）→ 编队 → 结算 → 物品
      5. 回到步骤 2 继续下一轮，直到体力不足
    """

    # 扫荡开关 OCR 区域
    SWEEP_SWITCH_ROI = [820, 520, 185, 30]
    # 关闭体力不足弹窗按钮（参考 MaaKEDR FarmResources.CheckStamina）
    CLOSE_STAMINA_TARGET = [125, 592, 10, 9]
    # auto 模式下最多减次次数（6 → 1）
    MAX_REDUCE_TIMES = 6
    # 点击「准备快速战斗」后等待界面响应的轮询次数与间隔（秒）
    # 弹窗有渲染延迟，需轮询等待；超时未响应则交由后续流程处理
    MAX_WAIT_TRIES = 10
    WAIT_INTERVAL = 0.5

    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        try:
            return self._run(context, argv)
        except Exception:
            # 异常必须显式返回失败，否则会被 ctypes 静默忽略导致误判成功
            traceback.print_exc()
            return CustomAction.RunResult(success=False)

    def _run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        params = parse_params(argv.custom_action_param)
        batch_size = params.get("batch_size", "auto")

        # ── 0. 等待关卡详情界面加载完成（能识别到扫荡开关即视为就绪）──
        # 避免在加载动画中过早执行 Check_unlock 导致误判
        if not self._wait_stage_ready(context):
            # 长时间识别不到扫荡开关：可能关卡未解锁 → 解锁检查确认
            if self._check_unlock(context):
                context.run_task("AutoSweepFailed_lock")
            return CustomAction.RunResult(success=False)

        # ── 1. 自动战斗可用性确认 ──
        if self._check_unlock(context):
            context.run_task("AutoSweepFailed_lock")
            return CustomAction.RunResult(success=False)

        # auto 模式：次数是否已初始化为最大、已减次数。
        # 跨轮次维护——否则每轮重新执行 Sweep_max 会把已减的次数抹掉。
        batch_inited = False
        reduced = 0

        while True:
            # ── 2. 开启扫荡选项 ──
            if not self._ensure_sweep_enabled(context):
                return CustomAction.RunResult(success=False)

            # ── 3. 设置次数并检查体力 ──
            ok, batch_inited, reduced = self._setup_batch(
                context, batch_size, batch_inited, reduced
            )
            if not ok:
                # 体力不足且无法继续 → 成功完成任务
                return CustomAction.RunResult(success=True)

            # ── 4. 开始扫荡（进入编队界面；若体力不足则由弹窗拦截）──
            context.run_task("AutoSweep_Click_Start")
            # 点击后等待界面响应：进入编队界面 → 点击开始战斗走完结算；
            # 出现体力不足弹窗 → 关掉弹窗回到步骤 2 降次重试。
            # 弹窗有渲染延迟，必须轮询等待，不能只查一次（否则会误判体力充足）。
            stamina_hit = False
            for _ in range(self.MAX_WAIT_TRIES):
                if self._check_stamina2(context):
                    stamina_hit = True
                    break
                if self._in_team_screen(context):
                    break  # 已进入编队界面，体力充足
                time.sleep(self.WAIT_INTERVAL)

            if stamina_hit:
                # 保底确认到体力不足弹窗 → 关闭后按模式处理
                self._close_stamina_dialog(context)
                if batch_size != "auto":
                    return CustomAction.RunResult(success=True)
                # 与 Check_Stamina 判定体力不足时一致：次数 -1 后重试
                if reduced >= self.MAX_REDUCE_TIMES:
                    return CustomAction.RunResult(success=True)  # 已减到下限
                context.run_task("AutoSweep_Click_Sweep_minus")
                reduced += 1
                continue

            # 体力充足 → 编队 → 结算 → 物品（由 pipeline 处理）
            context.run_task("AutoSweep_Click_Start2")

            # ── 5. 回到步骤 2 继续下一轮 ──

    def _screencap(self, context: Context) -> Any:
        """主动刷新截图并返回"""
        context.tasker.controller.post_screencap().wait()
        return context.tasker.controller.cached_image

    def _check_unlock(self, context: Context) -> bool:
        """识别到自动战斗不可用标识则返回 True"""
        detail = context.run_recognition(
            "AutoSweep_Check_unlock", self._screencap(context)
        )
        return bool(detail and detail.hit)

    def _check_stamina(self, context: Context) -> bool:
        """体力不足（红像素 > 100）则返回 True"""
        detail = context.run_recognition(
            "AutoSweep_Check_Stamina", self._screencap(context)
        )
        return bool(detail and detail.hit)

    def _check_stamina2(self, context: Context) -> bool:
        """保底：识别到体力不足弹窗则返回 True"""
        detail = context.run_recognition(
            "AutoSweep_Check_Stamina2", self._screencap(context)
        )
        return bool(detail and detail.hit)

    def _in_team_screen(self, context: Context) -> bool:
        """是否已进入编队界面（复用 AutoSweep_Click_Start2 的「开始战斗」按钮识别）"""
        detail = context.run_recognition(
            "AutoSweep_Click_Start2", self._screencap(context)
        )
        return bool(detail and detail.hit)

    def _read_sweep_switch(self, context: Context):
        """OCR 读取扫荡开关状态，返回 ("open"|"closed", box) 或 None"""
        image = self._screencap(context)
        detail = context.run_recognition_direct(
            JRecognitionType.OCR,
            JOCR(expected=["打开", "关闭"], roi=self.SWEEP_SWITCH_ROI),
            image,
        )
        if not detail or not detail.hit:
            return None
        for result in detail.all_results:
            text = getattr(result, "text", "") or ""
            if "打开" in text:
                return "open", result.box
            if "关闭" in text:
                return "closed", result.box
        return None

    def _wait_stage_ready(self, context: Context) -> bool:
        """等待关卡详情界面加载完成：能识别到扫荡开关（打开/关闭）即视为就绪。

        在加载动画期间 OCR 识别不到开关，会持续重试；避免过早执行后续检查。
        """
        for _ in range(10):
            state = self._read_sweep_switch(context)
            if state is not None:
                return True  # 已识别到开关 → 界面就绪
        return False

    def _ensure_sweep_enabled(self, context: Context) -> bool:
        """确保扫荡开关已开启；识别到"打开"则点击，识别到"关闭"则返回 True"""
        for _ in range(5):
            state = self._read_sweep_switch(context)
            if state is None:
                continue  # 未识别到，重试
            kind, box = state
            if kind == "closed":
                return True  # 已开启
            if kind == "open":
                context.run_action_direct(
                    JActionType.Click,
                    JClick(),
                    tuple(box),  # box 是 list [x,y,w,h]，转换为 tuple
                    "",
                )
                continue  # 点击后重新确认
        return False

    def _setup_batch(
        self,
        context: Context,
        batch_size: Any,
        batch_inited: bool,
        reduced: int,
    ) -> tuple[bool, bool, int]:
        """设置次数并检查体力。

        返回 (是否继续, batch_inited, reduced)。返回 False 表示体力不足应结束任务。

        batch_inited / reduced 由调用方跨轮次维护：
          - batch_inited：auto 模式下次数是否已初始化为最大。只在首轮执行 Sweep_max，
            否则每轮重置会把已减的次数抹掉（曾因此导致次数永远减不下去）；
          - reduced：已减次数，跨轮累积，防止弹窗重试时无限循环。
        """
        if batch_size == "auto":
            if not batch_inited:
                context.run_task("AutoSweep_Click_Sweep_max")
                batch_inited = True
            while self._check_stamina(context):
                if reduced >= self.MAX_REDUCE_TIMES:
                    return False, batch_inited, reduced  # 已减到下限仍不足 → 结束
                context.run_task("AutoSweep_Click_Sweep_minus")
                reduced += 1
            return True, batch_inited, reduced

        target = int(batch_size)
        if target >= 4:
            # 从最大开始减
            context.run_task("AutoSweep_Click_Sweep_max")
            for _ in range(self.MAX_REDUCE_TIMES - target):
                context.run_task("AutoSweep_Click_Sweep_minus")
        else:
            # 从最小开始加
            context.run_task("AutoSweep_Click_Sweep_min")
            for _ in range(target - 1):
                context.run_task("AutoSweep_Click_Sweep_plus")

        if self._check_stamina(context):
            return False, batch_inited, reduced  # 体力不足 → 结束
        return True, batch_inited, reduced

    def _close_stamina_dialog(self, context: Context) -> None:
        """点击关闭体力不足弹窗"""
        context.run_action_direct(
            JActionType.Click,
            JClick(),
            tuple(self.CLOSE_STAMINA_TARGET),
            "",
        )
