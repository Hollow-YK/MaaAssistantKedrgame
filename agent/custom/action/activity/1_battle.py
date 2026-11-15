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


# -----
# region AutoBattle_Activity_1_Manager
# -----
@AgentServer.custom_action("AutoBattle_Activity_1_Manager")
class AutoBattleActivity1Manager(CustomAction):
    """耀斑活动-自动战斗管理器：在关卡详情界面循环判断剩余挑战次数并开战。

    前置：AutoBattle_Activity_1_Stage 已完成选关，停留在关卡详情界面。

    流程：
      1. OCR [940, 120, 180, 30] 读取剩余挑战次数（如 "剩余挑战次数：3/3"）
      2. 次数不足（0）→ 返回成功，pipeline 转至 AutoBattle_Activity_1_Finish
      3. 次数足够 → run_task("AutoBattle_Activity_1_Manager:Start") 点击准备战斗，进入编队界面
      4. 交由 custom_action_param["battle"] 指定的 custom（如 AutoBattle_Activity_1_Battle_EX2-1_1）处理编队与战斗
      5. 战斗完成回到关卡详情，回到步骤 1 循环

    custom_action_param:
      - battle: 战斗处理 custom 所在节点名（必填）
      - max_battles: 安全上限（默认 20），防止战斗 custom 未生效时死循环
    """

    # 剩余挑战次数 OCR 区域
    COUNT_ROI = [940, 120, 180, 30]
    # 匹配 "剩余挑战次数：3/3" 中的 "3/3"
    COUNT_PATTERN = re.compile(r"(\d+)\s*/\s*(\d+)")
    # 识别次数失败时的重试次数与间隔（秒）
    COUNT_RETRY = 5
    COUNT_RETRY_INTERVAL = 1.0

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
        battle = str(params.get("battle", "") or "").strip()
        max_battles = int(params.get("max_battles", 20))

        if stop_requested(context):
            return CustomAction.RunResult(success=False)

        battles_done = 0
        while True:
            if stop_requested(context):
                print("[AutoBattle_Activity_1_Manager] 收到停止请求，中断战斗循环")
                return CustomAction.RunResult(success=False)
            # ── 1. 读取剩余挑战次数 ──
            current, total = self._read_count(context)
            if stop_requested(context):
                return CustomAction.RunResult(success=False)
            if current is None:
                print("[AutoBattle_Activity_1_Manager] 未能识别剩余挑战次数，任务失败")
                return CustomAction.RunResult(success=False)
            print(f"[AutoBattle_Activity_1_Manager] 剩余挑战次数: {current}/{total}")

            # ── 2. 次数不足 → 结束（pipeline 转至 Finish）──
            if current <= 0:
                print("[AutoBattle_Activity_1_Manager] 挑战次数不足，任务完成")
                return CustomAction.RunResult(success=True)

            # 安全上限，防止战斗 custom 未实际消耗次数导致死循环
            if battles_done >= max_battles:
                print(
                    f"[AutoBattle_Activity_1_Manager] 达到安全上限 {max_battles} 次，结束"
                )
                return CustomAction.RunResult(success=True)

            if not battle:
                print("[AutoBattle_Activity_1_Manager] 未配置 battle custom，任务完成")
                return CustomAction.RunResult(success=True)

            # ── 3. 点击准备战斗，进入编队界面 ──
            context.run_task("AutoBattle_Activity_1_Manager:Start")

            # ── 4. 交由战斗 custom 处理编队与战斗；完成后回到关卡详情 ──
            battle_detail = context.run_task(battle)
            if battle_detail and battle_detail.status.failed:
                print(f"[AutoBattle_Activity_1_Manager] 战斗处理失败: {battle}")
                return CustomAction.RunResult(success=False)

            battles_done += 1

    def _screencap(self, context: Context) -> Any:
        """主动刷新截图并返回"""
        context.tasker.controller.post_screencap().wait()
        return context.tasker.controller.cached_image

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


