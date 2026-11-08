from __future__ import annotations

import copy
import datetime as dt
import difflib
import re
import time
import traceback
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import numpy as np

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from maa.pipeline import JOCR, JRecognitionType

from .general import log_message, parse_params

# ---------------------------------------------------------------------------
# 常量与小工具
# ---------------------------------------------------------------------------

#: 北京时间。游戏日在北京时间 05:00 切换，这里固定 UTC+8 而不依赖 tzdata
BEIJING = dt.timezone(dt.timedelta(hours=8))

#: 游戏日切换时刻（北京时间小时数）
GAME_DAY_START_HOUR = 5

#: 互动履历的日期列，形如 ``2026.11.07 02:46:10``
_DATE_RE = re.compile(
    r"(\d{4})\s*[.\-/年]\s*(\d{1,2})\s*[.\-/月]\s*(\d{1,2})\s*日?\D{0,4}"
    r"(\d{1,2})\s*[:：]\s*(\d{1,2})(?:\s*[:：]\s*(\d{1,2}))?"
)

#: 提取任意整数（友情点、“0/20” 这类文本都用它）
_INT_RE = re.compile(r"\d+")

#: 文本归一化（去掉空白与标点，只保留中英文与数字，用于名字模糊比较）
_NON_WORD = re.compile(r"[\W_]+", re.UNICODE)

#: 互动履历里的记录类型
KIND_RECEIVE = "receive"  # 获赠（别人送我，需要回礼）
KIND_SEND = "send"  # 赠送（我送别人）
KIND_UNKNOWN = "unknown"


def _normalize(text: str) -> str:
    """归一化文本，用于玩家名与页面文本的模糊比较。"""
    return _NON_WORD.sub("", text or "").upper()


def _game_day(moment: dt.datetime, hour: int = GAME_DAY_START_HOUR) -> dt.date:
    """按游戏日换算日期（凌晨 5 点前算前一天）。"""
    return (moment - dt.timedelta(hours=hour)).date()


def _now_beijing() -> dt.datetime:
    """当前北京时间（naive，便于和画面上的时间戳直接比较）。"""
    return dt.datetime.now(dt.timezone.utc).astimezone(BEIJING).replace(tzinfo=None)


def _runs(on: Any) -> list[tuple[int, int]]:
    """把布尔数组里的 True 段提取成 (start, end) 列表（含端点）。"""
    runs: list[tuple[int, int]] = []
    start = None
    for index, value in enumerate(on):
        if value and start is None:
            start = index
        elif not value and start is not None:
            runs.append((start, index - 1))
            start = None
    if start is not None:
        runs.append((start, len(on) - 1))
    return runs


@dataclass
class Geometry:
    """好友列表名片格子的几何参数。

    数值来自 ``assets/resource/image/0.png``（单个格子 1077x131）与
    ``assets/resource/image/1.png``（好友界面 1280x720）实测。
    """

    # ---- 格子 ----
    cell_left: int = 19  # 列表左沿 = 格子左边
    cell_w: int = 1077  # 格子宽（0.png 尺寸）
    cell_h: int = 131  # 格子高
    list_top: int = 110  # 列表可视区上沿（与 SendGift 的赠送按钮 ROI 起点一致）
    list_bottom: int = 690  # 列表可视区下沿（再往下会被裁掉）

    # ---- 头像白框（0.png 实测 37..160 / 4..127，即 124x124 的圆角白边）----
    frame_w: int = 124
    frame_h: int = 124
    frame_right_offset: int = 158  # 白框右竖线相对格子左边
    frame_top_offset: int = 4  # 白框上沿相对格子上边
    frame_bottom_offset: int = 127  # 白框下沿相对格子上边
    frame_scan_w: int = 200  # 从列表左沿向右扫描白框的宽度
    frame_min_run: int = 100  # 右竖线最短连续白像素（整格时约 124）
    white_min: int = 220  # 近白阈值（RGB 三通道都 >= 该值）
    border_gap: int = 6  # 相邻列合并成一条边线
    run_y_tolerance: int = 8  # 合并同一条边线时允许的 y 偏差
    edge_tolerance: int = 6  # 上下沿推算出的格子 y 允许的偏差
    bottom_border_rows: int = 3  # 校验下边框用的行数
    bottom_border_ratio: float = 0.8  # 下边框白色占比下限

    # ---- 名字 / UID / 赠送按钮（相对格子）----
    name_roi: tuple[int, int, int, int] = (185, 4, 185, 31)
    uid_roi: tuple[int, int, int, int] = (185, 32, 185, 26)
    uid_center_offset: int = 45  # UID 文字中心相对格子顶部（无白框时用它反推格子）
    gift_roi: tuple[int, int, int, int] = (960, 18, 112, 108)  # “赠送”按钮
    name_band: tuple[int, int] = (-2, 31)  # 名字文字中心相对格子顶部的取值范围
    uid_band: tuple[int, int] = (32, 63)  # UID 文字中心相对格子顶部的取值范围

    def gift_box(self, cell: Sequence[int]) -> list[int]:
        """格子里“赠送”按钮的识别区域（绝对坐标）。"""
        x, y = cell[0] + self.gift_roi[0], cell[1] + self.gift_roi[1]
        return [x, y, self.gift_roi[2], self.gift_roi[3]]

    def usable(self, cell: Sequence[int], width: int, height: int) -> bool:
        """格子的“赠送”按钮是否完整落在可视区内（否则可能是被裁掉的半格）。"""
        if cell[0] < 0 or cell[0] + self.cell_w > width:
            return False
        top = cell[1] + self.gift_roi[1]
        bottom = top + self.gift_roi[3]
        return top >= self.list_top and bottom <= min(height, self.list_bottom)


