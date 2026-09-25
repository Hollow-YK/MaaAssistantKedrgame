---
title: Auto Sweep (自动刷本)
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# Auto Sweep (自动刷本)

Task entry: `AutoSweep`

PI file: `assets/resource/tasks/AutoSweep.json`

Pipeline entry file: `assets/resource/pipeline/AutoSweep.json`

Entry node: `AutoSweepMain`

## Feature Overview

自动刷本 (Auto Sweep) navigates from the main screen to 出击 (Combat), selects a stage, then enters the stage details screen to sweep quickly using the in-game **自动战斗** (Auto Battle) feature. It supports two modes — drain-all-stamina (auto multiplier) and a fixed count (1–6) — and loops until stamina is depleted or the specified count is reached.

Currently supported modes:

- `MaterialQuests` (资源收集 / Resource Collection): four areas, 特别军费行动 (Special Military Funding Operation), 作战体能训练 (Combat Fitness Training), 兵种能力评级 (Unit Capability Rating), and 载具对抗演练 (Vehicle Combat Drill), have been adapted.
- `SkillMaterial` (技能演练 / Skill Training): no specific stages have been adapted yet.

Core logic is handled by `AutoSweepManager` (a custom action): from entering the stage details screen, it manages unlock checks, enabling Auto Battle, setting the sweep count, stamina checks, and the loop control until the task completes.

## Main Nodes

### Entry and Routing

- `AutoSweepMain`: the 自动刷本 (Auto Sweep) entry point. Its `next` contains `[JumpBack]AutoSweep_Do:JumpToField` as the universal navigation fallback, routing to the target stage page for the selected area.
- `AutoSweep_Do:JumpToField`: universal navigation node. Calls the `SceneJump` custom action (`target` is injected by the option, e.g. `Combat_MaterialQuests_1`), navigating from any screen to the resource-collection area page.
- `AutoSweepStage`: the stage-page verification node. It uses `And` recognition to confirm arrival at the target stage page, then enters the stage-selection flow.

### Stage Selection Flow

- `AutoSweep_Stage`: the stage-selection entry point. It first attempts to swipe to the far left, then recognizes and clicks the target stage.
- `AutoSweep_Stage_Click`: recognizes and clicks the target stage image (`And` recognition; target injected by the option). Clicking enters `AutoSweepManager`.

### Sweep Management (custom)

File: `agent/custom/action/sweep.py`

- `AutoSweepManager`: the sweep manager. It takes over flow control once the stage details screen is entered:
  - Waits for the stage details screen to finish loading (recognizes the sweep switch).
  - Checks whether Auto Battle is unlocked (`AutoSweep_Check_unlock`); notifies failure if locked.
  - Enables the Auto Battle switch (OCR recognizes “打开/关闭”; clicks when “打开” is found).
  - Sets the single-run count: in auto mode, sets to max then decreases by stamina; for a fixed count, normalizes from max/min then adjusts.
  - Checks stamina (`AutoSweep_Check_Stamina`, red-pixel counting) and decreases the count to retry when insufficient.
  - Clicks to start the sweep, enters the pipeline settlement flow, then returns to the switch check for the next round.

### Sweep and Settlement Flow

- `AutoSweep_Click_Start`: recognizes and clicks the “开始扫荡” (Start Sweep) button (`UI/Combat/StageDetails/Sweep_Start.png`).
- `AutoSweep_Check_Stamina2`: fallback stamina check (recognizes the insufficient-stamina dialog `no_stamina.png`). If the dialog is found, it is closed and handled per mode (auto mode decreases the count and retries; fixed count ends immediately).
- `AutoSweep_Click_Start2`: recognizes and clicks the formation screen's “开始战斗” (Start Battle) button (`UI/Combat/Start2.png`, green screen).
  - `next` contains:
    - `[JumpBack]AutoSweep_Click_Stage_finish`: waits for and clicks the settlement screen (`battle_victory.png`), looping until it disappears.
    - `[JumpBack]SceneDo_GetItem`: loops clicking the item-acquisition dialog until it closes.
    - `AutoSweep_BackToStage`: confirms return to the stage details screen (recognizes the sweep switch “打开/关闭”) and ends this round.

### Wrap-up

- `AutoSweepFinish`: task-complete notification node.

## Options

File: `assets/resource/tasks/AutoSweep.json`

- `AutoSweep_Category`: mode selection (资源收集 / 技能演练).
- `AutoSweep_Field_MaterialQuests`: resource-collection area selection (特别军费行动 / 作战体能训练 / 兵种能力评级 / 载具对抗演练).
- `AutoSweep_Stage_MaterialQuests_N`: specific stage selection for each area.
- `AutoSweep_BatchSize`: Auto Battle multiplier (`auto` drain stamina / `1`–`6` fixed count), injected into `AutoSweepManager`’s `custom_action_param.batch_size` via `pipeline_override`.

## Key Design Points

- **Custom / pipeline division of labor**: `AutoSweepManager` handles loop control, count calculation, and stamina determination — logic that is hard to express in pipeline. Concrete UI recognition and clicks are done through pipeline nodes, which the custom calls via `context.run_task` / `context.run_recognition`.
- **Operation interval**: at least 0.5s between every recognition/click operation, to avoid UI not being ready when operations run too fast.
- **Settlement tolerance**: both the settlement screen and the item-acquisition dialog are clicked repeatedly via `[JumpBack]` until they disappear, preventing getting stuck on the settlement screen due to game lag.
