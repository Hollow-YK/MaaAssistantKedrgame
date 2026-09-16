from __future__ import annotations

import re
import time
import traceback
from typing import Any

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from maa.pipeline import JActionType, JClick, JOCR, JRecognitionType

from ..general import parse_params


@AgentServer.custom_action("Activity_Stage_Select")
class ActivityStageSelect(CustomAction):
    """活动选关 Custom：以 EP（章节）为单位定位，划动到目标 EP 开头后逐屏寻找目标并点击。

    选关逻辑：
      1. 根据输入判断目标关卡所属 EP（如 EX2-2 → EP2）
      2. OCR 识别 roi 区域，判断当前所在位置（可见 EP 范围）；若有效信息不足则向前划动
      3. 划动到目标 EP 的开头（如 EP2 的关卡划动到 EP1 与 EP2 交界；EP1 划到最左侧）
      4. 从目标 EP 开头向后（前进方向）划动，逐屏寻找目标关卡并点击

    活动关专属：点击后校验进入的关卡，并处理“挑战次数已耗尽”分支。
    通用关卡选关请使用 Stage_Select（按 assets/resource/stage/map.json 的顺序定位）。

    通过 custom_action_param 配置：
      - stage: 目标关卡，如 "2-3"、"EX2-1"
      - roi: 选关地图 OCR 区域，默认 [0, 200, 1280, 400]
      - swipe_begin: 向左（回退）滑动节点名，默认 SceneDo_Swipe_Stage_Swipe2begin
      - swipe_next: 向右（前进）滑动节点名，默认 SceneDo_Swipe_Stage_Swipe2next
      - load_wait: 进入选关界面后的等待秒数，默认 5
      - max_swipes: 每个阶段最多滑动次数（安全上限），默认 50
    """

    # 默认选关地图 OCR 区域
    DEFAULT_STAGE_MAP_ROI = [0, 200, 1280, 400]
    # 默认左右滑动节点名
    DEFAULT_SWIPE_BEGIN = "SceneDo_Swipe_Stage_Swipe2begin"
    DEFAULT_SWIPE_NEXT = "SceneDo_Swipe_Stage_Swipe2next"
    # 滑动结束后等待地图稳定（秒）
    SWIPE_SETTLE_SECONDS = 1.0
    # 点击后校验：进入关卡详情后标题 OCR 区域
    VERIFY_ROI = [130, 25, 290, 70]
    # 点击后等待关卡详情加载的秒数
    VERIFY_WAIT_SECONDS = 3.0

    # 关卡名 → EP：如 "1-1" → 1、"EX2-1" → 2
    _STAGE_EP_PATTERN = re.compile(r"(?:EX)?(\d+)-\d+", re.IGNORECASE)
    _ALNUM = re.compile(r"[^A-Z0-9]")

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
        stage = str(params.get("stage", "")).strip().upper()
        roi = params.get("roi", self.DEFAULT_STAGE_MAP_ROI)
        swipe_begin = params.get("swipe_begin", self.DEFAULT_SWIPE_BEGIN)
        swipe_next = params.get("swipe_next", self.DEFAULT_SWIPE_NEXT)
        load_wait = float(params.get("load_wait", 5))
        max_swipes = int(params.get("max_swipes", 50))

        target_norm = self._normalize(stage)
        target_ep = self._stage_ep(stage)
        if target_ep is None:
            print(f"[Activity_Stage_Select] 无效关卡参数: {stage!r}")
            return CustomAction.RunResult(success=False)

        def try_click(stages: list[dict[str, Any]]) -> CustomAction.RunResult | None:
            """目标在可见关卡中 → 点击其中心，随后等待并校验进入的关卡。

            返回 None 表示目标不在本屏（未点击）；否则返回点击+校验的结果。
            """
            for s in stages:
                if s["norm"] == target_norm:
                    box = s.get("box")
                    if box is not None:
                        context.run_action_direct(
                            JActionType.Click,
                            JClick(),
                            tuple(box),  # box: [x, y, w, h]，点击其中心
                            "",
                        )
                    print(f"[Activity_Stage_Select] 已点击目标关卡: {stage}，等待……")
                    # 活动关特殊逻辑：点击后先确认是否出现"次数耗尽"提示；有则跳过本关
                    if argv.node_name.startswith(
                        "AutoSweep_Activity_1_Stage"
                    ) and self._check_times_exhausted(context):
                        print(
                            f"[Activity_Stage_Select] 关卡 {stage} 挑战次数已耗尽，转 AutoSweep_Activity_1_Times0"
                        )
                        context.override_next(
                            argv.node_name, ["AutoSweep_Activity_1_Times0"]
                        )
                        return CustomAction.RunResult(success=True)
                    # 未出现耗尽提示 → 校验进入的关卡（成功/关卡不符/失败 三态）
                    verify = self._verify_stage(context, target_norm)
                    if verify == "success":
                        print(f"[Activity_Stage_Select] 校验通过：已进入关卡 {stage}")
                        return CustomAction.RunResult(success=True)
                    if verify == "mismatch":
                        # 进错关卡 → 关闭详情回到地图，重新寻找
                        print(
                            f"[Activity_Stage_Select] 进入的关卡与目标 {stage} 不符，关闭详情重新寻找"
                        )
                        self._click_node(context, "UI_Combat_StageDetails_Close")
                        return None
                    # 校验失败（未识别到关卡名）→ 判断是否在关卡详情：在则退出，否则视为已在地图，重新寻找
                    print(
                        f"[Activity_Stage_Select] 未识别到关卡名，处理关卡详情状态后重新寻找 {stage}"
                    )
                    if self._on_stage_detail(context):
                        self._click_node(context, "UI_Combat_StageDetails_Close")
                    return None
            return None

        # ── 1. 等待地图加载完成 ──
        time.sleep(load_wait)

        # ── 2. 获取初始有效位置（至少识别到一个关卡）；信息不足则向前（回退到开头）划动 ──
        stages = None
        for _ in range(max_swipes):
            stages = self._scan(context, roi)
            if stages is not None:
                break
            self._swipe_twice(context, swipe_begin)
            time.sleep(self.SWIPE_SETTLE_SECONDS)
        if stages is None:
            print("[Activity_Stage_Select] 始终未识别到有效关卡，无法定位")
            return CustomAction.RunResult(success=False)
        click_result = try_click(stages)
        if click_result is not None:
            return click_result
        print(
            f"[Activity_Stage_Select] 目标 {stage} 属 EP{target_ep}；"
            f"当前可见: {' '.join(s['norm'] for s in stages)}"
        )

        # ── 3. 划动到目标 EP 的开头 ──
        if target_ep == 1:
            # EP1 开头 = 地图最左侧：持续向左直到最左侧关卡为 1-1（或视野不再变化）
            first_norm = self._normalize("1-1")
            prev_norms: list[str] | None = None
            for _ in range(max_swipes):
                stages = self._scan(context, roi)
                if stages is None:
                    self._swipe_twice(context, swipe_begin)
                    time.sleep(self.SWIPE_SETTLE_SECONDS)
                    continue
                click_result = try_click(stages)
                if click_result is not None:
                    return click_result
                norms = [s["norm"] for s in stages]
                if stages[0]["norm"] == first_norm or norms == prev_norms:
                    break  # 已到最左侧
                prev_norms = norms
                self._swipe_twice(context, swipe_begin)
                time.sleep(self.SWIPE_SETTLE_SECONDS)
        else:
            # 目标 EP 开头 = (EP(target_ep-1), EP(target_ep)) 交界
            for _ in range(max_swipes):
                stages = self._scan(context, roi)
                if stages is None:
                    self._swipe_twice(
                        context, swipe_begin
                    )  # 偶发识别失败 → 向左推进重试
                    time.sleep(self.SWIPE_SETTLE_SECONDS)
                    continue
                click_result = try_click(stages)
                if click_result is not None:
                    return click_result
                lo = stages[0]["ep"]  # 最左侧可见关卡所属 EP
                hi = stages[-1]["ep"]  # 最右侧可见关卡所属 EP
                if lo == target_ep - 1 and hi >= target_ep:
                    break  # 已看到前一 EP 与目标 EP → 在目标 EP 开头
                if hi < target_ep:
                    self._swipe_twice(context, swipe_next)  # 目标 EP 在更右侧
                else:
                    self._swipe_twice(context, swipe_begin)  # 目标 EP 开头在更左侧
                time.sleep(self.SWIPE_SETTLE_SECONDS)

        # ── 4. 从目标 EP 开头向后（前进方向）划动寻找目标并点击 ──
        for _ in range(max_swipes):
            stages = self._scan(context, roi)
            if stages is None:
                self._swipe_twice(context, swipe_next)
                time.sleep(self.SWIPE_SETTLE_SECONDS)
                continue
            click_result = try_click(stages)
            if click_result is not None:
                return click_result
            if stages[0]["ep"] > target_ep:
                # 已越过目标 EP 仍未找到 → 失败
                print(
                    f"[Activity_Stage_Select] 已越过 EP{target_ep} 仍未找到关卡 {stage}"
                )
                return CustomAction.RunResult(success=False)
            self._swipe_twice(context, swipe_next)
            time.sleep(self.SWIPE_SETTLE_SECONDS)

        print(
            f"[Activity_Stage_Select] 超过最大滑动次数 {max_swipes}，仍未找到关卡 {stage}"
        )
        return CustomAction.RunResult(success=False)

    def _screencap(self, context: Context) -> Any:
        """主动刷新截图并返回"""
        context.tasker.controller.post_screencap().wait()
        return context.tasker.controller.cached_image

    def _swipe_twice(self, context: Context, node_name: str) -> None:
        """一次划两下，加快选关定位"""
        context.run_task(node_name)
        context.run_task(node_name)

    def _verify_stage(self, context: Context, target_norm: str) -> str:
        """点击后等待数秒，OCR 校验进入的关卡标题。

        先等待关卡详情加载（VERIFY_WAIT_SECONDS），再对 VERIFY_ROI 做 OCR；
        兼容 OCR 将 "EX2-1" 读成 "2-1" 的情况。

        返回三种结果：
          - "success"  进入的关卡与目标一致
          - "mismatch" 识别到关卡名（1-1 / EX1-1 格式）但非目标 → 进错关卡
          - "failed"   未识别到任何关卡名（可能未进入详情或仍在加载）
        """
        time.sleep(self.VERIFY_WAIT_SECONDS)

        candidates = {target_norm}
        if target_norm.startswith("EX"):
            candidates.add(target_norm[2:])  # 去掉 EX 前缀再比对

        for _ in range(3):
            image = self._screencap(context)
            detail = context.run_recognition_direct(
                JRecognitionType.OCR,
                JOCR(roi=self.VERIFY_ROI),
                image,
            )
            if detail and detail.hit:
                norms: list[str] = []
                for result in detail.all_results:
                    text = getattr(result, "text", "") or ""
                    if not self._STAGE_EP_PATTERN.search(text):
                        continue  # 忽略非关卡名格式（1-1 / EX1-1）的文本
                    norms.append(self._normalize(text))
                if norms:
                    if any(c in norm for norm in norms for c in candidates):
                        return "success"
                    return "mismatch"
            time.sleep(0.5)
        return "failed"

    def _check_times_exhausted(self, context: Context) -> bool:
        """OCR [260, 100, 750, 60]，包含"已耗尽"则返回 True（挑战次数已耗尽）"""
        image = self._screencap(context)
        detail = context.run_recognition_direct(
            JRecognitionType.OCR,
            JOCR(roi=[260, 100, 750, 60]),
            image,
        )
        if detail and detail.hit:
            for result in detail.all_results:
                text = getattr(result, "text", "") or ""
                if "已耗尽" in text:
                    return True
        return False

    def _on_stage_detail(self, context: Context) -> bool:
        """通过 UI_Combat_StageDetails_Close 是否命中判断是否在关卡详情页"""
        image = self._screencap(context)
        detail = context.run_recognition("UI_Combat_StageDetails_Close", image)
        return bool(detail and detail.hit)

    def _click_node(
        self,
        context: Context,
        node_name: str,
        attempts: int = 5,
        interval: float = 0.5,
    ) -> bool:
        """识别指定节点并点击其中心，返回是否成功点击"""
        for _ in range(attempts):
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
            time.sleep(interval)
        return False

    def _scan(self, context: Context, roi: Any) -> list[dict[str, Any]] | None:
        """OCR 扫描当前视野，返回有效关卡列表（按 x 坐标从左到右排序）；未识别到任何关卡返回 None。

        一次 OCR 可能识别到多个目标，这里仅取有效（关卡名）结果并保留坐标：
        每项: {"norm": 归一化关卡名, "ep": 所属EP, "x": 中心x坐标, "box": OCR box}
        """
        image = self._screencap(context)
        detail = context.run_recognition_direct(
            JRecognitionType.OCR,
            JOCR(roi=roi, color_filter="UI_Combat_StageMap_TextMask"),
            image,
        )
        if not detail or not detail.hit:
            return None

        stages: list[dict[str, Any]] = []
        for result in detail.all_results:
            text = getattr(result, "text", "") or ""
            m = self._STAGE_EP_PATTERN.search(text)
            if not m:
                continue  # 忽略非关卡文本
            box = getattr(result, "box", None)
            x = box[0] + box[2] // 2 if box else 0
            stages.append(
                {
                    "norm": self._normalize(text),
                    "ep": int(m.group(1)),
                    "x": x,
                    "box": box,
                }
            )
        if not stages:
            return None
        stages.sort(key=lambda s: s["x"])  # 按坐标从左到右排序
        return stages

    @staticmethod
    def _stage_ep(stage: str) -> int | None:
        """返回关卡所属 EP："1-1"→1，"EX2-2"→2；无效返回 None"""
        m = re.match(r"^(?:EX)?(\d+)-\d+$", stage, re.IGNORECASE)
        if not m:
            return None
        return int(m.group(1))

    @classmethod
    def _normalize(cls, text: str) -> str:
        """去掉非字母数字字符并转大写，用于精确匹配关卡名"""
        return cls._ALNUM.sub("", text.upper())
