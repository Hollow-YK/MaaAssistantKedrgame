from __future__ import annotations

import re
import traceback
from typing import Any

import numpy as np

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from maa.pipeline import JActionType, JClick, JOCR, JRecognitionType

from ..general import interruptible_sleep, parse_params, stop_requested


@AgentServer.custom_action("Shop_Activity_1_Manager")
class ShopActivity1Manager(CustomAction):
    """耀斑活动-商店购物管理器：在活动商店界面循环购买当前展示的全部商品。

    前置：开始时已停留在活动商店商品页面（商品格子处于可点击状态）。

    流程：
      一、格子商品判断
        1. 在 [330,180,925,430] 范围识别商品格子（约 194x209）：用名称栏行带定位
           每行 y，再用格子左右边界精确定位 x（左边界起点 → x0=起点-1；左边界被
           装饰渐变遮盖时用右边界 → x0=右边界起点-187），不受渐变影响
        2. 只标记完全展示的商品格子：格子完整落在搜索区域内即视为完全展示，
           左右装饰性渐变遮挡不计（否则最两端的商品会被永久忽略）；
           被容器边缘截断的格子（如右侧未完全展示的部分）不算
        3. 通过 Shop_Activity_1_Sold 节点判断每个格子是否售罄
      二、购买商品（逐个）
        1. 点击待购买商品 → 进入商品详情界面
        2. OCR [561,353,511,47] 解析数量排布（如 "MIN - 1/4 + MAX"）
        3. 当选择购买的数量不是最大时点击 MAX；设置数量存在约 1s 延迟，做硬延迟
        4. 确保数量为最大后，OCR [920,514,180,55] "确认购买" 并点击
        5. 执行一次 SceneDo_GetItem 节点，回到商品页；重复直至买完当前全部商品
      三、继续后续购买
        仅一次：执行 Shop_Activity_1_Swipe 右划使后面的商品出现，
        再进行一轮步骤一、二后，视为成功完成。

    custom_action_param（可选）：
      - swipe_times: 步骤三的右划轮数（默认 1，即"仅一次"）
      - max_purchase_rounds: 每轮购买的安全上限（默认 5），防止商品购买后
        不失效导致的死循环
    """

    # ---- 格子识别 ----
    # 商品格子搜索区域（商品容器可视区）
    SEARCH_ROI = [330, 180, 930, 430]
    # 商品格子尺寸（1.png / 2.png 模板尺寸）
    CELL_W = 194
    CELL_H = 209
    # 格子灰色边框颜色范围（BGR；边框与名称栏底色为 [48,48,48]/[49,49,49]，加容差）
    GRAY_LO = 44
    GRAY_HI = 53
    # 名称栏行高灰计数阈值（名称栏约 31 行全灰，计数约 750+；格身行仅左右边框约 <70）
    NAME_BAR_ROW_MIN = 200
    # 名称栏最小行数（排除底部边框等窄灰条）
    NAME_BAR_MIN_H = 15
    # 名称栏列计数阈值（列内至少 3 行灰视为名称栏像素）
    BAR_COL_MIN = 3
    # 被文字断开的名称栏片段合并的最大间隔（px）
    BAR_MERGE_GAP = 4
    # 名称栏最小可见宽度（完全展示格子的名称栏即使被渐变遮边也至少约 170px）
    BAR_MIN_W = 150
    # 底部边框相对格子顶部的 y 偏移（格子内 [1,203,193,6]）
    BOTTOM_BORDER_Y = 203
    # 底部边框校验的最小灰占比
    BOTTOM_BORDER_MIN_RATIO = 0.5
    # 垂直边框段：列内灰色 run 最短长度（边框约 200px，但可能被售罄遮盖断成 40~60px 段）
    MIN_V_RUN = 40
    # 同一边框相邻列合并允许的 x 间隔
    BORDER_GAP = 6
    # 左边界起点与右边界起点距离（右边界起点 - 187 = 格子 x0）
    LEFT_RIGHT_DIST = 187
    # 名称栏 x 范围匹配左/右边界的容差（px）
    MATCH_TOL_L = 8
    MATCH_TOL_R = 8

    # ---- 售罄判断 ----
    # 售罄遮盖区域在格子内的区域 [0,64,194,89]
    SOLD_REGION = (0, 64, 194, 89)
    # 售罄标记与售罄区域重叠判定阈值（重叠面积 / 售罄标记面积）
    SOLD_OVERLAP_RATIO = 0.5

    # ---- 购买 ----
    # 详情页数量设置 OCR 区域（"MIN - 1/4 + MAX"）
    QTY_ROI = [561, 353, 511, 47]
    # 确认购买按钮 OCR 区域
    CONFIRM_ROI = [920, 514, 180, 55]
    # 确认购买按钮文本
    CONFIRM_TEXT = "确认购买"
    # 数量比例正则（匹配 "1/4"）
    QTY_PATTERN = re.compile(r"(\d+)\s*/\s*(\d+)")
    # 点击 MAX 后设置数量的硬延迟（秒）
    SET_QTY_DELAY = 1.0
    # 每轮购买安全上限（防止商品购买后不失效导致死循环）
    MAX_PURCHASE_ROUNDS = 5
    # 界面加载/动画等待
    LOAD_DELAY = 1.0
    # 代币检测
    MONEY_CHECK_NODE = "Shop_Activity_1_Confirm:Money"

    # ---- OCR 重试 ----
    OCR_RETRY = 5
    OCR_RETRY_INTERVAL = 0.5
    # 识别不到格子的重试（界面可能仍在加载）
    CELL_FIND_RETRY = 5
    CELL_FIND_RETRY_INTERVAL = 1.0

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
        swipe_times = int(params.get("swipe_times", 1))
        self._max_purchase_rounds = int(
            params.get("max_purchase_rounds", self.MAX_PURCHASE_ROUNDS)
        )

        if stop_requested(context):
            return CustomAction.RunResult(success=False)

        # ── 二、购买当前展示的全部商品 ──
        success, should_continue = self._buy_all(context)
        if not success:
            print("[Shop_Activity_1_Manager] 购买当前商品失败")
            return CustomAction.RunResult(success=False)
        if not should_continue:
            # 代币不足，已关闭弹窗，任务成功完成
            print("[Shop_Activity_1_Manager] 代币不足，停止购买，任务成功完成")
            return CustomAction.RunResult(success=True)

        # ── 三、右划使后面的商品出现，再进行一轮购买 ──
        for i in range(swipe_times):
            if stop_requested(context):
                return CustomAction.RunResult(success=False)
            print(f"[Shop_Activity_1_Manager] 第 {i + 1} 次右划，使后面的商品出现")
            context.run_task("Shop_Activity_1_Swipe")
            if not interruptible_sleep(context, self.LOAD_DELAY):
                return CustomAction.RunResult(success=False)
            success, should_continue = self._buy_all(context)
            if not success:
                print("[Shop_Activity_1_Manager] 右划后购买商品失败")
                return CustomAction.RunResult(success=False)
            if not should_continue:
                print("[Shop_Activity_1_Manager] 右划后代币不足，任务成功完成")
                return CustomAction.RunResult(success=True)

        print("[Shop_Activity_1_Manager] 商店购物完成")
        return CustomAction.RunResult(success=True)

    # ---------- 一、格子识别与售罄判断 ----------
    def _buy_all(self, context: Context) -> tuple[bool, bool]:
        """步骤一、二：识别并购买当前展示的全部未售罄商品。"""
        for _ in range(self._max_purchase_rounds):
            if stop_requested(context):
                return (False, False)
            # 1. 获取当前屏幕上的所有格子
            cells = self._find_cells_with_retry(context)
            if not cells:
                print("[Shop_Activity_1_Manager] 未识别到商品格子")
                return (False, False)

            # 2. 只截一次图，运行一次售罄节点
            image = self._screencap(context)
            sold_detail = context.run_recognition("Shop_Activity_1_Sold", image)

            # 3. 过滤出未售罄的格子（使用同一份 detail）
            to_buy = []
            for cell in cells:
                if not self._is_sold_out_with_detail(sold_detail, cell):
                    to_buy.append(cell)

            if not to_buy:
                print("[Shop_Activity_1_Manager] 当前无待购买商品")
                return (True, True)

            print(f"[Shop_Activity_1_Manager] 本轮待购买商品: {len(to_buy)} 个")
            bought_any = False
            for cell in to_buy:
                result = self._buy_product(context, cell)
                if result is None:  # 代币不足
                    return (True, False)
                if result:
                    bought_any = True
            if not bought_any:
                print("[Shop_Activity_1_Manager] 本轮购买全部失败，终止")
                return (False, False)

        print("[Shop_Activity_1_Manager] 达到购买轮数上限，任务完成")
        return (True, True)

    def _is_sold_out_with_detail(self, detail, cell: list[int]) -> bool:
        """使用已获取的售罄识别结果 detail 判断格子是否售罄。"""
        if not (detail and detail.hit):
            return False
        sold_region = (
            cell[0] + self.SOLD_REGION[1],  # x 不变，因为 SOLD_REGION[0] = 0
            cell[1] + self.SOLD_REGION[1],
            self.SOLD_REGION[2],
            self.SOLD_REGION[3],
        )
        for box, _score in self._boxes_and_scores_from(detail):
            inter = self._intersection(tuple(box), sold_region)
            if inter and inter / (box[2] * box[3]) > self.SOLD_OVERLAP_RATIO:
                return True
        return False

    def _find_cells_with_retry(self, context: Context) -> list[list[int]]:
        for _ in range(self.CELL_FIND_RETRY):
            if stop_requested(context):
                return []
            cells = self._find_cells(context)
            if cells:
                return cells
            if not interruptible_sleep(context, self.CELL_FIND_RETRY_INTERVAL):
                return []
        return []

    def _find_cells(self, context: Context) -> list[list[int]]:
        """在搜索区域内识别完全展示的商品格子。

        定位方式（对齐血条识别敌方单位的思路，用格子左右边界精确定位）：
          1. 名称栏行带：商品格子顶部约 33 行高的名称栏（灰色底 + 白色商品名，
             商品名区域也属于边框）在行灰统计上表现为高灰带，据此定位每行格子的 y。
          2. 垂直边框段：按列提取垂直灰色 run（边框可能被售罄遮盖断成短段），
             相邻列聚合为左右边框段，并按行归属。
          3. 用名称栏 x 范围把边框段归属到对应格子：左边界起点 → x0=起点-1；
             左边界被装饰渐变遮盖时（如最左格）用右边界 → x0=右边界起点-187，
             从而不受渐变影响、精确定位到真实 x0。
          4. 校验底部边框存在、且格子完整落在搜索区域内（左右装饰性渐变遮挡
             不算未完整展示），只保留完全展示的格子。
        """
        image = self._screencap(context)
        sx, sy, _sw, _sh = self.SEARCH_ROI
        region = image[sy : sy + _sh, sx : sx + _sw]
        mask = self._gray_mask(region)
        row_count = mask.sum(axis=1)

        # 1. 名称栏行带（行灰计数高且连续）→ 每行格子的 y
        bands = self._name_bar_bands(row_count)

        # 2. 垂直边框段（按行归属）
        segments = self._vertical_border_segments(mask, bands)

        cells: list[list[int]] = []
        for i, (bt, bb) in enumerate(bands):
            y0 = sy + bt - 1
            # 名称栏 x 范围（近似，仅用于把边框归属到对应格子）
            name_bars = self._name_bar_ranges(mask, bt, bb)
            for n0, n1 in name_bars:
                # 3. 用左右边框精确定位 x0
                x0r = self._locate_x_from_borders(segments[i], n0, n1)
                if x0r is None:
                    continue
                cell = [sx + x0r, y0, self.CELL_W, self.CELL_H]
                # 4. 底部边框校验，防止把其他灰色 UI 误判为格子
                if not self._has_bottom_border(mask, n0, n1, y0 + self.BOTTOM_BORDER_Y):
                    continue
                # 5. 只保留完整落在搜索区域内的格子（完全展示）
                if not self._fully_displayed(cell):
                    continue
                cells.append(cell)

        cells.sort(key=lambda c: (c[1], c[0]))
        return cells

    def _name_bar_bands(self, row_count: np.ndarray) -> list[list[int]]:
        """名称栏行带：行灰计数 > 阈值且连续的行（约 31 行）即为一行格子的名称栏，
        返回 region 坐标的 [顶, 底] 列表"""
        bands: list[list[int]] = []
        in_band = False
        for y in range(row_count.shape[0]):
            if row_count[y] > self.NAME_BAR_ROW_MIN:
                if not in_band:
                    bands.append([y, y])
                    in_band = True
                else:
                    bands[-1][1] = y
            else:
                in_band = False
        return [b for b in bands if b[1] - b[0] + 1 >= self.NAME_BAR_MIN_H]

    def _name_bar_ranges(
        self, mask: np.ndarray, bt: int, bb: int
    ) -> list[tuple[int, int]]:
        """名称栏带内按列灰度切分单个名称栏（文字会断开灰列，需合并小间隔），
        返回 region 坐标的 [左, 右] 列表"""
        col_count = mask[bt : bb + 1].sum(axis=0)
        on = col_count >= self.BAR_COL_MIN
        runs = self._runs(on)
        bars: list[tuple[int, int]] = []
        for a0, a1 in runs:
            if bars and a0 - bars[-1][1] <= self.BAR_MERGE_GAP:
                bars[-1] = (bars[-1][0], a1)
            else:
                bars.append((a0, a1))
        return [(a0, a1) for a0, a1 in bars if a1 - a0 + 1 >= self.BAR_MIN_W]

    def _vertical_border_segments(
        self, mask: np.ndarray, bands: list[list[int]]
    ) -> list[list[tuple[int, int]]]:
        """提取各行的垂直边框段（左右边界）。

        按列提取长度 >= MIN_V_RUN 的垂直灰色 run（边框可能被售罄遮盖断成短段），
        按 run 中点归属到对应行，再把相邻列聚合为边框段。
        返回 band_idx -> [(x_start, x_end), ...]（region 坐标）。
        """
        row_runs: dict[int, list[tuple[int, int, int]]] = {
            i: [] for i in range(len(bands))
        }
        for x in range(mask.shape[1]):
            col = mask[:, x].astype(np.uint8)
            ry0 = None
            for y in range(mask.shape[0] + 1):
                v = col[y] if y < mask.shape[0] else 0
                if v:
                    if ry0 is None:
                        ry0 = y
                elif ry0 is not None:
                    if y - ry0 >= self.MIN_V_RUN:
                        mid = (ry0 + y) // 2
                        for i, (bt, _bb) in enumerate(bands):
                            if bt - 1 <= mid <= bt - 1 + self.CELL_H:
                                row_runs[i].append((x, ry0, y))
                                break
                    ry0 = None
        segments: dict[int, list[tuple[int, int]]] = {i: [] for i in range(len(bands))}
        for i in range(len(bands)):
            for x, _ry0, _ry1 in sorted(row_runs[i]):
                if segments[i] and x - segments[i][-1][1] <= self.BORDER_GAP:
                    segments[i][-1] = (segments[i][-1][0], x)
                else:
                    segments[i].append((x, x))
        return [segments[i] for i in range(len(bands))]

    def _locate_x_from_borders(
        self, segs: list[tuple[int, int]], n0: int, n1: int
    ) -> int | None:
        """用左右边框精确定位格子 x0（region 坐标）。

        左边界起点 → x0=起点-1；左边界被渐变遮盖时（如最左格）用右边界 →
        x0=右边界起点-187。均无法匹配则返回 None。
        """
        # 左边界：起点接近名称栏左端 n0
        best = None
        for xs, _xe in segs:
            if abs(xs - n0) <= self.MATCH_TOL_L:
                if best is None or abs(xs - n0) < abs(best - n0):
                    best = xs
        if best is not None:
            return best - 1
        # 右边界：起点接近名称栏右端 n1-5（右边界 = x0+187，名称栏 = x0+1..x0+192）
        best = None
        for xs, _xe in segs:
            if abs(xs - (n1 - 5)) <= self.MATCH_TOL_R:
                if best is None or abs(xs - (n1 - 5)) < abs(best - (n1 - 5)):
                    best = xs
        if best is not None:
            return best - self.LEFT_RIGHT_DIST
        return None

    def _is_sold_out(self, context: Context, cell: list[int]) -> bool:
        """通过 Shop_Activity_1_Sold 节点判断商品格子是否售罄。

        售罄时格子 [0,64,194,89] 区域会被售罄 UI 遮盖；该节点模板匹配售罄标记，
        只要售罄标记框与格子的售罄区域重叠比例足够即判定售罄。
        """
        image = self._screencap(context)
        detail = context.run_recognition("Shop_Activity_1_Sold", image)
        if not (detail and detail.hit):
            return False
        sold_region = (
            cell[0],
            cell[1] + self.SOLD_REGION[1],
            self.SOLD_REGION[2],
            self.SOLD_REGION[3],
        )
        for box, _score in self._boxes_and_scores_from(detail):
            inter = self._intersection(tuple(box), sold_region)
            if inter and inter / (box[2] * box[3]) > self.SOLD_OVERLAP_RATIO:
                return True
        return False

    # ---------- 二、购买单个商品 ----------
    def _buy_product(self, context: Context, cell: list[int]) -> bool | None:
        """购买单个商品：点击进入详情 → 设最大数量 → 确认购买 → 领取物品 → 回到商品页
        返回：
            True  ：购买成功
            False ：购买失败（其他错误）
            None  ：代币不足（已关闭弹窗），任务应结束并视为成功
        """
        # 1. 点击商品格子，进入详情界面
        if stop_requested(context):
            return False
        self._click_box(context, cell)
        if not interruptible_sleep(context, self.LOAD_DELAY):
            return False

        # 2. 设置最大购买数量
        if not self._set_max_quantity(context):
            print(f"[Shop_Activity_1_Manager] 设置最大数量失败: {cell}")
            return False

        # 确认代币足够
        if not self._money_confirm(context):
            print(f"[Shop_Activity_1_Manager] 代币不足: {cell}")
            context.run_task("Shop_Activity_1_CloseInfo")  # 关闭弹窗
            return None  # 特殊状态：代币不足，任务应结束

        # 3. 确认购买
        if not self._click_confirm(context):
            print(f"[Shop_Activity_1_Manager] 确认购买失败: {cell}")
            return False

        # 4. 领取物品并回到商品页
        if stop_requested(context):
            return False
        context.run_task("SceneDo_GetItem")
        if not interruptible_sleep(context, self.LOAD_DELAY):
            return False
        print(f"[Shop_Activity_1_Manager] 已购买: {cell}")
        return True

    def _set_max_quantity(self, context: Context) -> bool:
        """OCR 详情页数量排布，未达最大时点击 MAX 并做硬延迟。返回是否已确保数量最大。"""
        for _ in range(self.OCR_RETRY):
            if stop_requested(context):
                return False
            image = self._screencap(context)
            detail = context.run_recognition_direct(
                JRecognitionType.OCR, JOCR(roi=self.QTY_ROI), image
            )
            if not (detail and detail.hit):
                if not interruptible_sleep(context, self.OCR_RETRY_INTERVAL):
                    return False
                continue

            # 解析数量排布：找出 MAX 按钮位置与当前/最大数量
            max_box: tuple | None = None
            current: int | None = None
            total: int | None = None
            for result in detail.all_results:
                text = (getattr(result, "text", "") or "").strip()
                if not text:
                    continue
                if "MAX" in text and max_box is None and getattr(result, "box", None):
                    max_box = tuple(result.box)
                m = self.QTY_PATTERN.search(text)
                if m:
                    current = int(m.group(1))
                    total = int(m.group(2))

            # 已是最大（如 "1/1"）→ 无需点击 MAX
            if current is not None and total is not None and current >= total:
                print(f"[Shop_Activity_1_Manager] 数量已是最大 {current}/{total}")
                return True

            # 未达最大且能定位到 MAX 按钮 → 点击并做硬延迟
            if max_box is not None:
                self._click_box(context, max_box)
                if not interruptible_sleep(context, self.SET_QTY_DELAY):
                    return False
                print(f"[Shop_Activity_1_Manager] 已点击 MAX (数量 {current}/{total})")
                return True

            # 未识别到 MAX 也没法确认数量 → 重试
            if not interruptible_sleep(context, self.OCR_RETRY_INTERVAL):
                return False

        print("[Shop_Activity_1_Manager] 数量 OCR 解析失败")
        return False

    def _money_confirm(self, context: Context) -> bool:
        """
        检测代币是否不足。
        若 ColorMatch 节点命中（检测到红色区域），表示代币不足，返回 False；
        否则返回 True（代币充足）。
        """
        image = self._screencap(context)
        detail = context.run_recognition(self.MONEY_CHECK_NODE, image)
        if detail and detail.hit:
            print("[Shop_Activity_1_Manager] 代币不足")
            return False
        return True

    def _click_confirm(self, context: Context) -> bool:
        """OCR "确认购买" 并点击其中心"""
        for _ in range(self.OCR_RETRY):
            if stop_requested(context):
                return False
            image = self._screencap(context)
            detail = context.run_recognition_direct(
                JRecognitionType.OCR,
                JOCR(expected=[self.CONFIRM_TEXT], roi=self.CONFIRM_ROI),
                image,
            )
            if detail and detail.hit:
                for box, _score in self._boxes_and_scores_from(detail):
                    self._click_box(context, box)
                    return interruptible_sleep(context, 0.5)
            if not interruptible_sleep(context, self.OCR_RETRY_INTERVAL):
                return False
        return False

    # ---------- 工具 ----------
    def _screencap(self, context: Context) -> Any:
        """主动刷新截图并返回（BGR）"""
        context.tasker.controller.post_screencap().wait()
        return context.tasker.controller.cached_image

    def _click_box(self, context: Context, box) -> None:
        """点击指定框的中心"""
        context.run_action_direct(JActionType.Click, JClick(), tuple(box), "")

    def _gray_mask(self, region: np.ndarray) -> np.ndarray:
        """格子灰色边框 mask（[48,48,48]/[49,49,49] 加容差；灰阶色通道对称）"""
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
    def _runs(on: np.ndarray) -> list[tuple[int, int]]:
        """把布尔数组中的 True 段提取为 (start, end) 列表（含端点）"""
        runs: list[tuple[int, int]] = []
        start = None
        for i, v in enumerate(on):
            if v and start is None:
                start = i
            elif not v and start is not None:
                runs.append((start, i - 1))
                start = None
        if start is not None:
            runs.append((start, len(on) - 1))
        return runs

    def _has_bottom_border(
        self, mask: np.ndarray, xl: int, xr: int, y_abs: int
    ) -> bool:
        """校验格子底部边框存在：名称栏带下方约 203 行处有灰色横条"""
        y0 = y_abs - self.SEARCH_ROI[1]
        if y0 < 0 or y0 + 6 > mask.shape[0]:
            return False
        sub = mask[y0 : y0 + 6, xl : xr + 1]
        return sub.sum() > 6 * (xr - xl + 1) * self.BOTTOM_BORDER_MIN_RATIO

    def _fully_displayed(self, cell: list[int]) -> bool:
        """格子是否完全展示：完整落在搜索区域内（装饰性渐变遮挡不算未完整展示）"""
        sx, sy, sw, sh = self.SEARCH_ROI
        return (
            cell[0] >= sx
            and cell[1] >= sy
            and cell[0] + cell[2] <= sx + sw
            and cell[1] + cell[3] <= sy + sh
        )

    def _boxes_and_scores_from(self, detail) -> list[tuple[tuple, float]]:
        """从识别结果提取 (box, score) 列表（兼容 Or 嵌套 sub_results 递归）"""
        source = getattr(detail, "filtered_results", None) or []
        if not source:
            source = getattr(detail, "all_results", None) or []
        results: list[tuple[tuple, float]] = []
        for r in source:
            box = getattr(r, "box", None)
            if box is not None:
                results.append((tuple(box), float(getattr(r, "score", 0.0) or 0.0)))
            else:
                sub = getattr(r, "sub_results", None)
                if sub:
                    for sd in sub:
                        results.extend(self._boxes_and_scores_from(sd))
        return results

    @staticmethod
    def _intersection(a: tuple, b: tuple) -> int:
        x1 = max(a[0], b[0])
        y1 = max(a[1], b[1])
        x2 = min(a[0] + a[2], b[0] + b[2])
        y2 = min(a[1] + a[3], b[1] + b[3])
        if x2 <= x1 or y2 <= y1:
            return 0
        return (x2 - x1) * (y2 - y1)
