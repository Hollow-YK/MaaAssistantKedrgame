---
title: 开始游戏
---

# 开始游戏

任务入口：`StartGame`

任务文件：`assets/resource/tasks/StartGame.json`

Pipeline 文件：`assets/resource/pipeline/StartGame.json`

入口节点：`StartGameMain`

## 主要节点

- `StartGameMain`：开始游戏任务入口。
- `StartGameApp`：启动包名 `com.phxh.official.nld`。
- `StartGame_icon`：识别游戏图标或启动相关模板。
- `GameResources_update_OCR`：识别资源更新弹窗。
- `GameResources_update_confirm`：点击资源更新确认。
- `GameResources_update_wait`：等待更新包下载。
- `StartGame_wait`：等待初始化、服务器版本等启动文本。
- `StartGame_ClickStart`：识别“点击任意处开始”并点击。
- `StartGame_Login`：识别验证码登录并提示用户手动处理。
- `StartGame_Login_wait`：识别加载图。
- `StartGame_Scene_Check_Homepage`：确认进入主界面。

## 维护重点

- 启动流程中的 OCR 文案可能随游戏版本变化，需要保留多个 `expected` 候选。
- 登录节点只提示用户，不应尝试绕过验证码。
- 点击开始必须基于 OCR 识别，不要改成固定坐标点击。