# -----
# region AutoBattle_Activity_1_Battle_EX2-1_1
# -----
@AgentServer.custom_action("AutoBattle_Activity_1_Battle_EX2-1_1")
class AutoBattleActivity1BattleEX211(CustomAction):
    """耀斑活动 EX2-1 - 战斗处理：编队检查 → 进入战斗 → 战前准备 → 部署 → 指令 → 继续 → 技能循环 → 等待结束 → 结算。

    由 AutoBattle_Activity_1_Manager 调用（Manager 点击准备战斗后进入编队界面）。

    流程：
      一、检查编队：确认"禁止开火"指令；OCR 点击"编辑"；模板命中 尤利娅+侦察；返回
      二、进入战斗：点击 Start2 → 等待加载 → 等待 Start3 界面（不点击）
      三、战前准备：识别牌库干员，收起除 尤利娅+任一侦察 外的全部干员
      四、开始作战：记录剩余干员位置 → 点击 Start3 → 立即暂停（点到 continue 出现）
      五、前期准备：先部署侦察（地图上方），再部署尤利娅（地图下方）
      六、给出指令：点击"禁止开火"
      七、调整地图位置：最终点击继续游戏前执行 Mapw300
      八、继续游戏：点击 continue，战斗开始
      九、战斗中循环：只要还在战斗，反复"等待尤利娅充能满 → 暂停 → 点尤利娅 → 释放技能 → 继续"；
                      active 消失且 OCR 识别到"战斗胜利/战斗失败"视为战斗结束
      十、结算：领取"获得物品"（若有）→ 回到关卡详情 → Custom 结束
    """

    # ---- 编队检查 ----
    TEAM_EDIT_ROI = [255, 125, 80, 370]  # "编辑"按钮 OCR 区域
    # ---- 牌库 ----
    # 牌库仅第一位固定为指挥，其余位置任意职业/任意干员、无固定顺序；
    # 尤利娅是"压制"职业，识别压制会同时命中她，故同卡去重时类型需按优先级合并（尤利娅优先）。
    DECK_TYPES = ["指挥", "支援", "特射", "侦察", "压制", "尤利娅"]
    TYPE_PRIORITY = {"尤利娅": 0, "侦察": 1, "指挥": 2, "支援": 3, "特射": 4, "压制": 5}
    MIN_DECK_SCORE = 0.4  # 牌库识别置信度下限：低于此视为模板噪声，忽略
    # ---- 地图格 ----
    OVERLAP_THRESHOLD = 0.6  # 重叠面积占比阈值（去重用）
    # 目标草丛呈弧形：各格沿横向展开、间距均匀。相邻格中心 x 间距落在此范围视为同一弧段
    ARC_MIN_DX = 40  # 弧形相邻格最小 x 间距（像素）
    ARC_MAX_DX = 140  # 弧形相邻格最大 x 间距（像素）
    # ---- 技能循环 ----
    SKILL_TARGET_ROI = [405, 355, 75, 45]  # 技能释放位置兑底范围
    # 技能释放目标：SelectSkillPos 颜色范围（BGR，与 pipeline 一致）
    SKILL_COLOR_LOWER = (55, 45, 0)
    SKILL_COLOR_UPPER = (77, 67, 52)
    SKILL_UNIT_RATIO = 0.8  # 单位位置区域需 >=80% 像素符合该颜色才认为可命中
    # 敌方单位扫描节点（引用 custom recognition）
    SCAN_ENEMY_NODE = "AutoBattle_Activity_1_Battle:ScanEnemies"
    SCAN_VEHICLE_NODE = "AutoBattle_Activity_1_Battle:ScanVehicles"
    # ---- 战斗中判断 ----
    END_ROI = [14, 6, 270, 119]  # "战斗胜利/战斗失败" OCR 区域
    END_TEXTS = ("战斗胜利", "战斗失败")
    BATTLE_END_TIMEOUT = 600  # 等待战斗结束超时（秒）
    DETAIL_ROI = [940, 120, 180, 30]  # 关卡详情"剩余挑战次数" OCR 区域
    POST_BATTLE_TIMEOUT = 30  # 领取物品/返回关卡详情超时（秒）

    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        try:
            return self._run(context, argv)
        except Exception:
            traceback.print_exc()
            return CustomAction.RunResult(success=False)

    def _run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        if stop_requested(context):
            return CustomAction.RunResult(success=False)
        self._yulia_box: tuple | None = None
        self._recon_box: tuple | None = None
        self._target_units: list[tuple] = []  # 暂停后记录的敌方单位位置（unit）

        # 一、检查编队
        if not self._check_formation(context):
            print("[Battle] 编队检查失败")
            return CustomAction.RunResult(success=False)

        # 二、进入战斗
        if not self._enter_battle(context):
            print("[Battle] 进入战斗失败")
            return CustomAction.RunResult(success=False)

        # 三、战前准备（返回最终牌库）
        deck = self._prep_deck(context)
        if not deck:
            print("[Battle] 战前准备失败")
            return CustomAction.RunResult(success=False)
        self._save_deck_positions(deck)

        # 四、开始作战 + 暂停
        if not self._start_battle_and_pause(context):
            print("[Battle] 开始作战/暂停失败")
            return CustomAction.RunResult(success=False)

        # 五、前期准备（部署）
        if not self._early_deployment(context):
            print("[Battle] 前期部署失败")
            return CustomAction.RunResult(success=False)

        # 六、给出指令
        if not self._issue_command(context):
            print("[Battle] 给出指令失败")
            return CustomAction.RunResult(success=False)

        # 七、调整地图位置（最终点击继续游戏前）
        context.run_task("AutoBattle_Activity_1_Battle:Mapw300")

        # 八、继续游戏
        if not self._resume_game(context):
            print("[Battle] 继续游戏失败")
            return CustomAction.RunResult(success=False)

        # 九、战斗中循环：只要还在战斗就反复"等待充能→释放技能"，战斗结束则退出
        if not self._battle_loop(context):
            print("[Battle] 战斗中循环失败")
            return CustomAction.RunResult(success=False)

        # 十、结算：领取物品并回到关卡详情
        if not self._post_battle(context):
            print("[Battle] 领取物品/返回关卡详情失败")
            return CustomAction.RunResult(success=False)

        print("[Battle] 战斗处理完成")
        if stop_requested(context):
            return CustomAction.RunResult(success=False)
        return CustomAction.RunResult(success=True)

    # ---------- 一、检查编队 ----------
    def _check_formation(self, context: Context) -> bool:
        # 1.1 指令检查：确保识别到"禁止开火"
        if not self._wait_node_hit(context, "Combat_Team_Command_禁止开火"):
            print("[Battle] 编队中未识别到'禁止开火'指令")
            return False

        # 1.2 干员检查：OCR"编辑"并点击
        if not self._ocr_click(context, "编辑", self.TEAM_EDIT_ROI):
            print("[Battle] 未找到'编辑'按钮")
            return False
        if not interruptible_sleep(context, 3):
            return False

        # 1.3 模板匹配：要求命中 尤利娅 + 侦察
        image = self._screencap(context)
        d_yulia = context.run_recognition("Combat_Team_Operator_尤利娅", image)
        d_recon = context.run_recognition("Combat_Team_Operator_侦察", image)
        if not (d_yulia and d_yulia.hit and d_recon and d_recon.hit):
            print("[Battle] 编队中缺少 尤利娅 或 侦察")
            return False

        # 1.4 点击返回
        if not self._click_node(context, "UI_Common_BackButton"):
            print("[Battle] 未找到返回按钮")
            return False
        return interruptible_sleep(context, 3)

    # ---------- 二、进入战斗 ----------
    def _enter_battle(self, context: Context) -> bool:
        context.run_task("AutoBattle_Activity_1_Manager:Start2")
        if not self._wait_node_hit(
            context, "Status_Loading_Screen", attempts=20, interval=1.0
        ):
            print("[Battle] 未检测到加载界面")
            return False
        if not self._wait_node_hit(
            context, "AutoBattle_Activity_1_Manager:Start3", attempts=20, interval=1.0
        ):
            print("[Battle] 未检测到 Start3 界面")
            return False
        return True

    # ---------- 三、战前准备 ----------
    def _prep_deck(self, context: Context) -> list[dict[str, Any]] | None:
        """收起除尤利娅+任一侦察外的所有干员，返回最终牌库（按 x 排序）"""
        for _ in range(10):
            if stop_requested(context):
                return None
            deck = self._scan_deck(context)
            if not deck:
                print("[Battle] 牌库识别为空")
                return None
            to_collapse = self._pick_excess(deck)
            if to_collapse is None:
                print(f"[Battle] 牌库仅剩: {[d['type'] for d in deck]}")
                return deck
            print(f"[Battle] 收起 {to_collapse['type']} @x={to_collapse['x']}")
            if not self._collapse_operator(context, to_collapse["box"]):
                print(f"[Battle] 收起 {to_collapse['type']} 失败")
                return None
        print("[Battle] 战前准备超过安全上限")
        return None

    def _scan_deck(self, context: Context) -> list[dict[str, Any]]:
        image = self._screencap(context)
        entries: list[dict[str, Any]] = []
        for op_type in self.DECK_TYPES:
            node = f"Combat_InCombat_Operator_{op_type}"
            detail = context.run_recognition(node, image)
            if not detail:
                continue
            # 命中（filtered）结果优先；未命中（识别不清、如特射/支援低分卡）时
            # 回退全量结果，把这些"确实存在但置信度低"的卡也纳入牌库去收起。
            for box, score in self._boxes_and_scores_from(detail):
                # 过滤 DirectHit 全屏等异常框（干员卡片约 100x100）
                if box[2] > 250 or box[3] > 250:
                    continue
                # 低于下限的多为模板噪声，忽略
                if score < self.MIN_DECK_SCORE:
                    continue
                entries.append(
                    {"type": op_type, "box": box, "x": box[0], "score": score}
                )

        # 同一张卡片可能被多个识别命中（尤利娅=压制），合并保留更具体的类型
        deck: list[dict[str, Any]] = []
        for e in entries:
            merged = False
            for d in deck:
                if self._same_card(e["box"], d["box"]):
                    if self.TYPE_PRIORITY[e["type"]] < self.TYPE_PRIORITY[d["type"]]:
                        d["type"] = e["type"]
                    merged = True
                    break
            if not merged:
                deck.append(dict(e))
        deck.sort(key=lambda d: d["x"])
        return deck

    def _same_card(self, a: tuple, b: tuple) -> bool:
        """判断两个框是否为同一张干员卡片（重叠面积占比 > 0.5）"""
        inter = self._intersection(a, b)
        denom = min(a[2] * a[3], b[2] * b[3])
        return denom > 0 and inter / denom > 0.5

    def _pick_excess(self, deck: list[dict[str, Any]]) -> dict[str, Any] | None:
        counts: dict[str, int] = {}
        for d in deck:
            counts[d["type"]] = counts.get(d["type"], 0) + 1
        # 候选：非保留类型；或保留类型（尤利娅/侦察）中多出来的那张
        candidates: list[tuple[int, dict[str, Any]]] = []
        for d in deck:
            t = d["type"]
            if t in ("尤利娅", "侦察"):
                if counts[t] > 1:
                    candidates.append((2, d))  # 保留类型多出的，放最后处理
            else:
                # 识别不清（置信度低于 0.7 模板阈值）的卡优先收起，
                # 趁还能定位到位置先收掉，避免之后彻底识别不到而遗留
                fuzzy = d.get("score", 1.0) < 0.7
                candidates.append((0 if fuzzy else 1, d))
        if not candidates:
            return None
        candidates.sort(key=lambda c: (c[0], -c[1]["x"]))
        return candidates[0][1]

    def _collapse_operator(self, context: Context, box: tuple) -> bool:
        # 1. 点击干员卡片（选中）
        context.run_action_direct(JActionType.Click, JClick(), tuple(box), "")
        if not interruptible_sleep(context, 0.5):
            return False
        # 2. 识别 Selected 并点击（收起）
        if not self._click_node(
            context, "Combat_InCombat_Operator_Selected", attempts=5, interval=0.5
        ):
            return False
        # 3. 等待 1 秒
        if not interruptible_sleep(context, 1.0):
            return False
        # 4. 确认 Selected 不再命中
        image = self._screencap(context)
        detail = context.run_recognition("Combat_InCombat_Operator_Selected", image)
        return not (detail and detail.hit)

    # ---------- 四、开始作战 ----------
    def _save_deck_positions(self, deck: list[dict[str, Any]]) -> None:
        for d in deck:
            if d["type"] == "尤利娅" and self._yulia_box is None:
                self._yulia_box = d["box"]
            elif d["type"] == "侦察" and self._recon_box is None:
                self._recon_box = d["box"]

    def _start_battle_and_pause(self, context: Context) -> bool:
        if self._yulia_box is None or self._recon_box is None:
            print("[Battle] 未记录到尤利娅/侦察位置")
            return False
        if not self._click_node(context, "AutoBattle_Activity_1_Manager:Start3"):
            print("[Battle] 未找到 Start3 按钮")
            return False
        return self._pause_game(context)

    def _pause_game(self, context: Context) -> bool:
        """暂停游戏：点击 pause，间隔 0.5s，直到 continue 出现"""
        for _ in range(30):
            if stop_requested(context):
                return False
            if self._node_hit(context, "UI_Combat_InStage_continue"):
                print("[Battle] 已暂停（识别到 continue）")
                return True
            self._click_node(context, "UI_Combat_InStage_pause", attempts=1)
            if not interruptible_sleep(context, 0.5):
                return False
        print("[Battle] 未成功暂停")
        return False

    # ---------- 五、前期准备（部署） ----------
    def _early_deployment(self, context: Context) -> bool:
        if stop_requested(context):
            return False
        # 5.1 侦察干员部署（地图上方）
        context.run_task("AutoBattle_Activity_1_Battle:Mapw300")
        if self._recon_box is None:
            return False
        context.run_action_direct(
            JActionType.Click, JClick(), tuple(self._recon_box), ""
        )
        if not interruptible_sleep(context, 0.5):
            return False
        if not self._click_lowest_bush(context):
            print("[Battle] 部署侦察失败：未找到灌木")
            return False

        # 5.2 尤利娅部署（地图下方）
        for _ in range(3):
            context.run_task("AutoBattle_Activity_1_Battle:Maps300")
        if self._yulia_box is None:
            return False
        context.run_action_direct(
            JActionType.Click, JClick(), tuple(self._yulia_box), ""
        )
        if not interruptible_sleep(context, 0.5):
            return False
        if not self._click_upper_right_bush(context):
            print("[Battle] 部署尤利娅失败：未找到右上角草格子")
            return False
        return interruptible_sleep(context, 1.0)

    def _click_lowest_bush(self, context: Context) -> bool:
        boxes = self._bush_boxes(context)
        if not boxes:
            return False
        target = max(boxes, key=lambda b: b[1])  # 最靠下
        context.run_action_direct(JActionType.Click, JClick(), tuple(target), "")
        return True

    def _click_upper_right_bush(self, context: Context) -> bool:
        results = self._bush_results(context)  # [(box, score)]
        if not results:
            return False
        deduped = self._dedupe_boxes(results)
        if not deduped:
            return False
        target = self._top_right_tile(deduped)
        if target is None:
            return False
        context.run_action_direct(JActionType.Click, JClick(), tuple(target), "")
        return True

    def _bush_boxes(self, context: Context) -> list[tuple]:
        return [b for b, _ in self._bush_results(context)]

    def _bush_results(self, context: Context) -> list[tuple[tuple, float]]:
        image = self._screencap(context)
        detail = context.run_recognition("Combat_InCombat_Map_Grid_Bushes", image)
        if not detail or not detail.hit:
            return []
        # 草丛识别走全量结果，弧形定位交给几何判断（_arc_tiles），不依赖置信度筛选
        return self._boxes_and_scores_from(detail, use_filtered=False)

    # ---------- 六、指令 ----------
    def _issue_command(self, context: Context) -> bool:
        return self._click_node(context, "Combat_InCombat_Command_禁止开火")

    # ---------- 七、继续游戏 ----------
    def _resume_game(self, context: Context) -> bool:
        return self._click_node(context, "UI_Combat_InStage_continue")

    # ---------- 八、战斗中循环 ----------
    def _battle_loop(self, context: Context) -> bool:
        """战斗中主循环：只要还在战斗就反复"等待充能 → 释放技能"；
        战斗结束（active 消失且 OCR 识别到胜利/失败）则返回 True。"""
        for _ in range(self.BATTLE_END_TIMEOUT):
            if stop_requested(context):
                print("[Battle] 收到停止请求，中断战斗中循环")
                return False
            # 战斗结束？
            if self._battle_ended(context):
                print("[Battle] 战斗结束")
                return True
            # 尤利娅技能充能满 → 释放一轮（1.2~1.7）
            if self._skill_ready_for_yulia(context):
                print("[Battle] 尤利娅技能已就绪，开始释放")
                if not self._release_skill_round(context):
                    return False
                continue
            if not interruptible_sleep(context, 1.0):
                return False
        print("[Battle] 战斗超时")
        return False

    def _release_skill_round(self, context: Context) -> bool:
        """释放一轮尤利娅技能：暂停 → 点尤利娅 → 确认技能 → 点技能图标 → 点释放位置 → 继续"""
        if stop_requested(context):
            return False
        # 1.2 暂停游戏
        if not self._pause_game(context):
            return False
        # 1.2b 暂停后先识别敌人与载具位置并暂时记录
        self._record_target_positions(context)
        # 1.3 点击尤利娅，等待 1 秒显示技能图标
        if self._yulia_box is None:
            print("[Battle] 未记录尤利娅位置")
            return False
        context.run_action_direct(
            JActionType.Click, JClick(), tuple(self._yulia_box), ""
        )
        if not interruptible_sleep(context, 1.0):
            return False
        # 1.4 确保可以释放尤利娅技能（未命中则再次点击尤利娅卡牌）
        if not self._click_until_skill_visible(context):
            return False
        # 1.5 点击技能图标
        if not self._click_node(context, "Combat_InCombat_Skill_尤利娅"):
            print("[Battle] 点击技能图标失败")
            return False
        # 1.6 等待 1 秒后点击指定技能释放位置
        if not interruptible_sleep(context, 1.0):
            return False
        self._click_skill_target(context)
        # 1.7 继续游戏
        if not self._resume_game(context):
            print("[Battle] 技能循环-继续游戏失败")
            return False
        return True

    def _skill_ready_for_yulia(self, context: Context) -> bool:
        """SkillReady 命中区域之一是否位于尤利娅卡片上方"""
        if self._yulia_box is None:
            return False
        image = self._screencap(context)
        detail = context.run_recognition("Combat_InCombat_Operator_SkillReady", image)
        if not detail or not detail.hit:
            return False
        for box in self._boxes_from(detail):
            if self._above_card(box, self._yulia_box):
                return True
        return False

    def _above_card(self, box: tuple, card_box: tuple) -> bool:
        """判断 box 是否位于 card_box 卡片上方（x 中心接近且 y 在其之上）"""
        bx = box[0] + box[2] / 2
        by = box[1] + box[3] / 2
        cx = card_box[0] + card_box[2] / 2
        cy = card_box[1] + card_box[3] / 2
        return abs(bx - cx) < 60 and by < cy

    def _click_until_skill_visible(self, context: Context) -> bool:
        """1.4 确保技能图标可释放：命中则成功，否则再次点击尤利娅卡牌"""
        if self._yulia_box is None:
            return False
        for _ in range(5):
            if stop_requested(context):
                return False
            if self._node_hit(context, "Combat_InCombat_Skill_尤利娅"):
                return True
            context.run_action_direct(
                JActionType.Click, JClick(), tuple(self._yulia_box), ""
            )
            if not interruptible_sleep(context, 0.5):
                return False
        print("[Battle] 未能确认尤利娅技能可释放")
        return False

    def _record_target_positions(self, context: Context) -> None:
        """暂停后识别敌人与载具，暂时记录其单位位置（unit）"""
        self._target_units = []
        image = self._screencap(context)
        for node, key in (
            (self.SCAN_ENEMY_NODE, "enemies"),
            (self.SCAN_VEHICLE_NODE, "vehicles"),
        ):
            detail = context.run_recognition(node, image)
            if not detail or not detail.hit:
                continue
            d = getattr(detail, "raw_detail", None) or {}
            for item in d.get(key, []) or []:
                box = item.get("unit")
                if box and len(box) == 4:
                    self._target_units.append(tuple(box))
        print(
            f"[Battle] 记录敌方单位 {len(self._target_units)} 个: {self._target_units}"
        )

    def _click_skill_target(self, context: Context) -> bool:
        """1.6 选择技能释放位置：
        1) 用 SelectSkillPos 选出最大命中区域
        2) 排除不处于该范围内的敌方单位
        3) 剩余单位中，对该单位位置做 ColorMatch（>=80% 符合），选第一个满足的点击
        4) 无单位满足 → 点击默认位置
        """
        image = self._screencap(context)
        zone = self._skill_zone(context, image)
        candidates = [
            u for u in self._target_units if zone is None or self._in_zone(u, zone)
        ]
        print(f"[Battle] 释放范围内候选单位 {len(candidates)} 个")
        for u in candidates:
            if self._unit_color_ok(image, u):
                context.run_action_direct(JActionType.Click, JClick(), tuple(u), "")
                print(f"[Battle] 点击技能目标单位位置 {tuple(u)}")
                return True
        # 无单位符合 → 默认位置
        roi = self.SKILL_TARGET_ROI
        cx = roi[0] + roi[2] / 2
        cy = roi[1] + roi[3] / 2
        context.run_action_direct(JActionType.Click, JClick(), (cx, cy), "")
        print("[Battle] 无符合单位，点击默认释放位置")
        return True

    def _skill_zone(self, context: Context, image) -> tuple | None:
        """SelectSkillPos 最大命中区域（ColorMatch 已按面积取最大）"""
        detail = context.run_recognition(
            "AutoBattle_Activity_1_Battle:SelectSkillPos", image
        )
        if detail and detail.hit and detail.box:
            return tuple(detail.box)
        return None

    def _in_zone(self, unit_box: tuple, zone: tuple) -> bool:
        """单位位置中心是否处于释放区域内"""
        cx = unit_box[0] + unit_box[2] / 2
        cy = unit_box[1] + unit_box[3] / 2
        zx, zy, zw, zh = zone
        return zx <= cx <= zx + zw and zy <= cy <= zy + zh

    def _unit_color_ok(self, image, unit_box: tuple) -> bool:
        """单位位置区域内符合 SelectSkillPos 颜色范围的像素占比 >= 80%"""
        x0, y0 = max(unit_box[0], 0), max(unit_box[1], 0)
        x1, y1 = min(unit_box[0] + unit_box[2], image.shape[1]), min(
            unit_box[1] + unit_box[3], image.shape[0]
        )
        if x1 <= x0 or y1 <= y0:
            return False
        region = image[y0:y1, x0:x1]
        lo = np.array(self.SKILL_COLOR_LOWER, dtype=np.int32)
        hi = np.array(self.SKILL_COLOR_UPPER, dtype=np.int32)
        mask = np.all((region >= lo) & (region <= hi), axis=-1)
        ratio = float(mask.sum()) / (region.shape[0] * region.shape[1])
        return ratio >= self.SKILL_UNIT_RATIO

    # ---------- 九、战斗中判断与结算 ----------
    def _battle_ended(self, context: Context) -> bool:
        """战斗中判断：active 命中则一定在战斗；active 消失且
        OCR [14,6,270,119] 识别到"战斗胜利/战斗失败"时视为战斗结束。"""
        image = self._screencap(context)
        active = context.run_recognition("UI_Combat_InStage_active", image)
        if active and active.hit:
            return False
        detail = context.run_recognition_direct(
            JRecognitionType.OCR, JOCR(roi=self.END_ROI), image
        )
        if detail and detail.hit:
            for r in detail.all_results:
                text = getattr(r, "text", "") or ""
                if any(t in text for t in self.END_TEXTS):
                    print(f"[Battle] 战斗结束: {text}")
                    return True
        return False

    def _post_battle(self, context: Context) -> bool:
        """战斗结束后：领取"获得物品"（可能有），等待回到关卡详情"""
        # 1. 循环点击"获得物品"直到不再出现
        for _ in range(15):
            if stop_requested(context):
                return False
            if not self._click_node(
                context, "SceneDo_GetItem", attempts=1, interval=1.0
            ):
                break
            if not interruptible_sleep(context, 1.0):
                return False
        # 2. 等待回到关卡详情（OCR 识别到"剩余挑战次数"）
        for _ in range(self.POST_BATTLE_TIMEOUT):
            if stop_requested(context):
                return False
            if self._at_stage_detail(context):
                print("[Battle] 已回到关卡详情")
                return True
            if not interruptible_sleep(context, 1.0):
                return False
        print("[Battle] 未回到关卡详情")
        return False

    def _at_stage_detail(self, context: Context) -> bool:
        image = self._screencap(context)
        detail = context.run_recognition_direct(
            JRecognitionType.OCR, JOCR(roi=self.DETAIL_ROI), image
        )
        if detail and detail.hit:
            for r in detail.all_results:
                text = getattr(r, "text", "") or ""
                if "剩余挑战次数" in text:
                    return True
        return False

    # ---------- 工具 ----------
    def _screencap(self, context: Context) -> Any:
        context.tasker.controller.post_screencap().wait()
        return context.tasker.controller.cached_image

    def _node_hit(self, context: Context, node_name: str) -> bool:
        image = self._screencap(context)
        detail = context.run_recognition(node_name, image)
        return bool(detail and detail.hit)

    def _wait_node_hit(
        self, context, node_name: str, attempts: int = 5, interval: float = 1.0
    ) -> bool:
        for _ in range(attempts):
            if stop_requested(context):
                return False
            if self._node_hit(context, node_name):
                return True
            if not interruptible_sleep(context, interval):
                return False
        return False

    def _click_node(
        self, context, node_name: str, attempts: int = 5, interval: float = 0.5
    ) -> bool:
        for _ in range(attempts):
            if stop_requested(context):
                return False
            image = self._screencap(context)
            detail = context.run_recognition(node_name, image)
            if detail and detail.hit and detail.box:
                context.run_action_direct(
                    JActionType.Click, JClick(), tuple(detail.box), ""
                )
                return True
            if not interruptible_sleep(context, interval):
                return False
        return False

    def _ocr_click(
        self,
        context,
        expected: str,
        roi: list,
        attempts: int = 5,
        interval: float = 1.0,
    ) -> bool:
        for _ in range(attempts):
            if stop_requested(context):
                return False
            image = self._screencap(context)
            detail = context.run_recognition_direct(
                JRecognitionType.OCR, JOCR(expected=[expected], roi=roi), image
            )
            if detail and detail.hit and detail.box:
                context.run_action_direct(
                    JActionType.Click, JClick(), tuple(detail.box), ""
                )
                return True
            if not interruptible_sleep(context, interval):
                return False
        return False

    def _boxes_from(self, detail) -> list[tuple]:
        """从识别结果提取 box 列表（兼容 Or 嵌套）"""
        return [b for b, _ in self._boxes_and_scores_from(detail)]

    def _boxes_and_scores_from(
        self, detail, use_filtered: bool = True
    ) -> list[tuple[tuple, float]]:
        """从识别结果提取 (box, score) 列表（兼容 Or 嵌套 sub_results 递归）。

        use_filtered=True 时优先 filtered_results（节点阈值过滤，适合算子等单目标识别）；
        use_filtered=False 时用 all_results 全量结果，供需要几何判断的场景（如草丛弧形识别）。
        """
        source = None
        if use_filtered:
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
                        results.extend(self._boxes_and_scores_from(sd, use_filtered))
        return results

    def _dedupe_boxes(
        self, results: list[tuple[tuple, float]]
    ) -> list[tuple[tuple, float]]:
        """去重：互相重叠面积占比 > 阈值 的框并为一个，保留置信度高者"""
        deduped: list[tuple[tuple, float]] = []
        for box, score in results:
            area = box[2] * box[3]
            merged = False
            for i, (dbox, dscore) in enumerate(deduped):
                inter = self._intersection(box, dbox)
                darea = dbox[2] * dbox[3]
                denom = min(area, darea)
                if denom and inter / denom > self.OVERLAP_THRESHOLD:
                    if score > dscore:
                        deduped[i] = (box, score)
                    merged = True
                    break
            if not merged:
                deduped.append((box, score))
        return deduped

    def _intersection(self, a: tuple, b: tuple) -> int:
        x1 = max(a[0], b[0])
        y1 = max(a[1], b[1])
        x2 = min(a[0] + a[2], b[0] + b[2])
        y2 = min(a[1] + a[3], b[1] + b[3])
        if x2 <= x1 or y2 <= y1:
            return 0
        return (x2 - x1) * (y2 - y1)

    def _arc_tiles(
        self, results: list[tuple[tuple, float]]
    ) -> list[tuple[tuple, float]]:
        """从草丛格中识别出构成目标弧形的格子组（几何判断，不依赖置信度）。

        设计思路：目标是"弧形"形状的草丛，其各格沿一条横向展开、间距均匀的
        曲线排列；另一片装饰草丛（背景草）虽然也匹配模板，但不构成这种连续弧线。
        做法：先按重叠去重（合并同一格的重复检测框），再按格子中心 x 排序，
        把相邻间距落在 [ARC_MIN_DX, ARC_MAX_DX] 的格子连成横向连续段，
        取最长的一段作为弧形目标组。
        """
        deduped = self._dedupe_boxes(results)
        pts = sorted(
            ((b[0] + b[2] / 2, b[1] + b[3] / 2, b, s) for b, s in deduped),
            key=lambda p: p[0],
        )
        if not pts:
            return []
        segments: list[list[tuple[tuple, float]]] = []
        seg = [pts[0]]
        for prev, cur in zip(pts, pts[1:]):
            dx = cur[0] - prev[0]
            if self.ARC_MIN_DX <= dx <= self.ARC_MAX_DX:
                seg.append(cur)
            else:
                segments.append(seg)
                seg = [cur]
        segments.append(seg)
        segments.sort(key=len, reverse=True)
        return [(b, s) for _cx, _cy, b, s in segments[0]]

    def _top_right_tile(self, results: list[tuple[tuple, float]]) -> tuple | None:
        """先识别目标弧形草丛，再取弧形中最右上角的格（y 最小，并列取 x 最大）。"""
        arc = self._arc_tiles(results)
        if not arc:
            return None
        boxes = [b for b, _ in arc]
        boxes.sort(key=lambda b: (b[1], -b[0]))
        return boxes[0]
