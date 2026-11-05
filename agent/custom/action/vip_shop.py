from __future__ import annotations

import re
import time
import traceback
from dataclasses import dataclass
from typing import Any

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from maa.pipeline import JActionType, JClick, JOCR, JRecognitionType

from .general import parse_params

# 商品名归一化：去掉空白、标点，只保留中英文与数字
_NON_WORD = re.compile(r"[\W_]+", re.UNICODE)


def _normalize(text: str) -> str:
    """归一化文本，用于商品名与页面标识的模糊比较。"""
    return _NON_WORD.sub("", text or "").upper()


@dataclass
class _Cell:
    """由画面特征切出的商品格子。"""

    box: tuple[int, int, int, int]
    name: str = ""
    sold: bool = False  # 由 UI_Shop_Sold 节点识别结果标记

    @property
    def key(self) -> str:
        return _normalize(self.name)


@AgentServer.custom_action("Shop_VIP_Manager")
class ShopVipManager(CustomAction):
    """VIP 商店（专属商店）购物管理器：按画面特征定位商品格子，按名称购买指定商品。

    前置：开始时已停留在 VIP 商店商品页面（无商品详情弹窗）。

    格子识别从“整行统计 + 行带分组”改成**按格识别**（不再依赖整行灰像素总和，
    所以剩 1 列、2 列可购买时也不会漏格）：
      1. 定列：ROI 每列存在长度 >= MIN_V_RUN 的连续灰 run 即视为竖线，相邻列合并；
         相邻两条竖线起点相差约 LEFT_RIGHT_DIST(187) 配成一列，x0 = 左线起点 - 1；
      2. 定名称栏（逐格）：在该列 192 px 宽内逐行统计灰像素，取占比 >= SOLID_RATIO(85%)
         的“实心行段”，相邻两段（间隙 <= NAME_BAR_EDGE_GAP、总高 15–40 行）即名称栏，
         y0 = 上段起点 - 1。名称栏上下沿是实心灰、中间是浅灰底 + 白字、格身彩色，
         因此单格也能稳定切出；
      3. 校验底部边框（y0+BOTTOM_BORDER_Y 处有灰横条，挡掉“上一格底边框 + 下一格上沿”
         凑出的伪段）与“完整落在搜索区内”；
      4. 售罄格**不由特征切格**，而是由 UI_Shop_Sold 节点的识别框反推
         （x0 = box.x、y0 = box.y - 66），与可购买格一起进入格子列表并标记 sold。

    商品名只用来决定“这个格子里是什么”，不作为格子位置来源：OCR 一次商品区，
    把落在各格子名称栏内的文字分配给对应格子。售罄、货币不足、数量加减、关闭
    详情、获得物品弹窗、翻页全部交给 pipeline 节点（见 Scene/Do/Shop.json、
    Scene/UI/Shop.json、Scene/Do/Common.json）：
      - UI_Shop_Sold            售罄标识（与格子售罄区域重叠即为售罄）
      - UI_Shop_Confirm:Money   货币不足（价格显示红色）
      - SceneDo_Shop_Detail_Click_Max / _Plus / _Minus / _Min   数量调整
      - SceneDo_Shop_CloseInfo  关闭商品详情/弹窗
      - SceneDo_GetItem         获得物品/结算弹窗（与活动商店共用）
      - SceneDo_Shop_Swipe_Next / _Last   翻页与回首页

    参数通过节点 ``attach`` 传入（pipeline_override 时按 key 合并，而不是像
    custom_action_param 那样整体替换）；``custom_action_param`` 作为兼容回退。

    attach / custom_action_param 参数：
      - <商品名>: <购买方式>：attach 顶层键，键名即商品名（推荐写法）。多选时
        每个选项 case 各写一个键，靠 attach 的“顶层键合并”叠加。值支持：
          ``"MAX"`` / ``"max"``   买满（点 MAX 节点，回读数量行确认到上限）
          ``1``                   只买 1 份（页面默认值；回读确认是 1 就不点按钮）
          ``2`` / ``3`` …         买 N 份（按当前值与目标值点 + / -，超过上限按上限买）
          ``true``                购买，购买量沿用全局 max_quantity
          ``0`` / ``false``       不买（未勾选的 case 可直接不写这个键）
          ``{"quantity": 2}`` / ``{"max_quantity": false}``  单件参数对象
      - items: 要购买的商品名列表，也可写成逗号/换行分隔的字符串，或
        ``{"商品名": true}`` 形式的映射；为空则不购买任何商品
      - buy: 与 items 等价的映射形式。注意 attach 只合并顶层键、嵌套对象会被
        后写的整体替换，故只在同一份参数里一次性给出多个商品时才用它
      - max_quantity: 未指定份数的商品默认买满还是买 1 份（默认 true；单件参数可覆盖）
      - max_rounds: 主循环安全上限（默认 24）
      - search_roi / qty_roi / qty_count_roi / confirm_roi / marker_roi: 识别区域覆盖
      - max_node / plus_node / minus_node / min_node / sold_node / money_node /
        close_node / get_item_node / swipe_next_node / swipe_last_node:
        覆盖对应的 pipeline 节点名

    数量设置：识别沿用活动商店（OCR 数量行解析 "1/N"），点击沿用关卡扫荡
    （执行 pipeline 的 + / - / MAX 节点），每次点击后回读数量行确认到位。

    购买流程：
      1. 按格切格（竖线配对 + 格内实心段）得到可购买格，再用 UI_Shop_Sold 反推售罄格，
         OCR 一次填商品名
      2. 点击格子进入详情，按目标份数点 MAX / MIN / + / - 并回读数量行确认
      3. 点“确认购买”，获得物品弹窗交给 SceneDo_GetItem 节点
      4. 详情仍打开时用 SceneDo_Shop_CloseInfo 关闭，回到商店页面后继续下一个
      5. 本页没有目标商品时右划翻页，结束后左划翻回首页
    """

    # ---- 格子识别（按格：竖线配对定列 + 格内实心行段定名称栏）----
    # 商品格子搜索区域（商品容器可视区；格子 194x209，y0=182/400）
    SEARCH_ROI = [315, 175, 930, 440]
    CELL_W = 194
    CELL_H = 209
    # 格子灰色边框/名称栏颜色范围（BGR；边框与名称栏底色为 [48,48,48]/[49,49,49]）
    GRAY_LO = 44
    GRAY_HI = 53
    # 竖线：列内连续灰 run 最短长度、相邻列合并成一条线段的间隔
    MIN_V_RUN = 40
    BORDER_GAP = 6
    # 左右竖线起点间距（=格子宽 - 边框），配对容差
    LEFT_RIGHT_DIST = 187
    MATCH_TOL_L = 8
    # 名称栏：格内“实心灰行”（行灰占比 >= SOLID_RATIO）成对出现，上沿到下一段下沿即名称栏
    SOLID_RATIO = 0.85
    NAME_BAR_MIN_H = 15
    NAME_BAR_MAX_H = 40
    NAME_BAR_EDGE_GAP = 25
    # 底部边框相对格子顶部的 y 偏移与最小灰占比
    BOTTOM_BORDER_Y = 203
    BOTTOM_BORDER_MIN_RATIO = 0.5

    # ---- 页面 ----
    PAGE_MARKER = "专属商店"
    PAGE_MARKER_ROI = [340, 110, 200, 50]

    # ---- 商品详情 ----
    QTY_ROI = [530, 290, 580, 110]
    # 数量行 “MIN - 1/N + MAX” 的识别区域与解析规则（沿用活动商店 Shop_Activity_1_Manager）
    QTY_COUNT_ROI = [561, 353, 511, 47]
    QTY_PATTERN = re.compile(r"(\d+)\s*/\s*(\d+)")
    # 数量调整的最大轮数（每次点击后回读确认，防止界面不响应时死循环）
    QTY_MAX_ROUNDS = 12
    CONFIRM_ROI = [890, 500, 210, 70]
    CONFIRM_TEXT = "确认购买"
    QTY_LABEL = "购买数量"

    # ---- 售罄 / 货币 ----
    # 售罄标识在格子内的区域（与活动商店一致）
    SOLD_REGION = (0, 64, 194, 89)
    SOLD_OVERLAP_RATIO = 0.5
    # 售罄模板框相对格子顶部的 y 偏移（UI/Shop/sold.png 实测在格内 y+66，194x88）
    SOLD_TEMPLATE_DY = 66
    # 识别结果的最低可信分数（滤掉模板误报，如 0.36 的低分命中）
    TEMPLATE_SCORE_MIN = 0.7

    # ---- pipeline 节点（识别/点击都交给节点，可通过 attach 覆盖）----
    NODE_SOLD = "UI_Shop_Sold"
    NODE_MONEY = "UI_Shop_Confirm:Money"
    NODE_CLOSE_INFO = "SceneDo_Shop_CloseInfo"
    NODE_SWIPE_NEXT = "SceneDo_Shop_Swipe_Next"
    NODE_SWIPE_LAST = "SceneDo_Shop_Swipe_Last"
    NODE_QTY_MAX = "SceneDo_Shop_Detail_Click_Max"
    NODE_QTY_PLUS = "SceneDo_Shop_Detail_Click_Plus"
    NODE_QTY_MINUS = "SceneDo_Shop_Detail_Click_Minus"
    NODE_QTY_MIN = "SceneDo_Shop_Detail_Click_Min"
    # 获得物品/结算弹窗（通用节点，与活动商店共用）
    NODE_GET_ITEM = "SceneDo_GetItem"

    # 商品分页：最多翻几页 / 翻页后等待动画
    MAX_PAGES = 5
    SWIPE_DELAY = 1.2

    # ---- 交互与等待 ----
    LOAD_DELAY = 1.0
    SET_QTY_DELAY = 1.0
    OCR_RETRY = 4
    OCR_RETRY_INTERVAL = 0.4
    DETAIL_WAIT_RETRY = 6
    FINISH_RETRY = 12
    CONFIRM_STALL_RETRY = 6
    # 同一商品连续失败多少次后放弃
    MAX_ITEM_FAILURES = 2
    # 主循环安全上限
    MAX_ROUNDS = 24
    # 商品名匹配阈值
    MIN_PREFIX = 4
    MIN_CONTAIN = 2

    # ---- 参数 ----
    # 单品值写成该字符串（大小写不敏感）表示买满
    MAX_VALUE = "MAX"
    # attach / custom_action_param 里这些键是本管理器的参数，不会被当成商品名
    RESERVED_KEYS = frozenset(
        {
            "items",
            "buy",
            "max_quantity",
            "max_rounds",
            "close_point",
            "search_roi",
            "qty_roi",
            "confirm_roi",
            "marker_roi",
        }
    )

    # ---- 购买结果 ----
    BUY_OK = "ok"
    BUY_INSUFFICIENT = "insufficient"
    BUY_FAILED = "failed"
    BUY_UNKNOWN = "unknown"

    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        try:
            return self._run(context, argv)
        except Exception:
            # 异常必须显式返回失败，否则会被 ctypes 静默忽略导致误判成功
            traceback.print_exc()
            return CustomAction.RunResult(success=False)

    # ---------- 主流程 ----------
    def _run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        attach = self._read_attach(context, argv)
        legacy = parse_params(argv.custom_action_param)

        # ---- 商品条目：名称 + 单件参数 ----
        # 三种写法（同一份参数里可混用，同名商品按出现顺序合并参数）：
        #   1. attach 顶层键（推荐，多选项叠加）：键名即商品名，值为购买方式，
        #      见 _parse_item_spec（"MAX" / 1 / true / 0 / 参数对象）
        #   2. items: 商品名列表 / 逗号或换行分隔的字符串 / {"商品名": true} 映射
        #   3. buy: 与 items 等价的映射，仅方便一次性给出多个商品
        specs: list[tuple[str, dict[str, Any]]] = [
            (name, {})
            for name in self._parse_items(attach.get("items"))
            or self._parse_items(legacy.get("items"))
        ]
        buy_map = attach.get("buy") if isinstance(attach.get("buy"), dict) else None
        if buy_map is None and isinstance(legacy.get("buy"), dict):
            buy_map = legacy["buy"]
        if buy_map:
            specs.extend(
                (str(name), {}) for name, selected in buy_map.items() if selected
            )
        for key, value in attach.items():
            if key in self.RESERVED_KEYS:
                continue
            spec = self._parse_item_spec(value)
            if spec is not None:
                specs.append((key, spec))

        # 去重（同名合并单件参数）并保持顺序；忽略未被替换的模板占位符（如 "{items}"）
        ordered: dict[str, tuple[str, dict[str, Any]]] = {}
        for name, spec in specs:
            normalized = _normalize(name)
            if not normalized or (name.startswith("{") and name.endswith("}")):
                continue
            existing = ordered.get(normalized)
            if existing is None:
                ordered[normalized] = (name, spec)
            elif spec:
                existing[1].update(spec)
        pending = ordered  # 归一化名 → (原始名, 单件参数)

        merged = dict(legacy)
        merged.update(attach)
        max_quantity = bool(merged.get("max_quantity", True))
        max_rounds = max(1, int(merged.get("max_rounds", self.MAX_ROUNDS)))
        self._search_roi = self._parse_roi(merged.get("search_roi"), self.SEARCH_ROI)
        self._qty_roi = self._parse_roi(merged.get("qty_roi"), self.QTY_ROI)
        self._confirm_roi = self._parse_roi(
            merged.get("confirm_roi"), self.CONFIRM_ROI
        )
        self._marker_roi = self._parse_roi(
            merged.get("marker_roi"), self.PAGE_MARKER_ROI
        )
        self._qty_count_roi = self._parse_roi(
            merged.get("qty_count_roi"), self.QTY_COUNT_ROI
        )
        # pipeline 节点名可覆盖（默认见 NODE_* 常量）
        self._node_max = str(merged.get("max_node") or self.NODE_QTY_MAX)
        self._node_plus = str(merged.get("plus_node") or self.NODE_QTY_PLUS)
        self._node_minus = str(merged.get("minus_node") or self.NODE_QTY_MINUS)
        self._node_min = str(merged.get("min_node") or self.NODE_QTY_MIN)
        self._node_sold = str(merged.get("sold_node") or self.NODE_SOLD)
        self._node_money = str(merged.get("money_node") or self.NODE_MONEY)
        self._node_close = str(merged.get("close_node") or self.NODE_CLOSE_INFO)
        self._node_get_item = str(merged.get("get_item_node") or self.NODE_GET_ITEM)
        self._node_swipe_next = str(
            merged.get("swipe_next_node") or self.NODE_SWIPE_NEXT
        )
        self._node_swipe_last = str(
            merged.get("swipe_last_node") or self.NODE_SWIPE_LAST
        )

        print(
            f"[Shop_VIP_Manager] 参数: items={[name for name, _ in pending.values()]} "
            f"max_quantity={max_quantity}"
        )
        if not pending:
            print("[Shop_VIP_Manager] 未指定要购买的商品，退出")
            return CustomAction.RunResult(success=False)

        if not self._ensure_page(context):
            print("[Shop_VIP_Manager] 当前不在 VIP 商店页面，退出")
            return CustomAction.RunResult(success=False)

        done: set[str] = set()  # 已购买 / 已售罄的商品（目标名或格子名）
        failures: dict[str, int] = {}
        bought: list[str] = []
        insufficient = False
        pages_forward = 0  # 已右划的页数
        pages_back = 0  # 已回划的页数
        back_tried = False  # 回划兜底只尝试一次，避免来回摆动

        try:
            for _ in range(max_rounds):
                if all(key in done for key in pending):
                    break

                cells = self._scan_cells(context)
                if not cells:
                    # 界面可能仍在加载，稍等后重扫一次
                    time.sleep(self.OCR_RETRY_INTERVAL)
                    cells = self._scan_cells(context)
                if not cells:
                    print("[Shop_VIP_Manager] 未识别到商品格子")
                    break

                target_key: str | None = None
                cell: _Cell | None = None
                item_spec: dict[str, Any] = {}
                for key, (raw, spec) in pending.items():
                    if key in done:
                        continue
                    matched = self._best_match(cells, raw, done)
                    if matched is not None:
                        target_key = key
                        cell = matched
                        item_spec = spec
                        break

                if cell is None:
                    # 本页没有可买的了：右划找下一页；右划也翻不动时回划一次
                    # （覆盖“首列被裁、划一下才露出”的画面，如 2.png 的状态）
                    if pages_forward < self.MAX_PAGES - 1 and self._swipe_to_next_page(
                        context, cells
                    ):
                        pages_forward += 1
                        continue
                    if not back_tried and self._swipe_to_prev_page(context, cells):
                        back_tried = True
                        pages_back += 1
                        continue
                    break

                if cell.sold:
                    print(f"[Shop_VIP_Manager] 商品已售罄，跳过: {cell.name}")
                    done.add(cell.key)
                    if target_key is not None:
                        done.add(target_key)
                    continue

                print(
                    f"[Shop_VIP_Manager] 购买商品: {cell.name} (格子 {list(cell.box)})"
                )
                result = self._buy(
                    context,
                    cell,
                    self._resolve_quantity(item_spec, max_quantity),
                )
                if result == self.BUY_INSUFFICIENT:
                    insufficient = True
                    print("[Shop_VIP_Manager] 货币不足，停止购买")
                    break
                if result == self.BUY_OK:
                    bought.append(cell.name)
                    done.add(cell.key)
                    if target_key is not None:
                        done.add(target_key)
                    print(f"[Shop_VIP_Manager] 已购买: {cell.name}")
                elif result == self.BUY_UNKNOWN:
                    # 已点击确认购买但界面状态无法判定：按已处理对待，避免重复购买
                    done.add(cell.key)
                    if target_key is not None:
                        done.add(target_key)
                    print(
                        f"[Shop_VIP_Manager] 购买状态未知，停止重试以免重复购买: {cell.name}"
                    )
                else:
                    failures[cell.key] = failures.get(cell.key, 0) + 1
                    print(
                        f"[Shop_VIP_Manager] 购买失败: {cell.name} "
                        f"(第 {failures[cell.key]} 次)"
                    )
                    if failures[cell.key] >= self.MAX_ITEM_FAILURES:
                        done.add(cell.key)
                        if target_key is not None:
                            done.add(target_key)
        finally:
            self._rewind_pages(context, pages_forward - pages_back)

        remaining = [raw for key, raw in pending.items() if key not in done]
        hard_failed = [
            key for key, count in failures.items() if count >= self.MAX_ITEM_FAILURES
        ]

        if insufficient:
            print("[Shop_VIP_Manager] 货币不足，任务按成功结束")
            success = True
        elif remaining:
            print(f"[Shop_VIP_Manager] 未购买到指定商品: {remaining}")
            success = False
        elif hard_failed:
            print(f"[Shop_VIP_Manager] 存在购买失败的商品: {hard_failed}")
            success = False
        else:
            success = True

        print(
            f"[Shop_VIP_Manager] 完成: 已购买 {len(bought)} 个，成功={success}"
        )
        return CustomAction.RunResult(success=success)

    # ---------- 参数 ----------
    def _read_attach(
        self, context: Context, argv: CustomAction.RunArg
    ) -> dict[str, Any]:
        """读取当前节点的 attach（pipeline_override 时按 key 合并）。"""
        try:
            node = context.get_node_data(argv.node_name) or {}
        except Exception:
            traceback.print_exc()
            return {}
        attach = node.get("attach")
        return attach if isinstance(attach, dict) else {}

    @staticmethod
    def _parse_items(value: Any) -> list[str]:
        if isinstance(value, dict):
            return [str(name) for name, selected in value.items() if selected]
        if isinstance(value, (list, tuple, set)):
            return [str(name) for name in value if str(name).strip()]
        if isinstance(value, str):
            parts = re.split(r"[,，、;；\n\r]+", value)
            return [part.strip() for part in parts if part.strip()]
        return []

    @classmethod
    def _parse_item_spec(cls, value: Any) -> dict[str, Any] | None:
        """把 attach 顶层键的值解析成单件参数；返回 None 表示不购买该商品。

        - ``"MAX"``（大小写不敏感）→ 买满（点 MAX 节点）
        - 数字 ``N`` → 买 N 份（1 份即页面默认值，不需要点按钮）
        - ``true`` → 购买，购买量沿用全局 max_quantity
        - ``0`` / ``false`` / ``null`` / 空串 / 空对象 → 不购买
        - 对象 → 单件参数，支持 quantity / max_quantity
        """
        if isinstance(value, dict):
            return dict(value) if value else None
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            if text.upper() == cls.MAX_VALUE:
                return {"max_quantity": True}
            try:
                number = float(text)
            except ValueError:
                # 非数字的其它真值写法（如 "yes"）按“购买”处理
                return {}
            return cls._spec_from_number(number)
        if value is True:
            return {}
        if value is False or value is None:
            return None
        if isinstance(value, (int, float)):
            return cls._spec_from_number(float(value))
        return {} if value else None

    @classmethod
    def _spec_from_number(cls, number: float) -> dict[str, Any] | None:
        """数字形式的单品值：<=0 不买，其余表示买几份。"""
        if number <= 0:
            return None
        return {"quantity": max(1, int(number))}

    @staticmethod
    def _resolve_quantity(spec: dict[str, Any], global_max: bool) -> int | None:
        """单件参数 → 目标份数；返回 None 表示点 MAX 买满。"""
        if "max_quantity" in spec:
            return None if spec["max_quantity"] else 1
        if "quantity" in spec:
            try:
                return max(1, int(spec["quantity"]))
            except (TypeError, ValueError):
                print(
                    "[Shop_VIP_Manager] 单件 quantity 参数无效: "
                    f"{spec.get('quantity')!r}，按 1 份处理"
                )
                return 1
        return None if global_max else 1

    @staticmethod
    def _parse_roi(value: Any, default: list[int]) -> list[int]:
        if isinstance(value, (list, tuple)) and len(value) >= 4:
            return [int(v) for v in value[:4]]
        return list(default)

    # ---------- 一、按格切商品格子 ----------
    def _scan_cells(self, context: Context) -> list[_Cell]:
        """按格切格（可购买格）+ UI_Shop_Sold 反推售罄格 + 一次 OCR 填名称。"""
        image = self._screencap(context)
        cells = self._find_cells(image)
        sold_boxes = self._sold_boxes(context, image)
        if sold_boxes:
            self._add_sold_cells(cells, sold_boxes)
            self._mark_sold(cells, sold_boxes)
        if not cells:
            return []
        self._assign_texts(context, image, cells)
        return cells

    def _sold_boxes(self, context: Context, image: Any) -> list[tuple[int, int, int, int]]:
        """UI_Shop_Sold 节点识别售罄标识（一次截图只识别一次，按分数过滤误报）。"""
        detail = context.run_recognition(self._node_sold, image)
        if detail is None or not detail.hit:
            return []
        return self._boxes_from(detail)

    def _add_sold_cells(
        self, cells: list[_Cell], sold_boxes: list[tuple[int, int, int, int]]
    ) -> None:
        """售罄格直接由售罄标识框反推（模板位于格内 y+SOLD_TEMPLATE_DY），补进格子列表。"""
        for box in sold_boxes:
            x0 = box[0]
            y0 = box[1] - self.SOLD_TEMPLATE_DY
            cell = (x0, y0, self.CELL_W, self.CELL_H)
            if not self._fully_displayed(cell):
                continue
            if any(
                abs(x0 - other.box[0]) < 10 and abs(y0 - other.box[1]) < 10
                for other in cells
            ):
                continue
            cells.append(_Cell(cell, sold=True))
        cells.sort(key=lambda c: (c.box[1], c.box[0]))

    def _mark_sold(
        self, cells: list[_Cell], sold_boxes: list[tuple[int, int, int, int]]
    ) -> None:
        """用售罄标识框给已切出的格子打售罄标记。"""
        for cell in cells:
            x, y, _w, _h = cell.box
            off_x, off_y, sold_w, sold_h = self.SOLD_REGION
            sold_area = (x + off_x, y + off_y, sold_w, sold_h)
            for box in sold_boxes:
                overlap = self._intersection(sold_area, box)
                if overlap and overlap / (box[2] * box[3]) > self.SOLD_OVERLAP_RATIO:
                    cell.sold = True
                    break

    def _boxes_from(self, detail: Any) -> list[tuple[int, int, int, int]]:
        """从识别结果提取 box 列表（兼容 Or 等组合识别的 sub_results 递归）。"""
        boxes: list[tuple[int, int, int, int]] = []
        for result in getattr(detail, "filtered_results", None) or (
            getattr(detail, "all_results", None) or []
        ):
            if float(getattr(result, "score", 0.0) or 0.0) < self.TEMPLATE_SCORE_MIN:
                continue
            box = getattr(result, "box", None)
            if box is not None:
                boxes.append((box[0], box[1], box[2], box[3]))
            for sub in getattr(result, "sub_results", None) or []:
                sub_box = getattr(sub, "box", None)
                if sub_box is not None:
                    boxes.append((sub_box[0], sub_box[1], sub_box[2], sub_box[3]))
        return boxes

    def _swipe_page(
        self, context: Context, cells: list[_Cell], node: str, label: str
    ) -> bool:
        """执行一次翻页节点并重扫；页面内容没变化说明翻不动，返回 False。"""
        before = {cell.key for cell in cells if cell.key}
        context.run_task(node)
        time.sleep(self.SWIPE_DELAY)
        after_cells = self._scan_cells(context)
        after = {cell.key for cell in after_cells if cell.key}
        if not after or after == before:
            print(f"[Shop_VIP_Manager] {label}失败（页面无变化）")
            return False
        print(f"[Shop_VIP_Manager] {label}（{len(after)} 个格子）")
        return True

    def _swipe_to_next_page(self, context: Context, cells: list[_Cell]) -> bool:
        return self._swipe_page(context, cells, self._node_swipe_next, "翻到下一页")

    def _swipe_to_prev_page(self, context: Context, cells: list[_Cell]) -> bool:
        return self._swipe_page(context, cells, self._node_swipe_last, "回划一页")

    def _rewind_pages(self, context: Context, net_pages: int) -> None:
        """把商店翻回首页（net_pages>0 表示需要右划回去，<0 表示需要左划回去）。"""
        if net_pages == 0:
            return
        node = self._node_swipe_last if net_pages > 0 else self._node_swipe_next
        for _ in range(abs(net_pages)):
            context.run_task(node)
            time.sleep(self.SWIPE_DELAY)
        print(f"[Shop_VIP_Manager] 已把商店还原到首页（{abs(net_pages)} 页）")

    def _find_cells(self, image: Any) -> list[_Cell]:
        """按格切出可购买格子：竖线配对定列 → 格内实心行段成对定名称栏 → 校验。

        1. 竖线：ROI 每列最长连续灰 run >= MIN_V_RUN 记为竖线段（不依赖行带，
           因此列数多少、相邻列是售罄卡还是空白都不影响）；
        2. 配对：相邻两条竖线起点相差约 LEFT_RIGHT_DIST 才配成一列，x0 = 左线起点 - 1
           （只认成对竖线：单线猜测会生成错位窗口，实测会切出空名伪格）；
        3. 名称栏（逐格）：在该列 192 px 宽内逐行统计灰像素，取 >=SOLID_RATIO 的实心行段，
           相邻两段（间隙 <= NAME_BAR_EDGE_GAP、总高 NAME_BAR_MIN_H..MAX_H）即名称栏，
           y0 = 上段起点 - 1；单格与多格完全同一套判据；
        4. 校验底部边框 (y0+BOTTOM_BORDER_Y) 存在、且格子完整落在搜索区内。
        """
        height, width = image.shape[:2]
        sx, sy, sw, sh = self._search_roi
        sw = min(sw, width - sx)
        sh = min(sh, height - sy)
        if sw <= 0 or sh <= 0:
            return []
        region = image[sy : sy + sh, sx : sx + sw]
        mask = self._gray_mask(region)

        cells: list[_Cell] = []
        for x0r in self._pair_columns(self._vertical_lines(mask)):
            for band_top, _band_bottom in self._cell_name_bars(mask, x0r):
                y0 = sy + band_top - 1
                cell = (sx + x0r, y0, self.CELL_W, self.CELL_H)
                x_left = x0r + 1
                x_right = min(x0r + self.CELL_W - 1, mask.shape[1] - 1)
                if x_right <= x_left:
                    continue
                if not self._has_bottom_border(
                    mask, x_left, x_right, y0 + self.BOTTOM_BORDER_Y
                ):
                    continue
                if not self._fully_displayed(cell):
                    continue
                cells.append(_Cell(cell))

        # 去重（单边兜底候选可能与配对结果重合）
        unique: list[_Cell] = []
        for cell in cells:
            if any(
                abs(cell.box[0] - other.box[0]) < 10
                and abs(cell.box[1] - other.box[1]) < 10
                for other in unique
            ):
                continue
            unique.append(cell)
        unique.sort(key=lambda c: (c.box[1], c.box[0]))
        return unique

    def _vertical_lines(self, mask: Any) -> list[tuple[int, int]]:
        """全高扫描：每列存在长度 >= MIN_V_RUN 的连续灰 run 即视为竖线，相邻列合并成线段。"""
        hits: list[int] = []
        for x in range(mask.shape[1]):
            column = mask[:, x]
            run_start: int | None = None
            for y in range(mask.shape[0] + 1):
                value = bool(column[y]) if y < mask.shape[0] else False
                if value:
                    if run_start is None:
                        run_start = y
                elif run_start is not None:
                    if y - run_start >= self.MIN_V_RUN:
                        hits.append(x)
                    run_start = None
        segments: list[tuple[int, int]] = []
        for x in sorted(set(hits)):
            if segments and x - segments[-1][1] <= self.BORDER_GAP:
                segments[-1] = (segments[-1][0], x)
            else:
                segments.append((x, x))
        return segments

    def _pair_columns(self, segments: list[tuple[int, int]]) -> list[int]:
        """相邻两条竖线起点相差约 LEFT_RIGHT_DIST 才配成一列（x0 = 左线起点 - 1）。

        只认成对的竖线：单条竖线做“左/右边界”猜测会生成错位窗口（窗口覆盖到相邻格的
        名称栏时同样能通过实心度检查），实测会切出数个空名伪格，故不使用该兜底。
        """
        starts = [start for start, _end in segments]
        columns: list[int] = []
        for index in range(len(starts) - 1):
            if abs((starts[index + 1] - starts[index]) - self.LEFT_RIGHT_DIST) <= self.MATCH_TOL_L:
                columns.append(starts[index] - 1)
        return sorted(set(columns))

    def _cell_name_bars(self, mask: Any, x0r: int) -> list[tuple[int, int]]:
        """格内逐行统计灰像素，实心行段两两成对即名称栏（单格与多格同一判据）。"""
        left = x0r + 1
        right = min(x0r + self.CELL_W - 1, mask.shape[1])
        if right - left < 50:
            return []
        counts = mask[:, left:right].sum(axis=1)
        solid = counts >= (right - left) * self.SOLID_RATIO
        runs = self._runs(solid)
        bars: list[tuple[int, int]] = []
        for index in range(len(runs) - 1):
            top = runs[index][0]
            bottom = runs[index + 1][1]
            gap = runs[index + 1][0] - runs[index][1] - 1
            height = bottom - top + 1
            if (
                0 < gap <= self.NAME_BAR_EDGE_GAP
                and self.NAME_BAR_MIN_H <= height <= self.NAME_BAR_MAX_H
            ):
                bars.append((top, bottom))
        return bars

    def _assign_texts(
        self, context: Context, image: Any, cells: list[_Cell]
    ) -> None:
        """OCR 一次商品区，把名称文字分配给特征切出的格子（售罄由节点标记）。"""
        for text, box, _score in self._ocr(context, self._search_roi, image):
            cell = self._cell_for_name_box(cells, box)
            if cell is None:
                continue
            # 同一格出现多段文字时保留更长的一段（名称栏可能被截断成多段）
            if len(_normalize(text)) > len(cell.key):
                cell.name = text

    @staticmethod
    def _intersection(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> int:
        """两个矩形的重叠面积。"""
        x1 = max(a[0], b[0])
        y1 = max(a[1], b[1])
        x2 = min(a[0] + a[2], b[0] + b[2])
        y2 = min(a[1] + a[3], b[1] + b[3])
        if x2 <= x1 or y2 <= y1:
            return 0
        return (x2 - x1) * (y2 - y1)

    def _cell_for_name_box(
        self, cells: list[_Cell], box: tuple[int, int, int, int]
    ) -> _Cell | None:
        """把 OCR 文字框分配给名称栏包含它的格子。"""
        best: tuple[float, _Cell] | None = None
        for cell in cells:
            x, y, w, _h = cell.box
            # 名称栏：格子顶部约 33 行
            bar = (x + 1, y + 1, w - 2, 33)
            overlap = self._intersection(box, bar)
            if overlap <= 0:
                continue
            # 文字框中心落在名称栏内才算，避免把价格/装饰文字算进来
            cx, cy = box[0] + box[2] // 2, box[1] + box[3] // 2
            if not (bar[0] <= cx <= bar[0] + bar[2] and bar[1] <= cy <= bar[1] + bar[3]):
                continue
            if best is None or overlap > best[0]:
                best = (overlap, cell)
        return best[1] if best else None

    def _has_bottom_border(self, mask: Any, xl: int, xr: int, y_abs: int) -> bool:
        """校验格子底部边框存在：名称栏带下方约 203 行处有灰色横条。"""
        y0 = y_abs - self._search_roi[1]
        if y0 < 0 or y0 + 6 > mask.shape[0]:
            return False
        sub = mask[y0 : y0 + 6, xl : xr + 1]
        return sub.sum() > 6 * (xr - xl + 1) * self.BOTTOM_BORDER_MIN_RATIO

    def _fully_displayed(self, cell: tuple[int, int, int, int]) -> bool:
        """格子是否完整展示：完整落在搜索区域内（与活动商店一致）。"""
        sx, sy, sw, sh = self._search_roi
        return (
            cell[0] >= sx
            and cell[1] >= sy
            and cell[0] + cell[2] <= sx + sw
            and cell[1] + cell[3] <= sy + sh
        )

    def _gray_mask(self, region: Any) -> Any:
        """格子灰色边框/名称栏 mask（[48,48,48]/[49,49,49] 加容差）。"""
        b = region[..., 0]
        g = region[..., 1]
        r = region[..., 2]
        return (
            (r >= self.GRAY_LO)
            & (r <= self.GRAY_HI)
            & (g >= self.GRAY_LO)
            & (g <= self.GRAY_HI)
            & (b >= self.GRAY_LO)
            & (b <= self.GRAY_HI)
        )

    @staticmethod
    def _runs(on: Any) -> list[tuple[int, int]]:
        """把布尔数组中的 True 段提取为 (start, end) 列表（含端点）。"""
        runs: list[tuple[int, int]] = []
        start = None
        for i, value in enumerate(on):
            if value and start is None:
                start = i
            elif not value and start is not None:
                runs.append((start, i - 1))
                start = None
        if start is not None:
            runs.append((start, len(on) - 1))
        return runs

    # ---------- 二、按名称选格 ----------
    def _best_match(
        self, cells: list[_Cell], target: str, used: set[str]
    ) -> _Cell | None:
        target_key = _normalize(target)
        best: _Cell | None = None
        best_score = 0.0
        for cell in cells:
            if cell.key in used or not cell.key:
                continue
            score = self._name_score(target_key, cell.key)
            if score <= 0:
                continue
            if cell.sold:
                score -= 0.05
            if score > best_score:
                best_score = score
                best = cell
        return best if best_score > 0 else None

    def _name_score(self, target: str, candidate: str) -> float:
        """商品名匹配打分：完全一致 > 首尾截断 > 包含 > 公共前缀。"""
        if not target or not candidate:
            return 0.0
        if target == candidate:
            return 1.0
        short, long = sorted((target, candidate), key=len)
        if len(short) >= self.MIN_CONTAIN:
            if long.startswith(short):
                return 0.9
            if long.endswith(short):
                return 0.85
            if short in long:
                return 0.75
        lcp = 0
        for left, right in zip(target, candidate):
            if left != right:
                break
            lcp += 1
        if lcp >= self.MIN_PREFIX and lcp >= min(len(target), len(candidate)) * 0.5:
            return 0.6
        return 0.0

    # ---------- 三、购买 ----------
    def _buy(self, context: Context, cell: _Cell, quantity: int | None) -> str:
        if not self._open_detail(context, cell):
            print(f"[Shop_VIP_Manager] 打开商品详情失败: {cell.name}")
            return self.BUY_FAILED

        target = "买满" if quantity is None else f"{quantity} 份"
        if not self._set_quantity(context, quantity):
            print(f"[Shop_VIP_Manager] 设置购买数量（{target}）失败: {cell.name}")
            self._close_detail(context)
            return self.BUY_FAILED

        image = self._screencap(context)
        if self._money_insufficient(context, image):
            print("[Shop_VIP_Manager] 货币不足（UI_Shop_Confirm:Money 命中）")
            self._close_detail(context)
            return self.BUY_INSUFFICIENT

        if not self._confirm_purchase(context):
            print(f"[Shop_VIP_Manager] 未找到确认购买按钮: {cell.name}")
            self._close_detail(context)
            return self.BUY_FAILED

        return self._after_purchase(context)

    def _open_detail(self, context: Context, cell: _Cell) -> bool:
        """点击商品格子进入详情（与活动商店一致：点格子矩形中心）。"""
        self._click_box(context, cell.box)
        time.sleep(self.LOAD_DELAY)
        if self._wait_detail(context):
            return True
        # 美术动画/加载抖动时再点一次
        self._click_box(context, cell.box)
        time.sleep(self.LOAD_DELAY)
        if self._wait_detail(context):
            return True
        print(f"[Shop_VIP_Manager] 点击格子 {list(cell.box)} 后未进入详情")
        return False

    def _wait_detail(self, context: Context) -> bool:
        for _ in range(self.DETAIL_WAIT_RETRY):
            image = self._screencap(context)
            if self._detail_visible(context, image):
                return True
            time.sleep(self.OCR_RETRY_INTERVAL)
        return False

    def _detail_visible(self, context: Context, image: Any) -> bool:
        for text, _box, _score in self._ocr(context, self._qty_roi, image):
            if _normalize(self.QTY_LABEL) in _normalize(text):
                return True
        for text, _box, _score in self._ocr(context, self._confirm_roi, image):
            if _normalize(self.CONFIRM_TEXT) in _normalize(text):
                return True
        return False

    def _read_quantity(self, context: Context, image: Any) -> tuple[int, int] | None:
        """OCR 数量行解析（当前份数, 可买上限），沿用活动商店的 "1/N" 解析。"""
        for text, _box, _score in self._ocr(context, self._qty_count_roi, image):
            match = self.QTY_PATTERN.search(text)
            if match:
                return int(match.group(1)), int(match.group(2))
        return None

    def _run_quantity_node(self, context: Context, node: str, action: str) -> None:
        """执行数量控制节点（pipeline 的 TemplateMatch + Click，做法同 AutoSweep）。"""
        context.run_task(node)
        time.sleep(self.SET_QTY_DELAY)
        print(f"[Shop_VIP_Manager] 数量{action}: {node}")

    def _set_quantity(self, context: Context, quantity: int | None) -> bool:
        """把购买数量设到 quantity 份；quantity 为 None 表示买满。

        识别沿用活动商店（OCR 数量行 "1/N" 解析当前值与上限），点击沿用关卡扫荡
        （执行 pipeline 的 + / - / MAX 节点）；每次点击后重新截图回读数量，
        确认到位才返回，读不到或调不到目标值时放弃该商品，避免买错份数。
        """
        want = None if quantity is None else max(1, int(quantity))
        parsed_any = False
        min_tried = False
        for _ in range(self.QTY_MAX_ROUNDS):
            image = self._screencap(context)
            parsed = self._read_quantity(context, image)
            if parsed is None:
                time.sleep(self.OCR_RETRY_INTERVAL)
                continue
            parsed_any = True
            current, total = parsed

            if want is None:
                if total > 0 and current >= total:
                    print(f"[Shop_VIP_Manager] 数量已是最大 {current}/{total}")
                    return True
                self._run_quantity_node(context, self._node_max, "设为最大")
                continue

            if total > 0 and want > total:
                print(f"[Shop_VIP_Manager] 目标 {want} 份超过可买上限 {total}，按上限买")
                want = total
            if current == want:
                print(f"[Shop_VIP_Manager] 购买数量 {current}/{total} 已就绪")
                return True
            if current < want:
                self._run_quantity_node(context, self._node_plus, "增加")
            elif want == 1 and not min_tried:
                # 只要 1 份：直接用 MIN 归位，比连点 - 更稳（失败一次后退回点 -）
                self._run_quantity_node(context, self._node_min, "归位最小")
                min_tried = True
            else:
                self._run_quantity_node(context, self._node_minus, "减少")

        if not parsed_any:
            # 数量行一直读不到：MAX 是幂等的，仍点一次；1 份是页面默认值
            if want is None:
                print("[Shop_VIP_Manager] 读不到数量行，直接点 MAX")
                self._run_quantity_node(context, self._node_max, "设为最大")
                return True
            if want == 1:
                print("[Shop_VIP_Manager] 读不到数量行，1 份是页面默认值，继续")
                return True
            print(f"[Shop_VIP_Manager] 读不到数量行，无法把数量调到 {want} 份，放弃该商品")
            return False
        if want is None:
            print("[Shop_VIP_Manager] 已点击 MAX 但未回读到上限，按已点 MAX 继续")
            return True
        print(f"[Shop_VIP_Manager] 数量未能调到 {want} 份，放弃该商品")
        return False

    def _confirm_purchase(self, context: Context) -> bool:
        expected = _normalize(self.CONFIRM_TEXT)
        for _ in range(self.OCR_RETRY):
            image = self._screencap(context)
            for text, box, _score in self._ocr(context, self._confirm_roi, image):
                if expected in _normalize(text):
                    self._click_box(context, box)
                    time.sleep(0.5)
                    return True
            time.sleep(self.OCR_RETRY_INTERVAL)
        return False

    def _after_purchase(self, context: Context) -> str:
        stalled = 0
        for _ in range(self.FINISH_RETRY):
            # 获得物品/结算弹窗交给 pipeline 的 SceneDo_GetItem 节点
            context.run_task(self._node_get_item)
            image = self._screencap(context)
            if self._is_page(context, image):
                return self.BUY_OK
            if self._detail_visible(context, image):
                if self._money_insufficient(context, image):
                    print("[Shop_VIP_Manager] 检测到货币不足提示")
                    self._close_detail(context)
                    return self.BUY_INSUFFICIENT
                stalled += 1
                if stalled >= self.CONFIRM_STALL_RETRY:
                    print("[Shop_VIP_Manager] 详情长时间未变化，停止等待")
                    break
                time.sleep(0.5)
                continue
            # 既不在列表也不在详情：可能还有后续弹窗，再让节点处理一轮
            stalled = 0
            time.sleep(self.OCR_RETRY_INTERVAL)

        image = self._screencap(context)
        if self._detail_visible(context, image):
            self._close_detail(context)
        image = self._screencap(context)
        if self._is_page(context, image):
            return self.BUY_OK
        print("[Shop_VIP_Manager] 购买后未能确认回到商店页面")
        return self.BUY_UNKNOWN

    def _money_insufficient(self, context: Context, image: Any) -> bool:
        """货币是否不足：交给 UI_Shop_Confirm:Money 节点（红色价格）判断。"""
        detail = context.run_recognition(self._node_money, image)
        return bool(detail is not None and detail.hit)

    def _close_detail(self, context: Context) -> None:
        """关闭商品详情/弹窗：交给 SceneDo_Shop_CloseInfo 节点（点“点击空白区域关闭弹窗”）。"""
        for _ in range(3):
            context.run_task(self._node_close)
            time.sleep(self.LOAD_DELAY)
            image = self._screencap(context)
            if not self._detail_visible(context, image):
                return
        print("[Shop_VIP_Manager] 关闭详情失败")

    # ---------- 页面 ----------
    def _is_page(self, context: Context, image: Any) -> bool:
        expected = _normalize(self.PAGE_MARKER)
        for text, _box, _score in self._ocr(context, self._marker_roi, image):
            if expected in _normalize(text):
                return True
        return False

    def _ensure_page(self, context: Context) -> bool:
        for index in range(3):
            image = self._screencap(context)
            if self._is_page(context, image):
                return True
            if self._detail_visible(context, image):
                self._close_detail(context)
            time.sleep(self.OCR_RETRY_INTERVAL)
            print(f"[Shop_VIP_Manager] 等待商店页面 ({index + 1}/3)")
        return False

    # ---------- 工具 ----------
    def _screencap(self, context: Context) -> Any:
        """主动刷新截图并返回（BGR）"""
        context.tasker.controller.post_screencap().wait()
        return context.tasker.controller.cached_image

    def _ocr(
        self, context: Context, roi: list[int], image: Any
    ) -> list[tuple[str, tuple[int, int, int, int], float]]:
        detail = context.run_recognition_direct(
            JRecognitionType.OCR, JOCR(roi=list(roi)), image
        )
        if not (detail and detail.hit):
            return []
        results: list[tuple[str, tuple[int, int, int, int], float]] = []
        source = getattr(detail, "filtered_results", None) or (
            getattr(detail, "all_results", None) or []
        )
        for result in source:
            text = (getattr(result, "text", "") or "").strip()
            box = getattr(result, "box", None)
            if not text or box is None:
                continue
            results.append(
                (
                    text,
                    tuple(int(v) for v in box),
                    float(getattr(result, "score", 0.0) or 0.0),
                )
            )
        return results

    def _click_box(self, context: Context, box: tuple[int, int, int, int]) -> None:
        x, y, w, h = box
        self._click_point(context, (x + w // 2, y + h // 2))

    def _click_point(self, context: Context, point: tuple[int, int]) -> None:
        context.run_action_direct(
            JActionType.Click, JClick(), (int(point[0]), int(point[1]), 1, 1), ""
        )