@dataclass
class _Cell:
    """好友列表里的一个名片格子。"""

    box: tuple[int, int, int, int]
    name: str = ""
    uid: str = ""

    @property
    def key(self) -> str:
        return _normalize(self.name)

    @property
    def uid_key(self) -> str:
        return _normalize(self.uid)


@dataclass
class _Record:
    """互动履历里的一条记录。"""

    name: str
    points: int | None = None
    moment: dt.datetime | None = None
    kind: str = KIND_UNKNOWN
    raw: str = ""

    @property
    def day(self) -> dt.date | None:
        return None if self.moment is None else _game_day(self.moment)


#: 互动履历记录区（不含表头与页脚，实测自 assets/resource/image/2.png）
HISTORY_ROI = [205, 242, 858, 328]

#: 记录区各列的 x 分界（玩家名称 / 类型 / 友情点 / 日期）
HISTORY_NAME_X = 460
HISTORY_TYPE_X = 585
HISTORY_POINTS_X = 730
HISTORY_DATE_X = 775  # 日期列起点，用来判断一段文字是不是日期

#: 同一行内文字中心 y 的容差（行距约 40）
HISTORY_ROW_TOLERANCE = 18


def parse_history_rows(
    texts: list[tuple[str, tuple[int, int, int, int], float]],
) -> list[_Record]:
    """把互动履历记录区的 OCR 结果按行拼成记录。

    以“日期”列的文字框作为行锚点（日期字符串最长最有辨识度），
    再把同一行里落在 玩家名称 / 类型 / 友情点 列的其它文字归到这一行。
    """
    dates: list[tuple[float, dt.datetime, str]] = []
    others: list[tuple[float, float, str]] = []
    for text, box, _score in texts:
        cx = box[0] + box[2] / 2.0
        cy = box[1] + box[3] / 2.0
        moment = FriendReturnGift._parse_datetime(text)
        if moment is not None and cx >= HISTORY_DATE_X:
            dates.append((cy, moment, text))
        else:
            others.append((cx, cy, text))

    records: list[_Record] = []
    for cy, moment, raw in dates:
        name_parts: list[tuple[float, str]] = []
        type_parts: list[tuple[float, str]] = []
        point_parts: list[tuple[float, str]] = []
        for cx, ocy, text in others:
            if abs(ocy - cy) > HISTORY_ROW_TOLERANCE:
                continue
            if cx < HISTORY_NAME_X:
                name_parts.append((cx, text))
            elif cx < HISTORY_TYPE_X:
                type_parts.append((cx, text))
            elif cx < HISTORY_POINTS_X:
                point_parts.append((cx, text))
        type_text = "".join(text for _cx, text in sorted(type_parts))
        records.append(
            _Record(
                name="".join(text for _cx, text in sorted(name_parts)),
                points=FriendReturnGift._parse_points(
                    "".join(text for _cx, text in sorted(point_parts)), type_text
                ),
                moment=moment,
                kind=FriendReturnGift._parse_kind(type_text),
                raw=raw,
            )
        )
    return records


def assign_cell_texts(
    texts: list[tuple[str, tuple[int, int, int, int], float]],
    cells: list[_Cell],
    geo: Geometry,
) -> None:
    """把一次 OCR 的结果按格子 y 区段归属成“名字”与“UID”。"""
    for cell in cells:
        name_parts: list[tuple[float, str]] = []
        uid_parts: list[tuple[float, str]] = []
        for text, box, _score in texts:
            relative_y = box[1] + box[3] / 2.0 - cell.box[1]
            if geo.name_band[0] <= relative_y <= geo.name_band[1]:
                name_parts.append((box[0], text))
            elif geo.uid_band[0] <= relative_y <= geo.uid_band[1]:
                uid_parts.append((box[0], text))
        cell.name = "".join(text for _x, text in sorted(name_parts)).strip()
        cell.uid = "".join(text for _x, text in sorted(uid_parts)).strip()


def _white_mask(image: Any, white_min: int) -> Any:
    """近白像素 mask（头像白框、下边框都是近白）。"""
    return (
        (image[..., 0] >= white_min)
        & (image[..., 1] >= white_min)
        & (image[..., 2] >= white_min)
    )


def _group_border_columns(
    hits: list[tuple[int, int, int]], gap: int, y_tolerance: int
) -> list[dict[str, int]]:
    """把“列 + 竖直白 run”分组：相邻列且 y 范围相近的算同一条边线。"""
    groups: list[dict[str, int]] = []
    for x, y_top, y_bot in hits:
        for group in groups:
            if (
                abs(x - group["x_last"]) <= gap
                and abs(y_top - group["y_top"]) <= y_tolerance
                and abs(y_bot - group["y_bot"]) <= y_tolerance
            ):
                group["x_last"] = max(group["x_last"], x)
                group["y_top"] = min(group["y_top"], y_top)
                group["y_bot"] = max(group["y_bot"], y_bot)
                break
        else:
            groups.append({"x_first": x, "x_last": x, "y_top": y_top, "y_bot": y_bot})
    return groups


def _bottom_border_ok(mask: Any, x_right: int, y_bottom: int, geo: Geometry) -> bool:
    """校验头像白框的下边框：白框宽度范围内横向近白像素占比足够高。

    头像图片本身也可能有竖着的白色亮带（会误判成右竖线），
    但很少同时有一条横贯整个白框宽度的白线，所以用它兜底。
    """
    x_lo = max(0, x_right - geo.frame_w + 1)
    x_hi = min(mask.shape[1], x_right + 2)
    y_lo = max(0, y_bottom - geo.bottom_border_rows + 1)
    y_hi = min(mask.shape[0], y_bottom + 1)
    if x_hi <= x_lo or y_hi <= y_lo:
        return False
    return float(mask[y_lo:y_hi, x_lo:x_hi].mean()) >= geo.bottom_border_ratio


