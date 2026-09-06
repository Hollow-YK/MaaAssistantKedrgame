from __future__ import annotations

import heapq
import json
import time
import traceback
from pathlib import Path
from typing import Any

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

from .general import parse_params

# 场景跳转关系表（与本模块同目录，不依赖 cwd）
MAP_FILE = Path(__file__).resolve().parent / "scene_jump_map.json"


def _strip_jsonc_comments(text: str) -> str:
    """移除 JSONC 注释（// 与 /* */），保留字符串/转义，并维持行号。

    scene_jump_map.json 允许写注释（agent 运行时无法引用 tools/，此处自包含实现）。
    """
    result = []
    state = 0  # 0=普通, 1=字符串内, 2=转义
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if state == 0:
            if ch == '"':
                result.append(ch)
                state = 1
                i += 1
            elif text.startswith("//", i):
                i += 2
                while i < n and text[i] != "\n":
                    i += 1
                if i < n:
                    result.append("\n")  # 保留换行以维持行号
                    i += 1
            elif text.startswith("/*", i):
                i += 2
                while i + 1 < n and not text.startswith("*/", i):
                    if text[i] == "\n":
                        result.append("\n")
                    i += 1
                i = min(i + 2, n)
            else:
                result.append(ch)
                i += 1
        elif state == 1:
            result.append(ch)
            if ch == "\\":
                state = 2
            elif ch == '"':
                state = 0
            i += 1
        else:  # state == 2（转义）
            result.append(ch)
            state = 1
            i += 1
    return "".join(result)


