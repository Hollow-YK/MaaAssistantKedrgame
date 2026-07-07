---
title: 领取奖励
---

# 领取奖励

任务入口：`Award`

任务文件：`assets/resource/tasks/Award.json`

Pipeline 入口文件：`assets/resource/pipeline/Award.json`

子流程目录：`assets/resource/pipeline/Award/`

入口节点：`AwardMain`

当前包含两个子功能：

- `Award_MaintenanceArea`：资源派遣奖励。
- `Award_Task`：每日、每周、成就任务奖励。

`AwardMain` 使用 `[JumpBack]` 串联子功能，`AwardSub_MaintenanceArea` 和 `AwardSub_Task` 使用 `max_hit: 1` 限制每个子流程只进入一次。

## 资源派遣奖励

文件：`assets/resource/pipeline/Award/MaintenanceArea.json`

主要节点：

- `Award_MaintenanceArea`：资源派遣奖励入口。
- `Award_MaintenanceArea_Enter:MainMenu_list_maintenancearea`：识别主界面资源派遣入口并点击。
- `Award_MaintenanceArea_Click:GetAll`：识别“一键领取”并点击。
- `Award_MaintenanceArea_Click:Again`：根据选项确认再次派遣。
- `Award_MaintenanceArea_Click:NotAgain`：根据选项关闭再次派遣弹窗。
- `Award_MaintenanceArea_Click:Close`：关闭资源派遣页面。
- `Award_MaintenanceArea_OCR:Alert_Again`：识别再次派遣弹窗文案。

相关选项在 `assets/resource/tasks/Award.json` 中配置，通过 `pipeline_override` 控制 `Again` 或 `NotAgain` 节点启用状态。

## 任务奖励

文件：`assets/resource/pipeline/Award/Task.json`

主要节点：

- `Award_Task`：任务奖励入口。
- `Award_Task_Enter:MainMenu_list_task`：识别主界面任务入口并点击。
- `Award_Task_Verify:EnterTaskPage`：确认进入任务页。
- `Award_Task_Daily`：每日任务入口。
- `Award_Task_Do:DailyTask_ClaimAll`：每日任务领取全部。
- `Award_Task_Weekly`：每周任务入口。
- `Award_Task_Click:WeeklyTask_Into`：进入每周任务标签。
- `Award_Task_Verify:WeeklyTab`：确认每周任务标签选中。
- `Award_Task_Do:WeeklyTask_ClaimAll`：每周任务领取全部。
- `Award_Task_Achievement`：成就任务入口。
- `Award_Task_Click:AchievementTask_Into`：进入成就任务标签。
- `Award_Task_Verify:AchievementTab`：确认成就任务标签选中。
- `Award_Task_Do:AchievementTask_ClaimAll`：成就任务领取全部。

维护重点：

- 进入标签页后必须用 `Verify` 节点确认选中状态。
- 领取全部时必须同时识别当前标签和 `UI_Task_ClaimAll`。
- 子流程结束后应能回到主界面或进入下一个子流程。
