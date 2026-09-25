---
title: 自动刷本
---

# 自动刷本

任务入口：`AutoSweep`

PI 文件：`assets/resource/tasks/AutoSweep.json`

Pipeline 入口文件：`assets/resource/pipeline/AutoSweep.json`

入口节点：`AutoSweepMain`

## 功能概述

自动刷本从主界面进入出击页面，根据用户选择的关卡模式、区域和具体关卡，选关后进入关卡详情，通过游戏内「自动战斗」功能进行快速扫荡。支持清空体力（自动倍率）与指定次数（1-6）两种模式，循环扫荡直到体力耗尽或达到指定次数。

当前支持的模式：

- `MaterialQuests`（资源收集）：已适配 特别军费行动、作战体能训练、兵种能力评级、载具对抗演练 四个区域。
- `SkillMaterial`（技能演练）：尚未适配具体关卡。

核心逻辑由 `AutoSweepManager`（custom action）接管：从进入关卡详情开始，负责解锁检查、开启自动战斗、设置次数、体力检查与循环控制，直到任务完成。

## 主要节点

### 入口与路由

- `AutoSweepMain`：自动刷本入口。`next` 中以 `[JumpBack]AutoSweep_Do:JumpToField` 作为通用导航兜底，前往所选区域的关卡页面。
- `AutoSweep_Do:JumpToField`：通用导航节点。调用 `SceneJump` custom action（`target` 由选项注入，如 `Combat_MaterialQuests_1`），从任意界面跳转到资源收集对应区域页面。
- `AutoSweepStage`：关卡页面确认节点。使用 `And` 识别确认已到达目标关卡页面，然后进入选关流程。

### 选关流程

- `AutoSweep_Stage`：选关入口。先尝试滑到最左侧，再依次识别并点击目标关卡。
- `AutoSweep_Stage_Click`：识别并点击目标关卡图片（`And` 识别，目标由选项注入）。点击后进入 `AutoSweepManager`。

### 扫荡管理（custom）

文件：`agent/custom/action/sweep.py`

- `AutoSweepManager`：扫荡管理器。进入关卡详情后接管流程控制：
  - 等待关卡详情界面加载完成（识别扫荡开关）。
  - 检查自动战斗是否解锁（`AutoSweep_Check_unlock`），未解锁则通知失败。
  - 开启自动战斗开关（OCR 识别"打开/关闭"，识别到"打开"则点击）。
  - 设置单次次数：自动倍率先设最大再按体力递减；指定次数从最大/最小归位后加减。
  - 检查体力（`AutoSweep_Check_Stamina`，红像素计数），不足时递减次数重试。
  - 点击开始扫荡，进入 pipeline 结算流程，结束后回到开关确认，继续下一轮。

### 扫荡与结算流程

- `AutoSweep_Click_Start`：识别并点击「开始扫荡」按钮（`UI/Combat/StageDetails/Sweep_Start.png`）。
- `AutoSweep_Check_Stamina2`：保底体力确认（识别体力不足弹窗 `no_stamina.png`）。识别到弹窗则关闭后按模式处理（自动倍率减次重试 / 指定次数直接结束）。
- `AutoSweep_Click_Start2`：识别并点击编队界面「开始战斗」按钮（`UI/Combat/Start2.png`，绿幕）。
  - next 包含：
    - `[JumpBack]AutoSweep_Click_Stage_finish`：等待并点击结算画面（`battle_victory.png`），循环直到消失。
    - `[JumpBack]SceneDo_GetItem`：获得物品弹窗循环点击，直到弹窗关闭。
    - `AutoSweep_BackToStage`：确认已回到关卡详情（识别扫荡开关"打开/关闭"）后结束本轮。

### 收尾

- `AutoSweepFinish`：任务完成通知节点。

## 选项

文件：`assets/resource/tasks/AutoSweep.json`

- `AutoSweep_Category`：模式选择（资源收集 / 技能演练）。
- `AutoSweep_Field_MaterialQuests`：资源收集区域选择（特别军费行动 / 作战体能训练 / 兵种能力评级 / 载具对抗演练）。
- `AutoSweep_Stage_MaterialQuests_N`：各区域的具体关卡选择。
- `AutoSweep_BatchSize`：自动战斗倍率（`auto` 清空体力 / `1`-`6` 指定次数），通过 `pipeline_override` 注入 `AutoSweepManager` 的 `custom_action_param.batch_size`。

## 关键设计

- **custom 与 pipeline 分工**：`AutoSweepManager` 负责循环控制、次数计算、体力判定等 pipeline 难以表达的逻辑；具体 UI 识别与点击通过 pipeline 节点完成，custom 通过 `context.run_task` / `context.run_recognition` 调用。
- **操作间隔**：所有识别与点击操作之间至少间隔 0.5s，避免操作过快导致界面未就绪。
- **结算容错**：结算画面与获得物品弹窗均通过 `[JumpBack]` 反复点击直到消失，防止游戏卡顿导致卡在结算界面。