@AgentServer.custom_action("SceneJump")
class SceneJump(CustomAction):
    """通用场景跳转 Custom。

    根据 scene_jump_map.json 中记录的各场景跳转关系，自动判断当前场景，
    规划最短路径，并通过多次“一步跳转”最终到达目标场景。

    数据文件（scene_jump_map.json）格式：
      - scenes: 场景名 → { desc, detect(用于识别该场景的 pipeline 节点，可选；缺省表示仅作 parent 的抽象场景，不直接识别), parent(父场景,可选) }
      - edges:  跳转关系 { from, to, cost(该一步跳转的成本,缺省1,数值越小越优先), jump(一步跳转要执行的 pipeline 节点名或列表，可为空), via(中间场景列表) }
        to 可为单个场景名或场景名列表：列表表示执行 jump 后有概率进入其中任意一个场景（例如
        进游戏可能落到主界面或签到页）；落到非目标候选时，会沿该候选继续规划下一步。
        其中 via 表示跳转过程中“可能经过”的中间场景（并不保证一定经过，也可能略过）。

    jump 为空（[]）时表示：from 场景无需任何操作，等待后必然会在某一刻自然进入 to 场景。

    路径规划：当两个场景间存在多条路径时，使用 Dijkstra 求“总成本最小”的路径
    （路径成本 = 各边 cost 之和），而非单纯的步数最少。

    父场景（parent）不仅参与“是否已到目标”的判断，规划时处于子场景也可使用父场景的出边
    （例如 MainMenu → Combat_MainStory，再借 Combat 的出边到达 Combat_SkillMaterial）。

    容错行为：
      - 未知界面、或当前场景没有通往其它界面的路径时，会进行等待（场景可能自行变化）；
        最多等待 wait_timeout 秒，超时按失败处理。
      - 因游戏 bug 点击/事件可能丢失：执行 jump 后若仍停留在 from，等待 retry_interval 秒后
        再次执行 jump（最多 max_attempts 次）。
      - 同一时刻可能有多个场景同时满足识别（如出击页与其子 Tab）：这些场景都可作起点，
        自动选择“到目标总成本最小”的那一个。

    custom_action_param 支持：
      - target: 目标场景名（必填），如 "Status_In_MainMenu"、"Status_In_Combat_MaterialQuests"；
                也可直接把 custom_action_param 写成目标场景名字符串
      - max_attempts: 单条边内 jump 重试次数，默认 3
      - settle_interval: 轮询检测间隔（秒），默认 1.0
      - retry_interval: jump 后仍停留在 from 时的重试间隔（秒），默认 10
      - wait_timeout: 未知界面/无路径/等待自然跳转的最大等待（秒），默认 300
      - max_total_edges: 整个流程最多执行的跳转边数（防循环），默认 30
      - strict: true 时遇到未记录的意外场景直接失败（默认 false，自动重新规划）

    示例：
        custom_action_param: {"target": "Status_In_Combat_MaterialQuests"}
        或
        custom_action_param: "Status_In_Combat_MaterialQuests"
    """

    DEFAULT_MAX_ATTEMPTS = 3
    DEFAULT_SETTLE_INTERVAL = 1.0
    DEFAULT_RETRY_INTERVAL = 10.0
    DEFAULT_WAIT_TIMEOUT = 300.0
    DEFAULT_MAX_TOTAL_EDGES = 30

    def __init__(self) -> None:
        super().__init__()  # 初始化基类 _handle（AgentServer 注册时需要 c_handle）
        self.scenes: dict[str, dict[str, Any]] = {}
        self._adj: dict[str, list[dict[str, Any]]] = {}
        self._descendants_cache: dict[str, set[str]] = {}

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
        raw = argv.custom_action_param
        params = parse_params(raw)
        if isinstance(raw, str) and raw.strip():
            # 兼容直接把目标场景名作为参数传入
            params.setdefault("target", raw.strip())

        target = self._resolve_target(params)
        if not target:
            print("[SceneJump] 缺少目标场景参数 target（如 Status_In_MainMenu）")
            return CustomAction.RunResult(success=False)

        if not self._load_map():
            print("[SceneJump] 加载场景跳转关系表失败")
            return CustomAction.RunResult(success=False)

        if target not in self.scenes:
            print(
                f"[SceneJump] 未知目标场景: {target}，请检查 scene_jump_map.json 的 scenes"
            )
            return CustomAction.RunResult(success=False)

        max_attempts = int(params.get("max_attempts", self.DEFAULT_MAX_ATTEMPTS))
        settle_interval = float(
            params.get("settle_interval", self.DEFAULT_SETTLE_INTERVAL)
        )
        retry_interval = float(
            params.get("retry_interval", self.DEFAULT_RETRY_INTERVAL)
        )
        wait_timeout = float(params.get("wait_timeout", self.DEFAULT_WAIT_TIMEOUT))
        max_total_edges = int(
            params.get("max_total_edges", self.DEFAULT_MAX_TOTAL_EDGES)
        )
        strict = bool(params.get("strict", False))

        print(f"[SceneJump] 目标场景: {target}（{self._desc(target)}）")

        matches = self._detect_scenes(context)
        if matches:
            print(
                "[SceneJump] 当前匹配场景: "
                + ", ".join(f"{m}（{self._desc(m)}）" for m in matches)
            )
        else:
            print("[SceneJump] 当前为未知界面")

        current = None
        if matches:
            current, _ = self._best_start(matches, target)

        if current is not None and self._satisfies(current, target):
            print("[SceneJump] 已在目标场景，无需跳转")
            return CustomAction.RunResult(success=True)

        # 总等待预算：未知界面/无路径/等待自然跳转/点击丢失重试 共用，超时按失败处理
        deadline = time.time() + wait_timeout
        visited: set[str] = set()
        if current is not None:
            visited.add(current)
        edges_done = 0

        while True:
            if time.time() >= deadline:
                print(f"[SceneJump] 等待超时（超过 {wait_timeout}s），终止")
                return CustomAction.RunResult(success=False)

            if current is None:
                # 未知界面：等待场景出现（场景可能自行变化）
                print("[SceneJump] 当前为未知界面，等待场景出现……")
                scene = self._wait_for_change(
                    context, None, target, deadline, settle_interval
                )
                if scene is None:
                    print("[SceneJump] 等待场景出现超时")
                    return CustomAction.RunResult(success=False)
                current = self._pick_best_start(context, target, scene)
                if current is None:
                    current = scene
                if self._satisfies(current, target):
                    print(f"[SceneJump] 已到达目标场景: {target}")
                    return CustomAction.RunResult(success=True)
                visited.add(current)
                continue

            if self._satisfies(current, target):
                print(f"[SceneJump] 已到达目标场景: {target}（{self._desc(target)}）")
                return CustomAction.RunResult(success=True)

            if edges_done >= max_total_edges:
                print(f"[SceneJump] 超过总跳转次数上限 {max_total_edges}，终止")
                return CustomAction.RunResult(success=False)

            path = self._plan(current, target)
            if not path:
                # 当前场景没有通往目标的路径（可能是死胡同）：等待场景自行变化
                print(
                    f"[SceneJump] 当前 {current} 无通往 {target} 的路径，"
                    "等待场景变化……"
                )
                current = self._wait_for_change(
                    context, current, target, deadline, settle_interval
                )
                if current is None:
                    print("[SceneJump] 等待场景变化超时")
                    return CustomAction.RunResult(success=False)
                current = self._pick_best_start(context, target, current)
                if current is None:
                    continue
                if self._satisfies(current, target):
                    print(f"[SceneJump] 已到达目标场景: {target}")
                    return CustomAction.RunResult(success=True)
                if current in visited:
                    print(f"[SceneJump] 回到已访问场景 {current}，疑似循环，终止")
                    return CustomAction.RunResult(success=False)
                visited.add(current)
                continue

            print(
                "[SceneJump] 规划路径: "
                + " -> ".join(e["from"] for e in path)
                + f" -> {target}"
            )
            edge = path[0]
            print(
                f"[SceneJump] 执行跳转: {edge['from']} -> {edge['to']}"
                f"（节点: {edge.get('jump')}，中间: {edge.get('via') or []}）"
            )
            reached, actual = self._execute_edge(
                context, edge, max_attempts, settle_interval, retry_interval, deadline
            )
            edges_done += 1

            if reached:
                current = actual if actual is not None else edge["to"][0]
                visited.add(current)
                continue

            # 未到达该边目标场景
            if strict:
                print(
                    f"[SceneJump] 跳转至 {edge['to']} 失败（实际: {actual}），"
                    "strict 模式终止"
                )
                return CustomAction.RunResult(success=False)
            if actual is None:
                print(f"[SceneJump] 跳转至 {edge['to']} 等待超时/无法识别场景，终止")
                return CustomAction.RunResult(success=False)
            if actual in visited:
                print(f"[SceneJump] 跳转后回到已访问场景 {actual}，疑似循环，终止")
                return CustomAction.RunResult(success=False)

            print(f"[SceneJump] 实际落在 {actual}，重新规划路径……")
            current = self._pick_best_start(context, target, actual)
            if current is None:
                current = actual
            if current in visited:
                print(f"[SceneJump] 回到已访问场景 {current}，疑似循环，终止")
                return CustomAction.RunResult(success=False)
            visited.add(current)

        print(f"[SceneJump] 已到达目标场景: {target}（{self._desc(target)}）")
        return CustomAction.RunResult(success=True)

    # ------------------------------------------------------------------
    # 路径规划与场景判断
    # ------------------------------------------------------------------
    def _resolve_target(self, params: dict[str, Any]) -> str | None:
        for key in ("target", "scene", "scene_name", "to"):
            val = params.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return None

    def _load_map(self) -> bool:
        try:
            with open(MAP_FILE, "r", encoding="utf-8-sig") as f:
                data = json.loads(_strip_jsonc_comments(f.read()))
        except Exception:
            traceback.print_exc()
            return False

        scenes = data.get("scenes", {})
        if not isinstance(scenes, dict) or not scenes:
            return False
        self.scenes = scenes
        self._adj = {}
        for edge in data.get("edges", []):
            if not isinstance(edge, dict):
                continue
            frm = edge.get("from")
            if not frm or frm not in scenes:
                continue
            # to 支持单个场景名或场景名列表（操作后有概率进入其中任意一个）
            raw_to = edge.get("to")
            if isinstance(raw_to, str):
                to_list = [raw_to]
            elif isinstance(raw_to, list):
                to_list = [t for t in raw_to if isinstance(t, str)]
            else:
                continue
            to_list = [t for t in to_list if t in scenes]
            if not to_list:
                continue
            edge["to"] = to_list  # 归一化为列表，后续统一处理
            self._adj.setdefault(frm, []).append(edge)
        # 构建后代索引以支持定向探测
        self._build_descendants_cache()
        return True

    def _build_descendants_cache(self) -> None:
        """构建父场景 -> 所有具有 detect 的后代场景 的映射"""
        self._descendants_cache = {}
        # 先收集所有有 detect 的场景（即实际可识别的场景）
        detectable = {name for name, info in self.scenes.items() if info.get("detect")}

        for name in detectable:
            # 向上遍历父链，将自身加入每个父节点的后代集合
            cur = name
            while cur:
                parent = self.scenes.get(cur, {}).get("parent")
                if parent:
                    self._descendants_cache.setdefault(parent, set()).add(name)
                cur = parent
            # 自身也加入自己的缓存（方便直接查）
            self._descendants_cache.setdefault(name, set()).add(name)

    def _desc(self, name: str) -> str:
        scene = self.scenes.get(name) or {}
        return str(scene.get("desc", ""))

    def _satisfies(self, scene: str | None, target: str) -> bool:
        """scene 是否满足目标 target：scene 自身，或 scene 的父场景链上存在 target。"""
        if scene is None:
            return False
        cur: str | None = scene
        while cur:
            if cur == target:
                return True
            node = self.scenes.get(cur) or {}
            cur = node.get("parent")
        return False

    def _satisfies_any(self, scene: str | None, targets: list[str]) -> bool:
        """scene 是否满足 targets 中的任意一个目标（to 为列表时使用）。"""
        if scene is None:
            return False
        return any(self._satisfies(scene, t) for t in targets)

    @staticmethod
    def _edge_cost(edge: dict[str, Any]) -> float:
        """读取边成本（缺省 1），非法值按 1 处理。"""
        try:
            return float(edge.get("cost", 1))
        except (TypeError, ValueError):
            return 1.0

    def _adj_edges(self, scene: str) -> list[dict[str, Any]]:
        """scene 可用的出边 = 自身出边 + 所有父场景（parent 链）的出边。

        处于子场景（如 Combat_MainStory）即视为处于父场景（Combat），因此可执行父场景的
        任意出边（例如在出击页任意 Tab 上都能点击技能演练 Tab）。
        """
        edges: list[dict[str, Any]] = list(self._adj.get(scene, []))
        node = self.scenes.get(scene) or {}
        parent = node.get("parent")
        while parent:
            edges.extend(self._adj.get(parent, []))
            node = self.scenes.get(parent) or {}
            parent = node.get("parent")
        return edges

    def _plan(self, start: str, target: str) -> list[dict[str, Any]] | None:
        """Dijkstra 求“总成本最小”路径，返回边序列；start 已满足 target 时返回空列表。

        路径成本 = 各边 cost 之和；存在多条路径时优先总成本最小的那一条。
        """
        if self._satisfies(start, target):
            return []
        best_cost: dict[str, float] = {start: 0.0}
        prev: dict[str, tuple[dict[str, Any], str]] = {}
        visited: set[str] = set()
        heap: list[tuple[float, str]] = [(0.0, start)]
        while heap:
            cost, cur = heapq.heappop(heap)
            if cur in visited:
                continue
            visited.add(cur)
            if self._satisfies(cur, target):
                path: list[dict[str, Any]] = []
                node = cur
                while node in prev:
                    edge2, parent = prev[node]
                    path.append(edge2)
                    node = parent
                path.reverse()
                return path
            for edge in self._adj_edges(cur):  # 自身出边 + 父场景出边
                for nxt in edge["to"]:  # to 可能是多个候选场景
                    if nxt in visited:
                        continue
                    new_cost = cost + self._edge_cost(edge)
                    if new_cost < best_cost.get(nxt, float("inf")):
                        best_cost[nxt] = new_cost
                        prev[nxt] = (edge, cur)
                        heapq.heappush(heap, (new_cost, nxt))
        return None

    def _best_start(
        self, matches: list[str], target: str
    ) -> tuple[str | None, list[dict[str, Any]] | None]:
        """从多个同时匹配的场景中，选“到目标总成本最小”的起点。

        返回 (起点场景名, 起点到目标的最短路径)；起点已满足目标时路径为空列表；
        所有候选都无法到达目标时返回 (None, None)。
        """
        best_scene: str | None = None
        best_path: list[dict[str, Any]] | None = None
        best_cost = float("inf")
        for m in matches:
            if self._satisfies(m, target):
                return m, []
            path = self._plan(m, target)
            if not path:
                continue
            cost = sum(self._edge_cost(e) for e in path)
            if cost < best_cost:
                best_cost = cost
                best_scene = m
                best_path = path
        return best_scene, best_path

    def _pick_best_start(
        self, context: Context, target: str, fallback: str | None
    ) -> str | None:
        """重新检测所有匹配场景，选最短路径起点；无匹配时返回 fallback。"""
        matches = self._detect_scenes(context)
        if not matches:
            return fallback
        best, _ = self._best_start(matches, target)
        return best if best is not None else fallback

    # ------------------------------------------------------------------
    # 场景检测
    # ------------------------------------------------------------------
    def _screencap(self, context: Context) -> Any:
        """主动刷新截图并返回"""
        context.tasker.controller.post_screencap().wait()
        return context.tasker.controller.cached_image

    def _detect_scene(self, context: Context) -> str | None:
        """按 scenes 定义顺序检测当前场景（更具体的场景优先，返回第一个命中的）。

        无 detect 的场景视为“仅作 parent 的抽象场景”，不可直接识别，跳过。
        """
        image = self._screencap(context)
        for name, scene in self.scenes.items():
            node = scene.get("detect")
            if not node:
                continue  # 仅作 parent，无独立识别
            detail = context.run_recognition(str(node), image)
            if detail and detail.hit:
                return name
        return None

    def _detect_scenes(self, context: Context) -> list[str]:
        """检测所有当前同时匹配的场景（同一时刻可能有多个场景同时满足识别）。"""
        image = self._screencap(context)
        matches: list[str] = []
        for name, scene in self.scenes.items():
            node = scene.get("detect")
            if not node:
                continue  # 仅作 parent，无独立识别
            detail = context.run_recognition(str(node), image)
            if detail and detail.hit:
                matches.append(name)
        return matches

    def _detect_scenes_subset(
        self, context: Context, candidates: set[str]
    ) -> list[str]:
        """仅对候选场景列表进行识别，返回其中命中的场景（按 scenes 定义顺序）。"""
        image = self._screencap(context)
        matches: list[str] = []
        # 按照 self.scenes 的定义顺序遍历，保证确定性（具体场景优先）
        for name, scene in self.scenes.items():
            if name not in candidates:
                continue
            node = scene.get("detect")
            if not node:
                continue
            detail = context.run_recognition(str(node), image)
            if detail and detail.hit:
                matches.append(name)
        return matches

    # ------------------------------------------------------------------
    # 单步跳转执行与等待
    # ------------------------------------------------------------------
    @staticmethod
    def _run_jump_node(context: Context, node: str) -> None:
        """执行单个 jump 节点：仅做该节点本身，忽略其 next 链。

        用 pipeline_override 把该节点的 next 清空，run_task 执行完当前节点即终止，
        不会级联执行 next 里的后续节点（如 Award_DailyAward_Click:Get 不再顺带
        执行 Award_DailyAward_MonthlyPlan / AnySceneEnter_MainMenu）。
        覆盖仅对本次调用生效，不影响 context 中其它流程。
        """
        context.run_task(node, {node: {"next": []}})

    def _execute_edge(
        self,
        context: Context,
        edge: dict[str, Any],
        max_attempts: int,
        settle_interval: float,
        retry_interval: float,
        deadline: float,
    ) -> tuple[bool, str | None]:
        """执行一条边（一步跳转），直到到达该边目标场景或超时。

        返回 (是否到达该边目标场景, 最终检测到的场景名)。
        未到达时：落在非预期已知场景返回 (False, 该场景名)；等待超时返回 (False, None)。

        规则：
          - jump 可为空（[]）：表示 from 场景无需任何操作，等待后必然自然进入 to；
          - 执行 jump 后若仍停留在 from（游戏点击可能丢失），等待 retry_interval 后重试
            jump（最多 max_attempts 次）；
          - via 表示“可能经过”的中间场景（也可能略过），处于 via 时继续等待其结束；
          - 未知界面（无法识别）时继续等待；
          - 全程受 deadline（wait_timeout）约束，超时返回失败。
        优化：使用定向探测（_detect_scenes_subset）替代全量扫描，
        仅识别与当前边相关的候选场景及其后代，大幅减少模板匹配次数。
        仅在定向探测未命中或命中意外场景时回退全量识别。"""
        targets = edge["to"]  # 可能为多个候选场景（to 列表）
        from_scene = edge["from"]
        vias = set(edge.get("via") or [])
        jumps = edge.get("jump")
        if isinstance(jumps, str):
            jumps = [jumps]
        elif not isinstance(jumps, list):
            jumps = []

        def _left() -> float:
            return max(0.0, deadline - time.time())

        def _nap(seconds: float) -> None:
            time.sleep(min(seconds, _left()))

        # ---- 构建定向探测候选集 ----
        base_candidates = set(targets)
        base_candidates.add(from_scene)
        base_candidates.update(vias)

        # 扩展所有后代（可识别场景）
        probe_candidates: set[str] = set()
        for base in base_candidates:
            probe_candidates.update(self._descendants_cache.get(base, set()))

        # 如果候选集意外为空（例如所有场景都无 detect），回退全量
        if not probe_candidates:
            probe_candidates = set(self.scenes.keys())

        # 1) 首次执行 jump（若有；空 jump 表示无需操作，仅等待自然跳转）
        for node in jumps:
            if time.time() >= deadline:
                return False, None
            self._run_jump_node(context, str(node))

        # 2) 轮询等待场景变化（定向探测候选场景及其后代）
        retries = 1 if jumps else 0  # 已执行 jump 的次数
        while time.time() < deadline:
            # 定向探测：仅识别候选场景
            matched = self._detect_scenes_subset(context, probe_candidates)

            if not matched:
                # 定向未命中任何候选 -> 可能进入了完全意外的场景，回退全量识别
                full_matches = self._detect_scenes(context)
                if not full_matches:
                    # 未知界面：等待（可能处于过渡中）
                    _nap(settle_interval)
                    continue
                # 返回意外场景，由主循环重新规划
                return False, full_matches[0]

            # 命中目标：任意匹配场景满足任一 to → 返回最具体的那个
            hit = next((s for s in matched if self._satisfies_any(s, targets)), None)
            if hit is not None:
                return True, hit

            if from_scene in matched and jumps:
                # jump 后仍停留在 from：可能点击丢失 → 等待后重试 jump
                if retries < max_attempts:
                    _nap(retry_interval)
                    for node in jumps:
                        self._run_jump_node(context, str(node))
                    retries += 1
                    continue
                # 重试次数用尽，继续等待到超时
                _nap(settle_interval)
                continue

            if any(s in vias or s == from_scene for s in matched):
                # 中间场景（via 可能经过也可能略过）或空 jump 的自然过渡等待
                _nap(settle_interval)
                continue

            # 命中了某个场景，但不是目标、不是 via、也不是 from
            # 回退全量识别以获取准确场景名并重新规划
            full_matches = self._detect_scenes(context)
            if not full_matches:
                return False, matched[0]  # 以定向结果为准
            return False, full_matches[0]

        return False, None  # 等待超时

    def _wait_for_change(
        self,
        context: Context,
        stuck_scene: str | None,
        target: str,
        deadline: float,
        interval: float,
    ) -> str | None:
        """在未知界面或“无路径”的死胡同等待场景自行变化。

        返回新的已知场景（期间若已满足 target 也返回该场景）；超时返回 None。

        优化：定向探测 target 及其后代，而非全量扫描。
        """
        # 构建目标的后代候选集
        probe_candidates = set(self._descendants_cache.get(target, {target}))
        # 确保 stuck_scene 也在候选里（避免误判变化）
        if stuck_scene:
            probe_candidates.add(stuck_scene)

        while time.time() < deadline:
            # 定向探测目标及相关场景
            matched = self._detect_scenes_subset(context, probe_candidates)
            if not matched:
                time.sleep(min(interval, max(0.0, deadline - time.time())))
                continue

            # 如果命中了目标（或其后代）
            if any(self._satisfies(s, target) for s in matched):
                return matched[0]  # 返回命中的具体场景

            # 如果离开 stuck_scene 到了其他已知场景（但不是目标），返回它
            if stuck_scene and stuck_scene not in matched:
                return matched[0]

            time.sleep(min(interval, max(0.0, deadline - time.time())))
        return None
