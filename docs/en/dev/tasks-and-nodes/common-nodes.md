---
title: Shared Nodes
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# Shared Nodes

Shared nodes are recognition, state, and action nodes that can be reused by multiple tasks. Before adding a business-specific node, first check whether a suitable shared node already exists.

Common categories:

- `assets/resource/pipeline/Scene/UI/`: nodes for recognizing UI elements.
- `assets/resource/pipeline/Scene/Status.json`: state-detection nodes that use `And` to recognize multiple UI elements and determine the current state.
- `assets/resource/pipeline/Scene/Do/`: shared action nodes. This directory is generally used for any-scene navigation and similar operations.

## Shared UI Nodes

Shared UI nodes are located in `assets/resource/pipeline/Scene/UI/`.

They are generally named according to the screen where they appear:

- `UI_MainMenu_*`: main-screen entries such as 任务 (Tasks), 资源派遣 (Resource Dispatch), 邮件 (Mail), and 商店 (Shop).
- `UI_Task_*`: task-page tabs, selected states, and claim buttons.
- `UI_Common_*`: common elements such as 返回 (Back), 主页 (Home), pop-ups, 确认 (Confirm), 关闭 (Close), and 获得物品 (Items Obtained).

Do not repeatedly add new templates and recognition nodes for the same button.

## Shared State Nodes

File: `assets/resource/pipeline/Scene/Status.json`

Current states:

- `Status_In_MainMenu`: the main screen.
- `Status_Loading_Screen`: the loading screen.
- `Status_In_Combat`: the 出击 (Combat) screen.
- `Status_In_Stage`: inside a battle stage.

State nodes only perform checks; they do not directly execute business actions. A business workflow should use a state node to confirm the current environment before proceeding.

## Shared Action Nodes

Shared action nodes are located in `assets/resource/pipeline/Scene/Do/`.

Commonly used nodes include:

- `SceneDo_PauseHomeButton`: recognizes and clicks the `HOME` button.
- `SceneDo_GetItem`: recognizes the 获得物品 (Items Obtained) screen and clicks to close it.
- `SceneDo_Alert_Close_safe`: closes only pop-ups that have been exhaustively verified as safe.
- `SceneDo_Alert_Close`: closes an ordinary pop-up.
- `SceneDo_Alert_Confirm`: confirms an ordinary pop-up.

Before adding a shared action, verify that it is genuinely reusable. An action that serves only one task should be placed under that task's namespace.