def find_cells(image: Any, geo: Geometry) -> list[tuple[int, int, int, int]]:
    """从好友列表截图里切出名片格子。

    以头像白框为锚点（白框是 124x124 的圆角白边，左上角被等级数字挡住，
    但**右竖线**与**下边框**始终存在）：

    1. 在列表左侧 ``frame_scan_w`` 宽度内，逐列找长度 >= ``frame_min_run`` 的
       连续近白 run（同一格子的右竖线是一条 124 高的白线），相邻列合并成边线；
    2. 同一条边线上不同的 y 段对应不同的格子，因此按 y 范围分组；
    3. 由“白框右竖线 + 白框上沿/下沿”反推格子左上角
       ``x0 = 右竖线 x - 158``、``y0 = 白框上沿 - 4``；
       顶端被列表裁掉时改用下沿反推（``y0 = 白框下沿 - 127``）；
    4. 校验下边框、且“赠送”按钮完整落在可视区内（半格不用，滑动后会再来）。

    白框找不到（例如名片皮肤不是白色）时返回空列表，由调用方退化到
    UID 文字锚点。
    """
    height, width = image.shape[:2]
    y_lo = max(0, geo.list_top)
    y_hi = min(height, geo.list_bottom)
    x_lo = max(0, geo.cell_left)
    x_hi = min(width, geo.cell_left + geo.frame_scan_w)
    if y_hi - y_lo < geo.frame_min_run or x_hi <= x_lo:
        return []

    mask = _white_mask(image, geo.white_min)
    hits: list[tuple[int, int, int]] = []
    for x in range(x_lo, x_hi):
        column = mask[y_lo:y_hi, x]
        for start, end in _runs(column):
            if end - start + 1 >= geo.frame_min_run:
                hits.append((x, y_lo + start, y_lo + end))
    if not hits:
        return []

    cells: list[tuple[int, int, int, int]] = []
    for group in _group_border_columns(hits, geo.border_gap, geo.run_y_tolerance):
        x_right = group["x_first"]
        y_top, y_bot = group["y_top"], group["y_bot"]
        if not _bottom_border_ok(mask, x_right, y_bot, geo):
            continue
        from_top = y_top - geo.frame_top_offset
        from_bottom = y_bot - geo.frame_bottom_offset
        if abs(from_top - from_bottom) <= geo.edge_tolerance:
            y0 = int(round((from_top + from_bottom) / 2))
        elif y_top <= geo.list_top + 3:
            # 格子顶端被列表裁掉：右竖线从可视区上沿才开始，只能用下边框反推
            y0 = from_bottom
        else:
            # 上下不一致且不是“顶端被裁”，说明这条白线不是头像白框
            continue
        cell = (x_right - geo.frame_right_offset, y0, geo.cell_w, geo.cell_h)
        if not geo.usable(cell, width, height):
            continue
        if any(
            abs(cell[0] - other[0]) < 10 and abs(cell[1] - other[1]) < 20
            for other in cells
        ):
            continue
        cells.append(cell)
    cells.sort(key=lambda item: item[1])
    return cells


# ---------------------------------------------------------------------------
# Custom Action
# ---------------------------------------------------------------------------


