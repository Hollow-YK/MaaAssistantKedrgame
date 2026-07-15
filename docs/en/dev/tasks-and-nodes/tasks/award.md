---
title: Claim Rewards (领取奖励)
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# Claim Rewards (领取奖励)

Task entry: `Award`

Task file: `assets/resource/tasks/Award.json`

Pipeline entry file: `assets/resource/pipeline/Award.json`

Subflow directory: `assets/resource/pipeline/Award/`

Entry node: `AwardMain`

Two subfeatures are currently included:

- `Award_MaintenanceArea`: 资源派遣奖励 (Resource Dispatch Rewards).
- `Award_Task`: daily, weekly, and achievement task rewards.

`AwardMain` chains the subfeatures with `[JumpBack]`. `AwardSub_MaintenanceArea` and `AwardSub_Task` use `max_hit: 1` to ensure that each subflow is entered only once.

## Resource Dispatch Rewards

File: `assets/resource/pipeline/Award/MaintenanceArea.json`

Main nodes:

- `Award_MaintenanceArea`: the Resource Dispatch Rewards entry point.
- `Award_MaintenanceArea_Enter:MainMenu_list_maintenancearea`: recognizes and clicks the 资源派遣 (Resource Dispatch) entry on the main screen.
- `Award_MaintenanceArea_Click:GetAll`: recognizes and clicks “一键领取” (Claim All).
- `Award_MaintenanceArea_Click:Again`: confirms dispatching again according to the selected option.
- `Award_MaintenanceArea_Click:NotAgain`: closes the dispatch-again pop-up according to the selected option.
- `Award_MaintenanceArea_Click:Close`: closes the Resource Dispatch page.
- `Award_MaintenanceArea_OCR:Alert_Again`: recognizes the text in the dispatch-again pop-up.

Related options are configured in `assets/resource/tasks/Award.json`; `pipeline_override` controls whether the `Again` or `NotAgain` node is enabled.

## Task Rewards

File: `assets/resource/pipeline/Award/Task.json`

Main nodes:

- `Award_Task`: the Task Rewards entry point.
- `Award_Task_Enter:MainMenu_list_task`: recognizes and clicks the 任务 (Tasks) entry on the main screen.
- `Award_Task_Verify:EnterTaskPage`: confirms arrival at the Tasks page.
- `Award_Task_Daily`: the Daily Tasks entry point.
- `Award_Task_Do:DailyTask_ClaimAll`: claims all Daily Task rewards.
- `Award_Task_Weekly`: the Weekly Tasks entry point.
- `Award_Task_Click:WeeklyTask_Into`: enters the Weekly Tasks tab.
- `Award_Task_Verify:WeeklyTab`: confirms that the Weekly Tasks tab is selected.
- `Award_Task_Do:WeeklyTask_ClaimAll`: claims all Weekly Task rewards.
- `Award_Task_Achievement`: the Achievement Tasks entry point.
- `Award_Task_Click:AchievementTask_Into`: enters the Achievement Tasks tab.
- `Award_Task_Verify:AchievementTab`: confirms that the Achievement Tasks tab is selected.
- `Award_Task_Do:AchievementTask_ClaimAll`: claims all Achievement Task rewards.

Maintenance priorities:

- After entering a tab, use a `Verify` node to confirm its selected state.
- When claiming all rewards, both the current tab and `UI_Task_ClaimAll` must be recognized.
- After a subflow finishes, it must be able to return to the main screen or proceed to the next subflow.
