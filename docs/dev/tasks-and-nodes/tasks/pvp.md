---
title: 玩家对战
---

# 玩家对战

任务入口：`PVP`

PI 文件：`assets/resource/tasks/PVP.json`

Pipeline 入口文件：`assets/resource/pipeline/PVP.json`

入口节点：`PVPMain`

## 功能概述

玩家对战从主界面点击「对战」入口进入玩家对战界面，自动选择三个对手中**等级最低**的进行挑战，支持多场次循环（1~6 次，由选项 `PVP_BattleCount` 控制），每次战斗结束后识别积分和排名变化，直到次数用尽或今日挑战次数达到上限后返回主界面。

> 移植参考：[MaaKEDR](https://github.com/APPLe-DF/MaaKEDR) 的 `pvp` 任务（ROI、模板图与识别逻辑均来自其实机配置，非 AI 生成）。

## 主要节点

### 入口与路由

- `PVPMain`：任务入口。先尝试 `PVP_Click:Exercise`（主界面直达），未在主界面时通过 `[JumpBack]PVP_Do:JumpToMain` 回到主界面后重试。
- `PVP_Do:JumpToMain`：使用通用 `SceneJump`（`target: "MainMenu"`）从任意界面跳转回主界面；场景图 `scene_jump_map.json` 已包含 `PVP` 场景（`detect: PVP_Verify:BattleInterface`）与 `PVP → MainMenu` 边（`jump: SceneDo_PauseHomeButton`），以及编队界面场景 `Team`（`detect: AutoSweep_Click_Start2`，返回键 `SceneDo_PauseBackButton` 后可能落到 `MainMenu` 或 `PVP`），任意界面重启任务均能正确回主界面。
- `PVP_Click:Exercise`：复用 `UI_MainMenu_exercise`（主界面-对战）识别并点击入口。点击后 `next` 列表中先尝试赛季重置候选 `PVP_Click:SeasonReset_Continue`（识别「点击任意处继续」提示），未命中时由该 next 列表继续尝试 `PVP_Verify:BattleInterface` 确认对战界面（回落发生在父节点 next 列表层面）。赛季重置时依次「点击继续 → 编辑 → 快速编队 → 人数确认 → 保存编队 → 进入布阵 → 保存部署位置」，链内节点均自带重试兜底，完成后回到 `PVP_Verify:BattleInterface` 正常流程。
- `PVP_Verify:BattleInterface`：确认已进入玩家对战界面（`PVP/battle_interface.png`）。

### 选对手

- `PVP_Do:InitBattleCount`：Custom 动作 `InitPVPBattleCount`，初始化战斗计数器（`target_count` 由任务选项注入）。
- `PVP_Select:Opponent`：Custom 识别 `SelectPVPOpponent`，对 3 个对手等级区域分别 OCR（`rois`），选择等级最低的点击（`click_positions`）。
- `PVP_Check:ChallengeLimit`：今日挑战次数用尽（并列候选），命中后通过 `PVP_Log` 输出日志并跳转 `PVP_Click:MainMenu` 结束任务（不弹窗）。

### 战斗

- `PVP_Click:StartBattle`：点击开始战斗（复用通用模板 `UI/Combat/Start2.png`，编队界面「开始战斗」按钮，与自动战斗/扫荡共用）。
- `PVP_Click:BeginCombat`：点击作战开始（复用通用模板 `UI/Combat/Start3.png`）。`timeout: 30000ms` 覆盖长加载场景（loading 画面持续动画，无法 `post_wait_freezes`）；`next` 中自身重试直到 `PVP_Check:InBattle` 命中。
- `PVP_Check:InBattle`：检测是否在战斗中（并列候选），命中后进入 `PVP_Click:Speed2x`。
- `PVP_Click:Speed2x`：点击 2 倍速。
- `PVP_Wait:BattleLoop`：战斗循环等待（`timeout: 300000ms`），轮询 `PVP_Check:BattleEnd`（OCR「跳过」）；超时后走 `on_error` 兜底 `PVP_Read:Result`。

### 结算

- `PVP_Check:BattleEnd`：OCR 识别「跳过」（`only_rec` 直接识别 ROI 并点击）。
- `PVP_Wait:Settlement`：等待结算动画播放完毕。
- `PVP_Read:Result`：Custom 识别 `ReadPVPResult`，读取结果、当前积分/排名及变化值（OCR 使用 `PVP_TextFilter` 颜色遮罩）；结果详情通过 `log_message` 输出到 agent 日志（每次识别成功即打印，无残留），focus 仅保留通用提示（「PVP 战斗结束」）。高级账号失败保护判定：**分数变化区域 OCR 为空 且 结果文字为失败** 才视为保护（本场不扣分）；若结果非失败，则以「变化值未识别」文案区分，避免 OCR/遮罩问题被误判为保护。
- **提示说明**：PVP 不使用弹窗（toast），所有提示均为日志形式 —— 关键事件由 `log_message`（stderr + `info:` 前缀，MFAAvalonia/MXU/VSC 插件均可见）与部分 focus 日志（`Node.PipelineNode.Starting`，仅常规事件如顺序进度/任务完成）输出，避免同一条提示多通道重复。
- `PVP_Click:ExitResult`：点击退出结果界面，循环关闭获得物品弹窗（`[JumpBack]SceneDo_GetItem`）后回到对战界面。

### 循环与退出

- `PVP_Verify:BackToBattleInterface`：确认回到对战界面。
- `PVP_Do:CheckBattleCount`：Custom 动作 `CheckPVPBattleCount`，递减计数器；每次递减后通过 `log_message` 输出「PVP 剩余战斗次数: N」，用完时输出「PVP 战斗次数已用完，返回主界面」并将 `next` 改为 `PVP_Click:MainMenu`。
- `PVP_Click:MainMenu`：复用 `UI_Common_HomeButton` 点击返回主页按钮。
- `PVP_End`：任务完成提示。

## 起点与结束状态

- 起点：任意界面都可，`PVPMain` 会先回到主界面再进入对战。
- 结束：主界面（次数用尽 / 挑战上限）。

## 注意事项

- 与 MaaKEDR 不同，`PVP_Check:ChallengeLimit` 在 `PVP_Select:Opponent` 的 `next` 中作为**普通并列候选**（未加 `[JumpBack]`），挑战次数用尽时以正常成功状态结束任务，而非触发错误兜底。
- 与 MaaKEDR 不同，`PVP_Do:CheckBattleCount` 未设置 `timeout`（MaaKEDR 为 5000ms）：对手识别失败的兜底等待使用默认 20s，加载慢时更稳，代价是异常场景退出稍慢。
- 战斗次数说明：每天 5 次 PVP 机会；高级账号含首次失败保护（首次失败不消耗次数），最多可打 6 场，打满请选「6次」。
- 自动化只负责操作流程，不保证胜负。

## 验收清单

1. 对手选择：三个对手等级 OCR 正确，选最低等级点击。
2. 单场战斗端到端：主界面 → 进对战 → 开战 → 结算 → 回对战界面。
3. 多场循环：按选项次数打完并正常回到主界面。
4. 任意进度重启（战斗中 / 结算中 / 结果界面）都能继续或正确退出。
5. 今日挑战次数用尽时正确提示并回主页。
6. 全量回归：与其它任务（启动、领取奖励、刷取）组合跑一遍无冲突。