@AgentServer.custom_action("Friend_ReturnGift")
class FriendReturnGift(CustomAction):
    """自动回礼：扫描“互动履历”，按时间先后给获赠友情点的好友回礼。

    流程（全部在本 Custom 内编排，底层动作仍交给 pipeline 节点）：

    1. **扫描互动履历**
       - 执行 ``SceneDo_Click_Friend_InteractionHistory`` 打开互动履历；
       - 截图 OCR 记录区，按“日期”列分行，识别每行的 玩家名称 / 类型 /
         友情点 / 日期；
       - 反复执行 ``ReturnGiftHistory_SwipeNext`` 向下滚动列表，直到
         出现比目标游戏日更早的记录、或连续两次滚动内容不再变化（到底）；
       - 执行 ``SceneDo_Close_Friend_InteractionHistory`` 回到好友列表；
       - 只保留“获赠”且友情点不为 0、日期落在目标游戏日的记录，
         按时间先后排序（同一赠送者只回礼一次）。
    2. **逐个回礼**
       - 截图并建立名片格子（见 :class:`Geometry` / :func:`find_cells`）；
       - OCR 格子里的玩家名，找到目标好友；
       - 用 ``ReturnGiftFriend_Sendable``（与 ``SendGiftDo`` 同样的
         “赠送按钮模板 ∩ 金色连通块”识别，ROI 换成该格子的按钮区）判断
         是否可赠送：可赠送就点击，否则说明今天已经送过，跳过；
       - 本页没有目标好友时执行 ``ReturnGiftFriend_SwipeNext`` 向上滑动列表，
         连续两次滑动后可见好友不再变化即认为已遍历整个好友列表；
       - 下一个好友开始前先 ``SceneDo_Click_Friend_AddFriend`` 切页、
         等一秒再 ``SceneDo_Click_Friend_FriendList`` 切回来，瞬间回到顶部；
       - 每次赠送后读取 ``ReturnGiftQuota``（今日赠礼 X/Y），
         达到上限或全部回礼完毕即结束。

    参数通过节点 ``attach`` 传入（``pipeline_override`` 按 key 合并），
    ``custom_action_param`` 作为兼容回退，两者同时存在时 attach 优先：

    - ``day``: 目标游戏日偏移，``0`` = 当天、``1`` = 昨天（默认 1），
      以此类推；游戏日按北京时间 05:00 切换
    - ``dry_run``: ``true`` 时只扫描不赠送，用于调试
    - ``max_gifts``: 最多赠送几次，默认取页面上的每日上限（20）
    - ``max_history_scrolls`` / ``max_friend_swipes``: 两个列表的滑动上限
    - ``settle_interval``: 每次页面操作后的等待（秒）
    - ``history_open_node`` / ``history_close_node`` / ``history_selected_node`` /
      ``history_swipe_node`` / ``friend_swipe_node`` / ``sendable_node`` /
      ``quota_node`` / ``add_friend_node`` /
      ``friend_list_node`` / ``friend_list_selected_node``: 覆盖默认节点名
    - ``geometry``: 覆盖 :class:`Geometry` 字段（例如 ``{"list_bottom": 700}``）
    """

    # ---- 默认值 ----
    DEFAULT_DAY = 1
    MAX_HISTORY_SCROLLS = 25
    MAX_FRIEND_SWIPES = 30
    REACH_BOTTOM_STALLS = 2  # 连续两次滑动内容不变 => 到底
    SETTLE_INTERVAL = 0.8
    SWIPE_DELAY = 1.0
    GIFT_DELAY = 1.2
    TAB_SWITCH_DELAY = 1.0
    HISTORY_OPEN_RETRY = 8
    FRIEND_LIST_RETRY = 6
    CLICK_VERIFY_RETRY = 6
    MAX_HISTORY_RECORDS = 120
    NAME_MATCH_MIN_SCORE = 0.6

    # ---- pipeline 节点 ----
    NODE_HISTORY_OPEN = "SceneDo_Click_Friend_InteractionHistory"
    NODE_HISTORY_CLOSE = "SceneDo_Close_Friend_InteractionHistory"
    NODE_HISTORY_SELECTED = "UI_Friend_InteractionHistory_Selected"
    NODE_HISTORY_SWIPE = "ReturnGiftHistory_SwipeNext"
    NODE_FRIEND_SWIPE = "ReturnGiftFriend_SwipeNext"
    NODE_FRIEND_SENDABLE = "ReturnGiftFriend_Sendable"
    NODE_QUOTA = "ReturnGiftQuota"
    NODE_ADD_FRIEND = "SceneDo_Click_Friend_AddFriend"
    NODE_FRIEND_LIST = "SceneDo_Click_Friend_FriendList"
    NODE_FRIEND_LIST_SELECTED = "UI_Friend_FriendList_Selected"

    def __init__(self) -> None:
        super().__init__()  # 初始化基类 _handle（AgentServer 注册时需要 c_handle）
        self.geo = Geometry()
        self._day = self.DEFAULT_DAY
        self._dry_run = False
        self._max_gifts: int | None = None
        self._max_history_scrolls = self.MAX_HISTORY_SCROLLS
        self._max_friend_swipes = self.MAX_FRIEND_SWIPES
        self._settle_interval = self.SETTLE_INTERVAL
        self._swipe_delay = self.SWIPE_DELAY
        self._node_names: dict[str, str] = {}
        self._gifted = 0

    # ------------------------------------------------------------------
    # 入口
    # ------------------------------------------------------------------
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
        self._load_params(context, argv)

        target_day = self._target_day()
        log_message(
            f"[Friend_ReturnGift] 目标游戏日 {target_day.isoformat()}"
            f"（day={self._day}，游戏日北京时间 {GAME_DAY_START_HOUR:02d}:00 切换，"
            f"现在 {_now_beijing():%Y-%m-%d %H:%M}）"
        )

        if not self._ensure_friend_list(context):
            log_message("[Friend_ReturnGift] 当前不在好友列表，任务失败")
            return CustomAction.RunResult(success=False)

        records = self._scan_history(context, target_day)
        if records is None:
            log_message("[Friend_ReturnGift] 打开互动履历失败，任务失败")
            return CustomAction.RunResult(success=False)

        if not records:
            log_message(
                "[Friend_ReturnGift] 目标时间范围内没有需要回礼的好友，任务结束"
            )
            return CustomAction.RunResult(success=True)

        log_message(
            "[Friend_ReturnGift] 需要回礼的好友（按时间先后）："
            + "、".join(record.name for record in records)
        )

        if self._dry_run:
            log_message("[Friend_ReturnGift] dry_run 已开启，只扫描不赠送")
            return CustomAction.RunResult(success=True)

        success = self._return_gifts(context, records)
        log_message(
            f"[Friend_ReturnGift] 回礼结束：成功赠送 {self._gifted} 人，"
            f"目标 {len(records)} 人"
        )
        return CustomAction.RunResult(success=success)

    # ------------------------------------------------------------------
    # 参数
    # ------------------------------------------------------------------
    def _load_params(self, context: Context, argv: CustomAction.RunArg) -> None:
        legacy = parse_params(argv.custom_action_param)
        merged: dict[str, Any] = dict(legacy)
        merged.update(self._read_attach(context, argv))

        # 每次都从默认几何开始，避免上一次运行（或上一次 attach）的覆盖残留
        self.geo = Geometry()
        self._day = self._as_int(merged.get("day"), self.DEFAULT_DAY)
        self._dry_run = bool(merged.get("dry_run", False))
        self._max_gifts = (
            None
            if merged.get("max_gifts") in (None, "", 0, "0")
            else self._as_int(merged.get("max_gifts"), 0)
        )
        self._max_history_scrolls = max(
            1, self._as_int(merged.get("max_history_scrolls"), self.MAX_HISTORY_SCROLLS)
        )
        self._max_friend_swipes = max(
            1, self._as_int(merged.get("max_friend_swipes"), self.MAX_FRIEND_SWIPES)
        )
        self._settle_interval = float(
            merged.get("settle_interval", self.SETTLE_INTERVAL)
        )
        self._swipe_delay = float(merged.get("swipe_delay", self.SWIPE_DELAY))
        self._gifted = 0

        geometry = merged.get("geometry")
        if isinstance(geometry, dict):
            for key, value in geometry.items():
                if hasattr(self.geo, key):
                    setattr(
                        self.geo, key, self._coerce_like(getattr(self.geo, key), value)
                    )
                else:
                    log_message(f"[Friend_ReturnGift] 未知的 geometry 参数: {key}")

        overrides = {
            "history_open_node": self.NODE_HISTORY_OPEN,
            "history_close_node": self.NODE_HISTORY_CLOSE,
            "history_selected_node": self.NODE_HISTORY_SELECTED,
            "history_swipe_node": self.NODE_HISTORY_SWIPE,
            "friend_swipe_node": self.NODE_FRIEND_SWIPE,
            "sendable_node": self.NODE_FRIEND_SENDABLE,
            "quota_node": self.NODE_QUOTA,
            "add_friend_node": self.NODE_ADD_FRIEND,
            "friend_list_node": self.NODE_FRIEND_LIST,
            "friend_list_selected_node": self.NODE_FRIEND_LIST_SELECTED,
        }
        self._node_names = {}
        for key, default in overrides.items():
            value = merged.get(key)
            self._node_names[key] = str(value) if value else default

        log_message(
            "[Friend_ReturnGift] 参数: "
            f"day={self._day} dry_run={self._dry_run} "
            f"max_history_scrolls={self._max_history_scrolls} "
            f"max_friend_swipes={self._max_friend_swipes} "
            f"max_gifts={self._max_gifts if self._max_gifts is not None else '每日上限'}"
        )

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
    def _as_int(value: Any, default: int) -> int:
        if value is None:
            return default
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _coerce_like(sample: Any, value: Any) -> Any:
        """把参数转成和默认值同类型（attach 里可能是字符串）。"""
        try:
            if isinstance(sample, bool):
                return bool(value)
            if isinstance(sample, int) and not isinstance(sample, bool):
                return int(str(value).strip())
            if isinstance(sample, float):
                return float(value)
            if isinstance(sample, tuple):
                return tuple(int(str(item).strip()) for item in value)
        except (TypeError, ValueError):
            pass
        return value

    def _target_day(self) -> dt.date:
        today = _game_day(_now_beijing())
        return today - dt.timedelta(days=max(0, self._day))

    # ------------------------------------------------------------------
    # 基础工具
    # ------------------------------------------------------------------
    def _node(self, key: str) -> str:
        return self._node_names.get(key, "")

    def _screencap(self, context: Context) -> Any:
        """主动刷新截图并返回（BGR）。"""
        context.tasker.controller.post_screencap().wait()
        return context.tasker.controller.cached_image

    def _run_node(self, context: Context, key: str) -> Any:
        node = self._node(key)
        detail = context.run_task(node)
        if detail is not None and getattr(detail, "status", None) is not None:
            if detail.status.failed:
                log_message(f"[Friend_ReturnGift] 执行节点失败: {node}")
        return detail

    def _recognition(
        self, context: Context, key: str, image: Any, override: Any = None
    ):
        node = self._node(key)
        try:
            return context.run_recognition(node, image, override or {})
        except Exception:
            traceback.print_exc()
            return None

    def _hit(self, context: Context, key: str, image: Any) -> bool:
        detail = self._recognition(context, key, image)
        return bool(detail is not None and detail.hit)

    def _ocr(
        self, context: Context, roi: Sequence[int], image: Any
    ) -> list[tuple[str, tuple[int, int, int, int], float]]:
        """对指定区域做一次 OCR，返回 (文本, box, 置信度)。"""
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
                    tuple(int(v) for v in list(box)[:4]),
                    float(getattr(result, "score", 0.0) or 0.0),
                )
            )
        return results

    # ------------------------------------------------------------------
    # 一、扫描互动履历
    # ------------------------------------------------------------------
    def _scan_history(
        self, context: Context, target_day: dt.date
    ) -> list[_Record] | None:
        """打开互动履历扫描记录，返回目标游戏日需要回礼的记录（按时间先后）。

        返回 ``None`` 表示连互动履历都打不开（真正的失败）。
        """
        if not self._open_history(context):
            return None

        collected: dict[tuple[str, int, str], _Record] = {}
        last_keys: set[tuple[str, str]] | None = None
        stalls = 0
        try:
            for round_index in range(self._max_history_scrolls):
                image = self._screencap(context)
                rows = self._read_history_rows(context, image)
                keys = {(row.name, row.raw) for row in rows if row.raw}
                hitting = 0
                for row in rows:
                    if row.kind != KIND_RECEIVE or not row.points:
                        continue
                    key = (_normalize(row.name), row.points, row.raw)
                    if key not in collected:
                        collected[key] = row
                        hitting += 1
                log_message(
                    f"[Friend_ReturnGift] 互动履历第 {round_index + 1} 页："
                    f"{len(rows)} 条记录，新增获赠 {hitting} 条"
                )

                if self._history_reached_target(rows, target_day):
                    log_message(
                        "[Friend_ReturnGift] 已扫到目标游戏日之前的记录，停止滚动"
                    )
                    break
                if not rows:
                    stalls += 1
                elif keys and keys == last_keys:
                    stalls += 1
                else:
                    stalls = 0
                if stalls >= self.REACH_BOTTOM_STALLS:
                    log_message("[Friend_ReturnGift] 互动履历已到底，停止滚动")
                    break
                last_keys = keys
                self._run_node(context, "history_swipe_node")
                time.sleep(self._swipe_delay)
            else:
                log_message(
                    f"[Friend_ReturnGift] 互动履历滚动达到上限 {self._max_history_scrolls} 次"
                )
        finally:
            self._close_history(context)

        records = [
            record
            for record in collected.values()
            if record.day == target_day and record.points
        ]
        # 按时间先后回礼；时间解析失败的排最后
        records.sort(
            key=lambda record: (
                record.moment is None,
                record.moment or dt.datetime.min,
            )
        )
        # 同一赠送者只回礼一次（取最早的一条）
        unique: list[_Record] = []
        seen: set[str] = set()
        for record in records:
            key = _normalize(record.name)
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(record)
        if len(unique) > self.MAX_HISTORY_RECORDS:
            log_message(
                f"[Friend_ReturnGift] 需要回礼的好友超过 {self.MAX_HISTORY_RECORDS} 人，只取最早的"
            )
            unique = unique[: self.MAX_HISTORY_RECORDS]
        return unique

    def _open_history(self, context: Context) -> bool:
        self._run_node(context, "history_open_node")
        for _ in range(self.HISTORY_OPEN_RETRY):
            image = self._screencap(context)
            if self._hit(context, "history_selected_node", image):
                log_message("[Friend_ReturnGift] 已进入互动履历")
                return True
            time.sleep(self._settle_interval)
        log_message("[Friend_ReturnGift] 点击互动履历后未能打开列表")
        return False

    def _close_history(self, context: Context) -> bool:
        for _ in range(3):
            self._run_node(context, "history_close_node")
            time.sleep(self._settle_interval)
            image = self._screencap(context)
            if not self._hit(context, "history_selected_node", image):
                log_message("[Friend_ReturnGift] 已退出互动履历")
                return True
        log_message("[Friend_ReturnGift] 关闭互动履历失败")
        return False

    def _history_reached_target(
        self, rows: Iterable[_Record], target_day: dt.date
    ) -> bool:
        """互动履历按时间倒序，一旦看到比目标游戏日更早的记录就不必再往下翻。"""
        for row in rows:
            if row.day is not None and row.day < target_day:
                return True
        return False

    def _read_history_rows(self, context: Context, image: Any) -> list[_Record]:
        """把互动履历记录区 OCR 结果按行拼成记录。"""
        return parse_history_rows(self._ocr(context, HISTORY_ROI, image))

    @staticmethod
    def _parse_datetime(text: str) -> dt.datetime | None:
        match = _DATE_RE.search(text or "")
        if not match:
            return None
        year, month, day, hour, minute = (int(match.group(i)) for i in range(1, 6))
        second = int(match.group(6) or 0)
        try:
            return dt.datetime(year, month, day, hour, minute, second)
        except ValueError:
            return None

    @staticmethod
    def _parse_points(points_text: str, type_text: str) -> int | None:
        """友情点数字；OCR 把“获赠”与数字并成一段时也从类型文本里取。"""
        for text in (points_text, type_text):
            match = _INT_RE.search(text or "")
            if match:
                try:
                    return int(match.group(0))
                except ValueError:
                    continue
        return None

    @staticmethod
    def _parse_kind(type_text: str) -> str:
        text = _normalize(type_text)
        if "赠送" in text:
            return KIND_SEND
        if "获" in text:
            return KIND_RECEIVE
        return KIND_UNKNOWN

    # ------------------------------------------------------------------
    # 二、逐个回礼
    # ------------------------------------------------------------------
    def _return_gifts(self, context: Context, records: list[_Record]) -> bool:
        if not self._ensure_friend_list(context):
            log_message("[Friend_ReturnGift] 赠送前未能回到好友列表，任务失败")
            return False
        need_reset = False
        hard_failure = False
        for index, record in enumerate(records):
            quota = self._read_quota(context)
            if quota and quota[0] >= quota[1]:
                log_message(
                    f"[Friend_ReturnGift] 今日赠礼已用尽（{quota[0]}/{quota[1]}），提前结束"
                )
                break
            if self._max_gifts is not None and self._gifted >= self._max_gifts:
                log_message(
                    f"[Friend_ReturnGift] 已达到本次赠送上限 {self._max_gifts} 次"
                )
                break
            if need_reset:
                self._reset_list_top(context)
                need_reset = False

            log_message(
                f"[Friend_ReturnGift] ({index + 1}/{len(records)}) 寻找好友：{record.name}"
                + (f"（获赠 {record.points} 友情点）" if record.points else "")
            )
            result, scrolled = self._gift_friend(context, record.name)
            need_reset = scrolled
            if result == "ok":
                self._gifted += 1
                log_message(f"[Friend_ReturnGift] 已回礼：{record.name}")
            elif result == "sent":
                log_message(f"[Friend_ReturnGift] {record.name} 今天已赠送过，跳过")
            elif result == "not_found":
                log_message(f"[Friend_ReturnGift] 好友列表里没找到 {record.name}，跳过")
            elif result == "unreadable":
                log_message("[Friend_ReturnGift] 好友列表读取失败，跳过该好友")
                hard_failure = True
                break
            else:
                log_message(f"[Friend_ReturnGift] 给 {record.name} 赠送失败")
        return not hard_failure

    def _gift_friend(self, context: Context, name: str) -> tuple[str, bool]:
        """在好友列表里找到 ``name`` 并回礼。

        返回 ``(结果, 是否滑动过列表)``；结果为
        ``ok`` / ``sent`` / ``not_found`` / ``unreadable`` / ``failed``。
        """
        last_keys: set[str] | None = None
        stalls = 0
        scrolled = False
        for attempt in range(self._max_friend_swipes + 1):
            cells = self._scan_friend_list(context)
            if not cells:
                log_message("[Friend_ReturnGift] 未识别到好友格子，重试一次")
                time.sleep(self._settle_interval)
                cells = self._scan_friend_list(context)
                if not cells:
                    return ("unreadable" if not scrolled else "not_found", scrolled)

            cell, score = self._best_match(cells, name)
            if cell is not None:
                log_message(
                    f"[Friend_ReturnGift] 命中好友 {cell.name}（匹配度 {score:.2f}）"
                )
                return (self._click_send(context, cell), scrolled)

            keys = {cell.uid_key or cell.key for cell in cells}
            if keys and keys == last_keys:
                stalls += 1
                if stalls >= self.REACH_BOTTOM_STALLS:
                    log_message("[Friend_ReturnGift] 已滑到好友列表底部")
                    break
            else:
                stalls = 0
            last_keys = keys
            if attempt >= self._max_friend_swipes:
                break
            self._run_node(context, "friend_swipe_node")
            scrolled = True
            time.sleep(self._swipe_delay)
        return ("not_found", scrolled)

    # ---------------- 好友列表 ----------------
    def _scan_friend_list(self, context: Context) -> list[_Cell]:
        """截图 -> 建立名片格子 -> OCR 名字/UID。"""
        image = self._screencap(context)
        cells = [_Cell(box) for box in find_cells(image, self.geo)]
        if not cells:
            # 头像白框不可用（例如名片皮肤不是白色）时，退化到 UID 文字锚点
            cells = self._cells_from_uid(context, image)
            if cells:
                log_message("[Friend_ReturnGift] 未识别到头像白框，改用 UID 定位格子")
        if cells:
            self._assign_texts(context, image, cells)
        return cells

    def _cells_from_uid(self, context: Context, image: Any) -> list[_Cell]:
        """用 UID 文字反推名片格子（格子 y = UID 文字中心 - 45）。"""
        height, width = image.shape[:2]
        top = max(0, self.geo.list_top)
        roi = [
            self.geo.cell_left + self.geo.uid_roi[0] - 4,
            top,
            280,
            max(1, min(height, self.geo.list_bottom) - top),
        ]
        cells: list[_Cell] = []
        for text, box, _score in self._ocr(context, roi, image):
            if sum(char.isdigit() for char in text) < 4:
                continue  # UID 是长串数字，名字里很少有这么长的数字
            center_y = box[1] + box[3] / 2.0
            y0 = int(round(center_y - self.geo.uid_center_offset))
            candidate = (self.geo.cell_left, y0, self.geo.cell_w, self.geo.cell_h)
            if not self.geo.usable(candidate, width, height):
                continue
            if any(abs(y0 - other.box[1]) < 20 for other in cells):
                continue
            cells.append(_Cell(candidate))
        cells.sort(key=lambda item: item.box[1])
        return cells

    def _assign_texts(self, context: Context, image: Any, cells: list[_Cell]) -> None:
        """一次 OCR 好友名字列，按格子 y 归属到名字/UID。"""
        top = max(0, self.geo.list_top)
        roi = [
            self.geo.cell_left + self.geo.name_roi[0] - 4,
            top,
            280,
            max(1, min(image.shape[0], self.geo.list_bottom) - top),
        ]
        assign_cell_texts(self._ocr(context, roi, image), cells, self.geo)

    def _best_match(
        self, cells: list[_Cell], target: str
    ) -> tuple[_Cell | None, float]:
        """在可见格子里找匹配度最高的好友。"""
        target_key = _normalize(target)
        best: _Cell | None = None
        best_score = 0.0
        for cell in cells:
            score = self._name_score(target_key, cell.key)
            if score > best_score:
                best, best_score = cell, score
        if best is not None and best_score >= self.NAME_MATCH_MIN_SCORE:
            return best, best_score
        if best is not None and best_score > 0:
            log_message(
                f"[Friend_ReturnGift] 最接近的是 {best.name}（匹配度 {best_score:.2f}），"
                "低于阈值，不当成目标好友"
            )
        return None, best_score

    def _name_score(self, target: str, candidate: str) -> float:
        """玩家名匹配打分：完全一致 > 首尾截断 > 包含 > 相似度。

        名字在好友列表里可能被截断（例如 ``银河基因组bil`` -> ``银河基因组bi``），
        两边 OCR 也可能有出入，所以除了完全一致还接受这几种近似；
        但单字名太容易撞，只认完全一致。
        """
        if not target or not candidate:
            return 0.0
        if target == candidate:
            return 1.0
        short, long = sorted((target, candidate), key=len)
        if len(short) < 2:
            return 0.0
        if long.startswith(short):
            return 0.9
        if long.endswith(short):
            return 0.85
        if short in long:
            return 0.75
        ratio = difflib.SequenceMatcher(None, target, candidate).ratio()
        if ratio >= 0.8:
            return 0.7
        return 0.0

    # ---------------- 赠送 ----------------
    def _is_sendable(self, context: Context, image: Any, cell: _Cell) -> bool:
        """用“赠送按钮模板 ∩ 金色连通块”判断该格子是否还能赠送。"""
        override = self._cell_override(context, "sendable_node", cell)
        if not override:
            return False
        detail = self._recognition(context, "sendable_node", image, override)
        return bool(detail is not None and detail.hit)

    def _click_send(self, context: Context, cell: _Cell) -> str:
        """点击该格子的“赠送”按钮。

        返回 ``ok``（已送出）/ ``sent``（按钮不可赠，今天已送过）/ ``failed``。
        """
        override = self._cell_override(context, "sendable_node", cell)
        if not override:
            return "failed"
        image = self._screencap(context)
        detail = self._recognition(context, "sendable_node", image, override)
        if detail is None or not detail.hit:
            return "sent"
        box = getattr(detail, "box", None)
        before = self._quota_of(context, image)
        try:
            context.run_action(self._node("sendable_node"), box, "", override)
        except Exception:
            traceback.print_exc()
            return "failed"
        time.sleep(self.GIFT_DELAY)
        return "ok" if self._verify_gift(context, cell, before) else "failed"

    def _verify_gift(
        self,
        context: Context,
        cell: _Cell,
        before: tuple[int, int] | None,
    ) -> bool:
        """赠送后的校验。

        判定依据（任一成立即算成功）：
          - 今日赠礼次数（``ReturnGiftQuota``）比点击前多了；
          - 该格子的“赠送”按钮已经不可赠（变灰）。
        """
        for _ in range(self.CLICK_VERIFY_RETRY):
            time.sleep(0.4)
            image = self._screencap(context)
            quota = self._quota_of(context, image)
            if before is not None and quota is not None and quota[0] > before[0]:
                return True
            if not self._hit(context, "friend_list_selected_node", image):
                continue  # 页面还没回到好友列表，继续等
            if not self._is_sendable(context, image, cell):
                return True
        return False

    def _reset_list_top(self, context: Context) -> None:
        """切到“添加好友”再切回“好友列表”，让列表瞬间回到顶部。"""
        self._run_node(context, "add_friend_node")
        time.sleep(self.TAB_SWITCH_DELAY)
        self._run_node(context, "friend_list_node")
        time.sleep(self.TAB_SWITCH_DELAY)
        log_message("[Friend_ReturnGift] 已把好友列表切回顶部")

    def _ensure_friend_list(self, context: Context) -> bool:
        """确保当前停留在好友列表。"""
        for _ in range(self.FRIEND_LIST_RETRY):
            image = self._screencap(context)
            if self._hit(context, "friend_list_selected_node", image):
                return True
            time.sleep(self._settle_interval)
        # 最后一招：点一下“好友列表”页签
        self._run_node(context, "friend_list_node")
        time.sleep(self.TAB_SWITCH_DELAY)
        image = self._screencap(context)
        return self._hit(context, "friend_list_selected_node", image)

    # ---------------- 今日赠礼次数 ----------------
    #: “今日赠礼 X/Y” 的识别区域（实测 [1133,666,107,24]）；节点读不到时用直连 OCR 兜底
    QUOTA_ROI = [1120, 660, 140, 32]

    def _read_quota(self, context: Context) -> tuple[int, int] | None:
        """截图并读出“今日赠礼 X/Y”；读不到返回 None。"""
        return self._quota_of(context, self._screencap(context))

    def _quota_of(self, context: Context, image: Any) -> tuple[int, int] | None:
        """从给定截图读出“今日赠礼 X/Y”；读不到返回 None。"""
        detail = self._recognition(context, "quota_node", image)
        if detail is not None:
            for result in list(getattr(detail, "all_results", None) or []) + list(
                getattr(detail, "filtered_results", None) or []
            ):
                parsed = self._parse_quota(getattr(result, "text", "") or "")
                if parsed:
                    return parsed
        # 节点没读到（例如 expected 没命中）时直连 OCR 兜底
        for text, _box, _score in self._ocr(context, self.QUOTA_ROI, image):
            parsed = self._parse_quota(text)
            if parsed:
                return parsed
        return None

    @staticmethod
    def _parse_quota(text: str) -> tuple[int, int] | None:
        match = re.search(r"(\d+)\s*[/／]\s*(\d+)", text or "")
        if not match:
            return None
        return int(match.group(1)), int(match.group(2))

    # ---------------- 节点 ROI 覆盖 ----------------
    def _cell_override(self, context: Context, key: str, cell: _Cell) -> dict[str, Any]:
        """把“可赠送”节点的全部 ROI 换成该格子内的赠送按钮区域。

        节点定义仍然是唯一来源（见 ``ReturnGiftFriend_Sendable``），这里只是把
        识别区域按格子平移过去：读出节点数据 -> 递归替换其中的 ``roi``。
        """
        node = self._node(key)
        try:
            data = context.get_node_data(node)
        except Exception:
            traceback.print_exc()
            return {}
        if not isinstance(data, dict):
            log_message(f"[Friend_ReturnGift] 读取节点失败: {node}")
            return {}
        updated = copy.deepcopy(data)
        if not self._replace_rois(updated, self.geo.gift_box(cell.box)):
            log_message(f"[Friend_ReturnGift] 节点 {node} 没有可覆盖的 roi，放弃赠送")
            return {}
        return {node: updated}

    @classmethod
    def _replace_rois(cls, node: Any, roi: Sequence[int]) -> bool:
        """递归把节点里所有 ``roi`` 换成 ``roi``，返回是否替换到。"""
        replaced = False
        if isinstance(node, dict):
            for key, value in list(node.items()):
                if key == "roi" and isinstance(value, (list, tuple)):
                    node[key] = [int(item) for item in roi]
                    replaced = True
                elif isinstance(value, (dict, list)):
                    replaced = cls._replace_rois(value, roi) or replaced
        elif isinstance(node, list):
            for item in node:
                replaced = cls._replace_rois(item, roi) or replaced
        return replaced
