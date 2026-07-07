---
title: StartGame 开发流程
---

# StartGame 开发流程

`StartGame` 是适合新手阅读的完整示例。它覆盖启动应用、等待加载、处理资源更新、点击开始、登录提示和主界面确认。

阅读这一页前，建议先看：

- [Pipeline 基础](./pipeline-basics)
- [添加功能](./new-feature)
- [公共节点与万能跳转](./common-nodes)

## 入口关系

入口链路：

```text
assets/resource/tasks/StartGame.json
  entry: StartGameMain

assets/resource/pipeline/StartGame.json
  StartGameMain -> StartGameApp -> StartGame_ClickStart -> StartGame_Scene_Check_Homepage
```

`assets/resource/tasks/StartGame.json` 中的 `entry` 指向 `StartGameMain`。这说明任务启动后会先进入 `StartGameMain`，再由 pipeline 决定后续流程。

## 流程拆分

`StartGame` 可以按开发流程拆成几个阶段：

1. 任务入口：`StartGameMain`
2. 启动应用：`StartGameApp`
3. 可选处理：图标、资源更新、加载等待
4. 点击开始：`StartGame_ClickStart`
5. 登录提示：`StartGame_Login`
6. 主界面确认：`StartGame_Scene_Check_Homepage`

这样的拆分符合 [Pipeline 规范](../project-conventions/pipeline) 中“进入、确认、执行、收尾”的思路。

## 关键节点说明

- `StartGameMain`：任务入口，只负责进入 `StartGameApp`。
- `StartGameApp`：用 `StartApp` 启动游戏，然后依次尝试更新、等待和点击开始。
- `GameResources_update_OCR`：用 OCR 判断是否出现资源更新弹窗。
- `GameResources_update_confirm`：识别“确定”后点击。
- `StartGame_ClickStart`：识别“点击任意处开始”后点击。
- `StartGame_Login`：识别验证码登录后弹出提示，让用户手动登录。
- `StartGame_Scene_Check_Homepage`：通过 `Status_In_MainMenu` 判断是否到达主界面。

## 可选步骤与 JumpBack

`StartGameApp` 中大量使用 `[JumpBack]`。这些节点是“能处理就处理，处理不了就回到原流程继续”的可选步骤。

例如没有资源更新时，`[JumpBack]GameResources_update_OCR` 失败不会让整个任务停止，而是继续尝试后续节点。

这类写法适合启动流程，因为启动时可能遇到更新、加载、等待等不同状态。但每个可选步骤都要有明确职责，不能把无关处理都塞进同一个节点。

## 识别后再点击

`StartGame_ClickStart` 不直接点击固定坐标，而是先 OCR 识别“点击任意处开始”：

```text
StartGame_ClickStart
  recognition: OCR "点击任意处开始"
  action: Click
```

这是“点击必须基于视觉识别”的基本示例。维护时不要把它改成无识别条件的固定坐标点击。

## 登录处理

`StartGame_Login` 只识别验证码登录并提示用户手动处理，不尝试绕过验证码或自动处理敏感登录流程。

这类节点的职责是把状态告诉用户，让流程停在可理解的位置。

## 主界面确认

流程最后通过 `Status_In_MainMenu` 判断是否到达主界面。这个状态节点会同时识别多个主界面元素，比只识别单个按钮更稳定。

如果你在新功能里也需要从主界面开始，优先复用 `Status_In_MainMenu` 或 `AnySceneEnter_MainMenu`，不要重新写一套主界面判断。

## 维护重点

- 启动流程中的 OCR 文案可能随游戏版本变化，需要根据实机画面维护 `expected` 候选。
- 登录节点只提示用户，不应尝试绕过验证码。
- 点击开始必须基于 OCR 识别，不要改成固定坐标点击。
- 修改启动流程后，需要至少验证冷启动、已有登录状态和需要更新资源的场景。
