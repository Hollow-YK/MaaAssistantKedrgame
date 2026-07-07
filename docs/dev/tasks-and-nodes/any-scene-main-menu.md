---
title: 万能跳转
---

# 万能跳转

万能跳转入口：`AnySceneEnter_MainMenu`

文件位置：`assets/resource/pipeline/Scene/Do/Mainmenu.json`

作用：尽量从任意场景回到主界面。

## 当前流程

`AnySceneEnter_MainMenu` 会依次尝试：

1. `[JumpBack]SceneDo_PauseHomeButton`：识别 HOME 按钮并点击。
2. `[JumpBack]SceneDo_GetItem`：识别获得物品界面并点击关闭。
3. `[JumpBack]Status_Loading_Screen`：识别加载界面。
4. `[JumpBack]SceneDo_Alert_Close_safe`：安全关闭可关闭弹窗。
5. `[JumpBack]StartGame_wait`：处理启动等待文本。
6. `[JumpBack]StartGame_ClickStart`：处理点击开始。
7. `Status_In_MainMenu`：确认已在主界面。

## 使用建议

- 适合作为功能失败或完成后的兜底回主界面节点。
- 不适合替代明确的页面确认。能写 `Verify` 节点时，优先写明确确认。
- 新增会频繁遇到的弹窗时，应先补充安全关闭规则，而不是让业务节点到处处理同一个弹窗。
