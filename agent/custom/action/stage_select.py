from __future__ import annotations

import json
import re
import time
import traceback
from pathlib import Path
from typing import Any, NamedTuple

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from maa.pipeline import JActionType, JClick, JOCR, JRecognitionType

from .general import parse_params, strip_jsonc_comments


class StageKey(NamedTuple):
    """关卡的语义化标识：由 OCR 原文解析而来，用于精确比对。

    相比“去掉符号转大写再比字符串”，按语义拆成三段后可以：
      - 容忍 OCR 在 EX / 数字 / 连字符之间插入的空格（EX 2 - 1 == EX2-1）
      - 用字段相等而非子串包含来比对，避免 1-1 被 1-11 误判为同一关
    """

    chapter: int  # 章节号，如 EX2-1 → 2
    index: int  # 关卡号，如 EX2-1 → 1
    ex: bool  # 是否为 EX 关


def _map_file_candidates() -> list[Path]:
    """map.json 候选路径。

    开发目录为 `assets/resource/stage/map.json`，安装后资源被拷贝到
    `<安装目录>/resource/stage/map.json`（见 tools/install.py），故一并尝试。
    """
    roots = [Path(__file__).resolve().parents[3], Path.cwd()]
    candidates: list[Path] = []
    for root in roots:
        candidates.append(root / "assets" / "resource" / "stage" / "map.json")
        candidates.append(root / "resource" / "stage" / "map.json")
    return candidates


