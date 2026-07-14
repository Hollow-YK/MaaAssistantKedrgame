---
title: 自动战斗
---

# 自动战斗

任务入口：`AutoBattle`

PI 文件：`assets/resource/tasks/AutoBattle.json`

Pipeline 入口文件：`assets/resource/pipeline/AutoBattle.json`

子流程目录：`assets/resource/pipeline/AutoBattle/`

入口节点：`AutoBattleMain`

## 功能概述

自动战斗从主界面进入出击页面，根据用户选择的关卡模式、区域和具体关卡，自动完成选关、编队确认、作战开始、等待结算等流程。支持设置循环次数以重复刷关卡。

当前支持的模式：

- `MainStory`（主线任务）：尚未适配具体关卡。
- `MaterialQuests`（资源收集）：已适配 特别军费行动、作战体能训练 两个区域。
- `SkillMaterial`（技能演练）：尚未适配具体关卡。

## 主要节点

### 入口与路由

- `AutoBattleMain`：自动战斗入口。接收选项中的 `pipeline_override` 来动态修改 `next`，跳转到对应关卡的 `AnySceneEnter_Combat_*` 节点。
- `AutoBattleStage`：关卡页面确认节点。使用 `And` 识别确认已到达目标关卡页面，然后进入战斗循环。

### 循环控制

- `AutoBattleLoop`：循环控制节点，通过 `max_hit` 设置循环次数（由选项 `AutoBattle_Looptimes` 注入）。
- `AutoBattleFinish`：循环结束后的收尾节点。

### 选关流程

文件：`assets/resource/pipeline/AutoBattle/MaterialQuests.json`

- `AutoBattle_Stage_MaterialQuests`：选关入口。先尝试滑到最左侧，再依次识别并点击目标关卡。
- `AutoBattle_Stage_MaterialQuests_Swipe2begin`：滑动到关卡列表最左侧（`max_hit: 3`）。
- `AutoBattle_Stage_MaterialQuests_Swipe2next`：向右滑动寻找目标关卡（`max_hit` 由选项注入）。
- `AutoBattle_Stage_MaterialQuests_Click`：识别并点击目标关卡图片（`And` 识别高阈值模板匹配，`threshold: 0.96`）。

### 作战流程

- `AutoBattle_MaterialQuests_Click:Start`：识别并点击「准备战斗」按钮（`UI/Combat/Start.png`）。
- `AutoBattle_MaterialQuests_Click:Start2`：识别并点击编队界面「开始战斗」按钮（`UI/Combat/Start2.png`，绿幕）。点击后可能进入加载界面。
- `AutoBattle_MaterialQuests_Click:Start3`：识别并点击地图内「作战开始」按钮（`UI/Combat/Start3.png`）。点击后进入战斗过程。
  - next 包含：
    - `[JumpBack]AutoBattle_MaterialQuests_Click:speed2x`：尝试二倍速。（暂未处理）
    - `[JumpBack]UI_Combat_InStage_active`：等待战斗中。
    - `[JumpBack]SceneDo_Click_Stage_finish`：等待结算。
    - `[JumpBack]SceneDo_GetItem`：领取结算奖励。
    - `AutoBattleStage`：返回关卡页面开始下一次循环。
