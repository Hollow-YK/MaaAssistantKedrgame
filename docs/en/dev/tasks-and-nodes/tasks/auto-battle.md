---
title: Auto Battle (自动战斗)
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# Auto Battle (自动战斗)

Task entry: `AutoBattle`

PI file: `assets/resource/tasks/AutoBattle.json`

Pipeline entry file: `assets/resource/pipeline/AutoBattle.json`

Subflow directory: `assets/resource/pipeline/AutoBattle/`

Entry node: `AutoBattleMain`

## Feature Overview

自动战斗 (Auto Battle) navigates from the main screen to 出击 (Combat), then automatically completes stage selection, formation confirmation, battle startup, and result waiting according to the stage mode, area, and specific stage selected by the user. A loop count can be configured to repeat the stage.

Currently supported modes:

- `MainStory` (主线任务 / Main Story): no specific stages have been adapted yet.
- `MaterialQuests` (资源收集 / Resource Collection): two areas, 特别军费行动 (Special Military Funding Operation) and 作战体能训练 (Combat Fitness Training), have been adapted.
- `SkillMaterial` (技能演练 / Skill Training): no specific stages have been adapted yet.

## Main Nodes

### Entry and Routing

- `AutoBattleMain`: the 自动战斗 (Auto Battle) entry point. It receives `pipeline_override` from the options to dynamically modify `next`, routing to the `AnySceneEnter_Combat_*` node for the selected stage.
- `AutoBattleStage`: the stage-page verification node. It uses `And` recognition to confirm arrival at the target stage page, then enters the battle loop.

### Loop Control

- `AutoBattleLoop`: the loop-control node. The loop count is set through `max_hit`, injected by the `AutoBattle_Looptimes` option.
- `AutoBattleFinish`: the cleanup node used after the loop ends.

### Stage Selection Flow

File: `assets/resource/pipeline/AutoBattle/MaterialQuests.json`

- `AutoBattle_Stage_MaterialQuests`: the stage-selection entry point. It first attempts to swipe to the far left, then recognizes and clicks the target stage.
- `AutoBattle_Stage_MaterialQuests_Swipe2begin`: swipes to the far left of the stage list (`max_hit: 3`).
- `AutoBattle_Stage_MaterialQuests_Swipe2next`: swipes right to find the target stage; `max_hit` is injected by an option.
- `AutoBattle_Stage_MaterialQuests_Click`: recognizes and clicks the target stage image using `And` recognition with high-threshold template matching (`threshold: 0.96`).

### Battle Flow

- `AutoBattle_MaterialQuests_Click:Start`: recognizes and clicks the “准备战斗” (Prepare for Battle) button (`UI/Combat/Start.png`).
- `AutoBattle_MaterialQuests_Click:Start2`: recognizes and clicks the formation screen's “开始战斗” (Start Battle) button (`UI/Combat/Start2.png`, green screen). A loading screen may appear after the click.
- `AutoBattle_MaterialQuests_Click:Start3`: recognizes and clicks the in-map “作战开始” (Commence Operation) button (`UI/Combat/Start3.png`). The battle begins after the click.
  - `next` contains:
    - `[JumpBack]AutoBattle_MaterialQuests_Click:speed2x`: attempts to enable 2× speed. (Not handled yet.)
    - `[JumpBack]UI_Combat_InStage_active`: waits while the battle is in progress.
    - `[JumpBack]SceneDo_Click_Stage_finish`: waits for the results.
    - `[JumpBack]SceneDo_GetItem`: claims the battle rewards.
    - `AutoBattleStage`: returns to the stage page to begin the next loop.
