from __future__ import annotations

import json
import random
from typing import Any

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_recognition import CustomRecognition


@AgentServer.custom_recognition("Common_AllOfIntersect")
class AllOfIntersectRecognition(CustomRecognition):
    """通用组合识别：多个子识别“同时命中”的重叠部分，再按 order_by / index 取一个。

    子识别的执行完全交给 MaaFramework：每个子识别都作为一个临时节点跑
    `context.run_recognition`（参数解析、默认值补全、阈值/连通域判定、调试图
    都由框架负责），本识别器只负责“收集每个子识别的全部命中框 -> 求交集 ->
    排序 -> 输出一个框”。

    语义相当于一个“能列出全部交集候选”的 And：
      - **第一个子识别**的结果框作为候选（比如 TemplateMatch 的每个按钮框）；
      - 候选框若与其余每个子识别都有结果框重叠（交集面积占候选框面积
        ≥ min_overlap），才算“同时命中”；
      - 通过的候选按 order_by 排序，index 选第几个，返回它的框。

    custom_recognition_param:
      - all_of: list<string | object>  必选，至少 2 个
          string: 已存在的 pipeline 节点名，直接跑该节点的识别
          object:
            - {"type": "TemplateMatch", "param": {...}}  内联识别定义
            - {"recognition": {...}, ...}                也可直接写节点体
      - order_by: "Vertical"(默认) | "Horizontal" | "Area" | "Random"
          作用于返回的框（`box_from` 指定的那个）
      - index: 取第几个，默认 0；支持负数（同框架规则，-1 为最后一个）
      - box_from: 返回第几个子识别的框，默认 0（即候选框本身，通常是模板框）
      - min_overlap: 交集面积占候选框面积的最小比例，默认 0（有任何重叠即可）

    返回 detail:
      - candidates: 全部通过的框（已排序，元素为各子识别对应的框列表）
      - index: 选中的下标
      - order_by: 使用的排序方式
    """

    TEMP_NODE_PREFIX = "__Common_AllOfIntersect_sub"

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult | None:
        params = self._load_params(argv.custom_recognition_param)
        subs = params.get("all_of") or []
        if not isinstance(subs, list) or len(subs) < 2:
            return None

        min_overlap = float(params.get("min_overlap", 0.0))
        box_from = int(params.get("box_from", 0))
        order_by = str(params.get("order_by", "Vertical"))
        index = int(params.get("index", 0))

        # 逐个交给框架识别，收集全部命中框
        results = [
            self._boxes(self._run_sub(context, argv, i, sub))
            for i, sub in enumerate(subs)
        ]

        base = results[0]
        if not base:
            return None

        # 交集：候选框必须与其余每个子识别都有结果框重叠
        candidates: list[list[list[int]]] = []
        for box in base:
            pair = [box]
            for other in results[1:]:
                partner = self._best_overlap(box, other, min_overlap)
                if partner is None:
                    break
                pair.append(partner)
            else:
                candidates.append(pair)

        if not candidates:
            return None
        if not 0 <= box_from < len(subs):
            box_from = 0

        candidates = self._sort(candidates, order_by, box_from)
        if index < 0:
            index += len(candidates)
        if not 0 <= index < len(candidates):
            return None

        chosen = candidates[index][box_from]
        return CustomRecognition.AnalyzeResult(
            box=(chosen[0], chosen[1], chosen[2], chosen[3]),
            detail={
                "candidates": candidates,
                "index": index,
                "order_by": order_by,
            },
        )

    # -----
    # region 子识别（交给框架执行）
    # -----

    def _run_sub(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
        index: int,
        sub: Any,
    ) -> Any:
        """执行一个子识别；返回 RecognitionDetail（失败为 None）。

        字符串 -> 直接跑已有节点；对象 -> 包成一个临时节点交给框架，
        由框架完成参数解析与默认值补全。
        """
        if isinstance(sub, str):
            return context.run_recognition(sub, argv.image)
        if not isinstance(sub, dict):
            return None

        if "recognition" in sub:  # 已是节点体
            node = dict(sub)
        elif "type" in sub:  # {"type": ..., "param": {...}}
            param = sub.get("param")
            if param is None:
                param = {k: v for k, v in sub.items() if k != "type"}
            node = {"recognition": {"type": sub["type"], "param": param}}
        else:
            return None

        name = f"{self.TEMP_NODE_PREFIX}{argv.node_name}_{index}"
        # 先把临时节点注册进当前任务的 pipeline（框架据此补全参数解析/默认值），
        # 再交给框架执行识别；两次都带 override，兼容只接受其中一种的版本。
        try:
            context.override_pipeline({name: node})
        except (RuntimeError, ValueError, TypeError):
            pass
        return context.run_recognition(name, argv.image, {name: node})

    @staticmethod
    def _boxes(detail: Any) -> list[list[int]]:
        """识别详情 -> [[x, y, w, h], ...]（取全部结果，退化为过滤后结果）。

        注意：`RecognitionDetail.box` 是 Rect，但 `all_results` 里的元素由框架
        原始 JSON 直接反序列化，`box` 可能是 list[int]，也可能被转成 Rect，
        这里两种都接受。
        """
        if not detail or not getattr(detail, "hit", False):
            return []
        boxes: list[list[int]] = []
        for result in detail.all_results or detail.filtered_results:
            box = AllOfIntersectRecognition._rect(getattr(result, "box", None))
            if box is not None:
                boxes.append(box)
        return boxes

    @staticmethod
    def _rect(value: Any) -> list[int] | None:
        """把 Rect / [x, y, w, h] / {"x": ...} 统一成 [x, y, w, h]。"""
        if value is None:
            return None
        if isinstance(value, dict):
            try:
                box = [int(value[k]) for k in ("x", "y", "w", "h")]
            except (KeyError, TypeError, ValueError):
                return None
        elif isinstance(value, (list, tuple)):
            if len(value) < 4:
                return None
            try:
                box = [int(v) for v in value[:4]]
            except (TypeError, ValueError):
                return None
        else:
            try:
                box = [int(value.x), int(value.y), int(value.w), int(value.h)]
            except (AttributeError, TypeError, ValueError):
                return None
        if box[2] <= 0 or box[3] <= 0:
            return None
        return box

    # -----
    # region 几何 / 排序
    # -----

    @staticmethod
    def _intersection(a: list[int], b: list[int]) -> int:
        x0 = max(a[0], b[0])
        y0 = max(a[1], b[1])
        x1 = min(a[0] + a[2], b[0] + b[2])
        y1 = min(a[1] + a[3], b[1] + b[3])
        if x1 <= x0 or y1 <= y0:
            return 0
        return (x1 - x0) * (y1 - y0)

    def _best_overlap(
        self,
        box: list[int],
        others: list[list[int]],
        min_overlap: float,
    ) -> list[int] | None:
        """在 others 里找与 box 重叠最多、且达到 min_overlap 的框。"""
        area = box[2] * box[3]
        best: list[int] | None = None
        best_area = 0
        for other in others:
            inter = self._intersection(box, other)
            if inter <= 0 or inter < area * min_overlap:
                continue
            if inter > best_area:
                best, best_area = other, inter
        return best

    @staticmethod
    def _sort(
        candidates: list[list[list[int]]],
        order_by: str,
        box_from: int,
    ) -> list[list[list[int]]]:
        key = order_by.lower()
        if key == "random":
            out = list(candidates)
            random.shuffle(out)
            return out
        if key == "area":
            return sorted(candidates, key=lambda c: -(c[box_from][2] * c[box_from][3]))
        if key == "horizontal":
            return sorted(candidates, key=lambda c: (c[box_from][0], c[box_from][1]))
        # 默认 Vertical：最靠上的优先，同一行从左到右
        return sorted(candidates, key=lambda c: (c[box_from][1], c[box_from][0]))

    @staticmethod
    def _load_params(param: Any) -> dict[str, Any]:
        if not param:
            return {}
        if isinstance(param, str):
            try:
                data = json.loads(param)
            except json.JSONDecodeError:
                return {}
            return data if isinstance(data, dict) else {}
        return dict(param)