@AgentServer.custom_action("Stage_Select")
class StageSelect(CustomAction):
    """通用选关 Custom：按选关地图（field）记录的关卡顺序定位并点击目标关卡。

    与活动选关（Activity_Stage_Select）的区别：本选关器不依赖 EP 规律，而是读取
    `assets/resource/stage/map.json` 中该 field 的关卡顺序，用“目标在前方则前进、
    在后方则回退”的方式逐屏收敛，因此可适配任意排布的选关地图。

    选关逻辑：
      1. 读取 map.json，取出目标 field 的 stage 关卡顺序，得到目标关卡的下标
      2. 等待选关界面加载完成后，OCR 扫描当前视野，识别可见关卡并换算成 map 下标
      3. 点击中心坐标位于目标关卡时点击；否则按“目标下标 < 可见最小下标 → 回退，
         其余情况前进”的方向滑动，逐屏重复直到找到目标
      4. 各方向视野均不再变化（已到地图边界）仍未找到目标 → 失败返回

    关卡名比对不采用“去符号转大写后比字符串”，而是把 OCR 原文解析成
    StageKey（章节号 + 关卡号 + EX 标记）后按字段相等比对，因此：
      - OCR 在 EX / 数字 / 连字符间插入空格（EX 2 - 1）也能正确识别
      - 1-1 不会被 1-11 误判为同一关（字段相等而非子串包含）

    map.json（assets/resource/stage/map.json，支持 JSONC 注释）格式：
      - `<field>`: 选关地图，key 即调用时传入的 field 名
        - `desc`:      地图描述（可选，仅用于日志）
        - `stage`:     关卡顺序，如 ["1-1", "1-2"]（必填，从左到右）
        - `roi`:       选关地图 OCR 区域，默认 [0, 200, 1280, 400]
        - `swipe_begin`: 向左（回退）滑动节点名，默认 SceneDo_Swipe_Stage_Swipe2begin
        - `swipe_next`:  向右（前进）滑动节点名，默认 SceneDo_Swipe_Stage_Swipe2next
        - `load_wait`:   进入选关界面后的等待秒数，默认 5
        - `max_swipes`:  最多滑动次数（安全上限），默认 50
        - `swipe_wait`:  每次滑动后等待地图稳定的上限秒数，默认 3
        - `verify`:      点击后是否校验进入的关卡，默认 true
        - `verify_roi`:  校验用标题 OCR 区域，默认 [130, 25, 290, 70]
        - `verify_wait`: 点击后等待关卡详情加载的秒数，默认 3

    流程中带多重兜底，确保异常时也能退出：同一位置最多点击 MAX_CLICK_ATTEMPTS 次，
    同一屏最多出现 MAX_SAME_VIEW 次（防两点间往复），连续 MAX_UNCHANGED_VIEWS 次
    滑动后视野无变化即判定到边界，识别到地图后连续 MAX_BLIND_SCANS 次扫不到本图
    关卡即判定滑出地图，以及总滑动次数上限 max_swipes。

    通过 custom_action_param 配置（field / stage 必填，其余覆盖 map.json 中的值）：
      - field: 选关地图名，须存在于 map.json
      - stage: 目标关卡，须在该 field 的 stage 顺序中
      - 其余同 map.json 中的可选字段
    """

    # 默认选关地图 OCR 区域
    DEFAULT_ROI = [0, 200, 1280, 400]
    # 默认左右滑动节点名
    DEFAULT_SWIPE_BEGIN = "SceneDo_Swipe_Stage_Swipe2begin"
    DEFAULT_SWIPE_NEXT = "SceneDo_Swipe_Stage_Swipe2next"
    # 进入选关界面后的等待秒数
    DEFAULT_LOAD_WAIT = 5.0
    # 最多滑动次数（安全上限）
    DEFAULT_MAX_SWIPES = 50
    # 滑动后等待地图稳定的上限（秒），以及轮询间隔（秒）
    DEFAULT_SWIPE_WAIT = 3.0
    SWIPE_POLL_INTERVAL = 0.3
    # 稳定判定时中心 x 的量化容差（像素）：小于该位移视为未移动，避免 OCR 抖动误判
    SETTLE_X_TOLERANCE = 8
    # 点击后校验：进入关卡详情后标题 OCR 区域 / 等待秒数
    DEFAULT_VERIFY = True
    DEFAULT_VERIFY_ROI = [130, 25, 290, 70]
    DEFAULT_VERIFY_WAIT = 3.0
    # 校验重试次数与间隔（秒）
    VERIFY_RETRY = 3
    VERIFY_RETRY_INTERVAL = 0.5
    # 同一位置最多点击次数（防止点击后未进入目标关卡时反复点击）
    MAX_CLICK_ATTEMPTS = 3
    # 同一屏最多出现次数（防止在两个位置之间来回震荡时不退出）
    MAX_SAME_VIEW = 4
    # 连续多少次“滑动后视野无变化”即判定已到地图边界（含反向重试那一次）
    MAX_UNCHANGED_VIEWS = 2
    # 已成功识别过地图后，连续扫描不到有效关卡的最大次数（防止盲滑到上限）
    MAX_BLIND_SCANS = 6

    # 关卡名解析：容忍 OCR 在 EX / 数字 / 连字符之间插入空白（含全角空格）
    # 例：1-1 / EX2-2 / EX 2-1 / EX2 - 1 / EX 2 - 1 均能解析
    _STAGE_KEY = re.compile(
        r"(?P<ex>EX)?[\s\u3000]*(?P<chapter>\d+)[\s\u3000]*-[\s\u3000]*(?P<index>\d+)",
        re.IGNORECASE,
    )

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
        field = str(params.get("field", "") or "").strip()
        stage = str(params.get("stage", "") or "").strip().upper()
        if not field:
            print("[Stage_Select] 缺少选关地图参数 field")
            return CustomAction.RunResult(success=False)
        if not stage:
            print("[Stage_Select] 缺少目标关卡参数 stage")
            return CustomAction.RunResult(success=False)

        # ── 1. 读取 map.json，取出该 field 的关卡顺序与目标下标 ──
        maps = self._load_map()
        if maps is None:
            return CustomAction.RunResult(success=False)
        entry = maps.get(field)
        if not isinstance(entry, dict):
            print(
                f"[Stage_Select] map.json 中不存在选关地图 field: {field}"
                f"（可用: {', '.join(maps) or '无'}）"
            )
            return CustomAction.RunResult(success=False)

        stage_list = entry.get("stage")
        if not isinstance(stage_list, list) or not stage_list:
            print(
                f"[Stage_Select] field {field} 的关卡顺序 stage 为空，请检查 map.json"
            )
            return CustomAction.RunResult(success=False)

        order = self._build_order(stage_list, field)
        target_key = self._parse_stage_key(stage)
        if target_key is None:
            print(f"[Stage_Select] 无法解析目标关卡名: {stage!r}")
            return CustomAction.RunResult(success=False)
        target_idx = order.get(target_key)
        if target_idx is None:
            print(
                f"[Stage_Select] 目标关卡 {stage} 不在 field {field} 的关卡顺序中"
                f"（{', '.join(str(s) for s in stage_list)}）"
            )
            return CustomAction.RunResult(success=False)

        roi = params.get("roi", entry.get("roi", self.DEFAULT_ROI))
        swipe_begin = str(
            params.get(
                "swipe_begin", entry.get("swipe_begin", self.DEFAULT_SWIPE_BEGIN)
            )
        )
        swipe_next = str(
            params.get("swipe_next", entry.get("swipe_next", self.DEFAULT_SWIPE_NEXT))
        )
        load_wait = float(
            params.get("load_wait", entry.get("load_wait", self.DEFAULT_LOAD_WAIT))
        )
        max_swipes = int(
            params.get("max_swipes", entry.get("max_swipes", self.DEFAULT_MAX_SWIPES))
        )
        swipe_wait = float(
            params.get("swipe_wait", entry.get("swipe_wait", self.DEFAULT_SWIPE_WAIT))
        )
        verify = bool(params.get("verify", entry.get("verify", self.DEFAULT_VERIFY)))
        verify_roi = params.get(
            "verify_roi", entry.get("verify_roi", self.DEFAULT_VERIFY_ROI)
        )
        verify_wait = float(
            params.get(
                "verify_wait", entry.get("verify_wait", self.DEFAULT_VERIFY_WAIT)
            )
        )

        desc = str(entry.get("desc", "") or field)
        print(
            f"[Stage_Select] 选关地图 {field}（{desc}），目标关卡 {stage}"
            f"（第 {target_idx + 1}/{len(stage_list)} 个）"
        )

        # ── 2. 等待选关界面加载完成 ──
        time.sleep(load_wait)

        # ── 3. 逐屏收敛寻找目标 ──
        direction = swipe_begin  # 上一次执行的滑动节点
        last_view: frozenset[int] | None = None  # 上一屏的可见关卡集合
        unchanged = 0  # 连续「滑动后视野无变化」次数（说明该方向已到边界）
        click_attempts = 0  # 已点击目标位置的次数（防止在同一位置反复点击）
        view_hits: dict[frozenset[int], int] = {}  # 各屏（关卡下标集合）出现次数
        seen_map = False  # 是否曾成功识别到本图关卡（用于区分“界面未就绪”与“盲滑”）
        blind_scans = 0  # 已识别过地图后，连续扫描不到有效关卡的次数

        for step in range(1, max_swipes + 1):
            visible = self._scan(context, roi, order)
            idxs = [v["index"] for v in visible] if visible else []

            if idxs:
                seen_map = True
                blind_scans = 0
                # 同一屏反复出现 → 已在两点之间来回震荡，提前失败
                hits = view_hits.get(frozenset(idxs), 0) + 1
                view_hits[frozenset(idxs)] = hits
                if hits > self.MAX_SAME_VIEW:
                    print(
                        f"[Stage_Select] 当前视野反复出现 {hits} 次，"
                        f"仍未找到关卡 {stage}，疑似在地图两点间往复"
                    )
                    return CustomAction.RunResult(success=False)
            else:
                # 识别过地图后若长时间扫不到本图关卡，说明已滑出地图（盲滑）→ 提前失败；
                # 一开始就扫不到则可能是界面未就绪，允许继续尝试到 max_swipes
                blind_scans += 1
                if seen_map and blind_scans > self.MAX_BLIND_SCANS:
                    print(
                        f"[Stage_Select] 连续 {blind_scans} 次未识别到本图关卡，"
                        f"疑似已滑出选关地图，任务失败"
                    )
                    return CustomAction.RunResult(success=False)

            found = next(
                (v for v in visible if v["key"] == target_key and v["box"] is not None),
                None,
            )
            if found is not None:
                if click_attempts >= self.MAX_CLICK_ATTEMPTS:
                    print(
                        f"[Stage_Select] 已尝试点击关卡 {stage} {click_attempts} 次"
                        f"仍未进入目标关卡，任务失败"
                    )
                    return CustomAction.RunResult(success=False)
                click_attempts += 1
                context.run_action_direct(
                    JActionType.Click,
                    JClick(),
                    tuple(found["box"]),  # box: [x, y, w, h]，点击其中心
                    "",
                )
                print(f"[Stage_Select] 已点击目标关卡 {stage}，等待……")
                if not verify:
                    return CustomAction.RunResult(success=True)
                verdict = self._verify_stage(
                    context, target_key, verify_roi, verify_wait
                )
                if verdict == "success":
                    print(f"[Stage_Select] 校验通过：已进入关卡 {stage}")
                    return CustomAction.RunResult(success=True)
                if verdict == "mismatch":
                    print(
                        f"[Stage_Select] 进入的关卡与目标 {stage} 不符，关闭详情重新寻找"
                    )
                else:
                    print(
                        f"[Stage_Select] 未识别到关卡名，关闭关卡详情后重新寻找 {stage}"
                    )
                # 回到选关地图后重扫本屏（目标已识别到，无需滑动）
                self._click_node(context, "UI_Combat_StageDetails_Close")
                view_hits.clear()
                last_view = None
                unchanged = 0
                continue

            # 目标在可见关卡左侧则回退，其余情况前进；无有效信息时维持上次方向
            if not idxs:
                next_direction = direction
            else:
                next_direction = swipe_begin if target_idx < min(idxs) else swipe_next

            # 判定上一次滑动是否“滑不动”：视野与上一屏完全相同即说明该方向已到边界。
            # 注意这里只比视野、不含方向——方向会被下面的翻转改动，若把方向也纳入
            # 判定键，翻转后必然不等于上一次，计数就永远被清零（曾经的缺陷）。
            view = frozenset(idxs) if idxs else None
            if view is not None and view == last_view:
                unchanged += 1
                if unchanged >= self.MAX_UNCHANGED_VIEWS:
                    print(
                        f"[Stage_Select] 连续 {unchanged} 次滑动后视野均无变化，"
                        f"已到选关地图边界，仍未找到关卡 {stage}"
                    )
                    return CustomAction.RunResult(success=False)
                # 该方向滑不动 → 反向再试一次
                next_direction = (
                    swipe_next if next_direction == swipe_begin else swipe_begin
                )
                print(
                    f"[Stage_Select] {'前进' if direction == swipe_next else '回退'}方向已到边界，改试反方向"
                )
            else:
                unchanged = 0
            last_view = view
            direction = next_direction

            names = (
                " ".join(v["text"] for v in visible) if visible else "未识别到本图关卡"
            )
            print(
                f"[Stage_Select] 第 {step} 屏（{names}）未找到 {stage}"
                f" → {'前进' if direction == swipe_next else '回退'}"
            )
            context.run_task(direction)
            # 滑动后轮询到地图稳定，避免固定等待时长在真机上偏短（OCR 到惯性动画中间帧）
            # 或偏长（白白空等）
            self._wait_swipe_settle(context, roi, order, swipe_wait)

        print(f"[Stage_Select] 超过最大滑动次数 {max_swipes}，仍未找到关卡 {stage}")
        return CustomAction.RunResult(success=False)

    # ------------------------------------------------------------------
    # 数据文件
    # ------------------------------------------------------------------
    def _load_map(self) -> dict[str, Any] | None:
        """读取并解析 map.json（JSONC）；失败返回 None"""
        for path in _map_file_candidates():
            if not path.is_file():
                continue
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    data = json.loads(strip_jsonc_comments(f.read()))
            except Exception:
                traceback.print_exc()
                print(f"[Stage_Select] 解析选关地图数据失败: {path}")
                return None
            if not isinstance(data, dict):
                print(f"[Stage_Select] 选关地图数据格式错误: {path}")
                return None
            # 只保留形如地图定义的 object 值，非 object 的字段一律忽略
            return {k: v for k, v in data.items() if isinstance(v, dict)}
        paths = "\n  ".join(str(p) for p in _map_file_candidates())
        print(f"[Stage_Select] 未找到选关地图数据文件 map.json，已尝试:\n  {paths}")
        return None

    @classmethod
    def _parse_stage_key(cls, text: str) -> StageKey | None:
        """把 OCR 原文解析为关卡语义标识；不含关卡名格式时返回 None。

        二次处理：不直接拿整段文本去比字符串，而是抽出「EX 标记 + 章节号 + 关卡号」
        三个字段。这样 OCR 在任意位置插入空格（EX 2 - 1）、或文本混有其它字样
        （"第2-1关"）时，都能得到同一个 StageKey。
        """
        m = cls._STAGE_KEY.search(text or "")
        if not m:
            return None
        return StageKey(
            chapter=int(m.group("chapter")),
            index=int(m.group("index")),
            ex=bool(m.group("ex")),
        )

    @classmethod
    def _build_order(cls, stage_list: list[Any], field: str) -> dict[StageKey, int]:
        """关卡顺序 → {关卡标识: 下标}；重复定义时保留靠前的下标并告警"""
        order: dict[StageKey, int] = {}
        for index, name in enumerate(stage_list):
            key = cls._parse_stage_key(str(name))
            if key is None:
                print(
                    f"[Stage_Select] field {field} 的关卡名无法解析: {name!r}，已跳过"
                )
                continue
            if key in order:
                print(
                    f"[Stage_Select] field {field} 的关卡顺序存在重复: {name}"
                    f"（下标 {order[key]} 与 {index}），定位可能不准确"
                )
                continue
            order[key] = index
        return order

    # ------------------------------------------------------------------
    # 识别与操作
    # ------------------------------------------------------------------
    def _screencap(self, context: Context) -> Any:
        """主动刷新截图并返回"""
        context.tasker.controller.post_screencap().wait()
        return context.tasker.controller.cached_image

    def _scan(
        self, context: Context, roi: Any, order: dict[StageKey, int]
    ) -> list[dict[str, Any]]:
        """OCR 扫描当前视野，返回按 x 坐标从左到右排序的可见关卡列表。

        仅保留能解析出关卡标识、且属于本选关地图（能在 order 中查到下标）的关卡，
        相邻选关地图的关卡会被忽略。
        每项: {"key": 关卡标识, "index": 地图下标, "x": 中心x, "box": OCR box, "text": 原文}
        """
        image = self._screencap(context)
        detail = context.run_recognition_direct(
            JRecognitionType.OCR,
            JOCR(roi=roi, color_filter="UI_Combat_StageMap_TextMask"),
            image,
        )
        if not detail or not detail.hit:
            return []

        visible: list[dict[str, Any]] = []
        for result in detail.all_results:
            text = getattr(result, "text", "") or ""
            key = self._parse_stage_key(text)
            if key is None:
                continue  # 非关卡名文本
            index = order.get(key)
            if index is None:
                continue  # 不属于本选关地图的关卡
            box = getattr(result, "box", None)
            x = box[0] + box[2] // 2 if box else 0
            visible.append(
                {"key": key, "index": index, "x": x, "box": box, "text": text}
            )
        visible.sort(key=lambda v: v["x"])  # 按坐标从左到右排序
        return visible

    def _visible_key(
        self, context: Context, roi: Any, order: dict[StageKey, int]
    ) -> tuple[tuple[StageKey, int], ...] | None:
        """当前视野的“稳定判定键”。

        以「关卡标识 + 量化后的中心 x」为键：只比对关卡名不足以判定静止——惯性减速
        期间画面仍在移动，但可能同样这几个关卡名仍可见；带上 x 即可识别出位移。
        x 按 SETTLE_X_TOLERANCE 量化，避免 OCR 亚像素抖动导致永远判定为“未稳定”。
        未识别到关卡时返回 None（滑动途中或已滑出地图）。
        """
        visible = self._scan(context, roi, order)
        if not visible:
            return None
        return tuple((v["key"], v["x"] // self.SETTLE_X_TOLERANCE) for v in visible)

    def _wait_swipe_settle(
        self, context: Context, roi: Any, order: dict[StageKey, int], timeout: float
    ) -> None:
        """滑动后等待地图稳定：轮询直到连续两次识别到相同画面，最多等待 timeout 秒。

        固定等待时长在真机上不适用（惯性动画时长不确定，偏短会 OCR 到中间帧、
        偏长则空等），因此以“可见关卡及其位置连续两次相同”作为稳定标志。
        只能是“确实识别到关卡且与上次一致”才算稳定：识别不到关卡时无法区分
        “仍在动画中”与“已滑出地图”，故不判定稳定，交由主循环的盲滑兜底处理；
        持续识别不到时会在超时后返回。
        """
        deadline = time.time() + max(0.0, timeout)
        last_key = self._visible_key(context, roi, order)
        while time.time() < deadline:
            time.sleep(self.SWIPE_POLL_INTERVAL)
            key = self._visible_key(context, roi, order)
            # 必须确实识别到关卡、且与上次一致，才算稳定。
            # 识别不到关卡（None）时不能视为稳定，否则滑动动画期间 OCR 短暂失败
            # 会被误判为已静止，自适应等待失效。
            if key is not None and key == last_key:
                return
            last_key = key

    def _verify_stage(
        self,
        context: Context,
        target_key: StageKey,
        verify_roi: Any,
        verify_wait: float,
    ) -> str:
        """点击后等待数秒，OCR 校验进入的关卡标题。

        比对的是解析出的关卡标识（章节号 + 关卡号 + EX 标记）而非字符串，
        因此 1-1 与 1-11 不会被混为一谈。

        返回三种结果：
          - "success"  进入的关卡与目标一致
          - "mismatch" 识别到关卡名但非目标 → 进错关卡
          - "failed"   未识别到任何关卡名（可能未进入详情或仍在加载）
        """
        time.sleep(verify_wait)

        # EX 关卡允许 OCR 漏读 EX 前缀（如 EX2-1 被读成 2-1）
        accepted = {target_key}
        if target_key.ex:
            accepted.add(target_key._replace(ex=False))

        for _ in range(self.VERIFY_RETRY):
            image = self._screencap(context)
            detail = context.run_recognition_direct(
                JRecognitionType.OCR,
                JOCR(roi=verify_roi),
                image,
            )
            if detail and detail.hit:
                keys: list[StageKey] = []
                for result in detail.all_results:
                    text = getattr(result, "text", "") or ""
                    key = self._parse_stage_key(text)
                    if key is None:
                        continue  # 忽略非关卡名格式的文本
                    keys.append(key)
                if keys:
                    if any(k in accepted for k in keys):
                        return "success"
                    return "mismatch"
            time.sleep(self.VERIFY_RETRY_INTERVAL)
        return "failed"

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
