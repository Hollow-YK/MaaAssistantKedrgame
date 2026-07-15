---
title: Start Game (开始游戏)
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# Start Game (开始游戏)

Task entry: `StartGame`

Task file: `assets/resource/tasks/StartGame.json`

Pipeline file: `assets/resource/pipeline/StartGame.json`

Entry node: `StartGameMain`

## Main Nodes

- `StartGameMain`: the 开始游戏 (Start Game) task entry point.
- `StartGameApp`: launches the package `com.phxh.official.nld`.
- `StartGame_icon`: recognizes the game icon or launch-related templates.
- `GameResources_update_OCR`: recognizes the resource-update pop-up.
- `GameResources_update_confirm`: clicks to confirm the resource update.
- `GameResources_update_wait`: waits for the update package to download.
- `StartGame_wait`: waits for startup text such as initialization and server-version messages.
- `StartGame_ClickStart`: recognizes and clicks “点击任意处开始” (Tap Anywhere to Start).
- `StartGame_Login`: recognizes verification-code login and prompts the user to handle it manually.
- `StartGame_Login_wait`: recognizes the loading image.
- `StartGame_Scene_Check_Homepage`: confirms arrival at the main screen.

## Maintenance Priorities

- OCR text in the startup flow may change between game versions, so retain multiple `expected` candidates.
- The login node should only notify the user; it must not attempt to bypass the verification code.
- Clicking to start must be based on OCR recognition. Do not replace it with a fixed-coordinate click.
