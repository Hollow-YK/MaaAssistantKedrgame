---
title: 公共节点与万能跳转
---

# 公共节点与万能跳转

公共节点是多个任务都能复用的识别、状态和动作。新增功能前，先查找是否已有公共节点可用。

更完整的节点说明见 [任务与节点](../tasks-and-nodes/)；命名和复用要求见 [Pipeline 规范](../project-conventions/pipeline)。

## 公共节点分类

公共节点主要放在 `assets/resource/pipeline/Scene/` 下：

- `Scene/UI/`：通用 UI 识别节点，例如主界面入口、任务页标签、返回按钮、弹窗按钮。
- `Scene/Status.json`：通用状态节点，例如是否处于主界面、是否处于加载界面，一般用于确保执行动作前处于正确的位置。
- `Scene/Do/`：通用动作节点，例如点击 HOME、关闭获得物品界面、安全关闭弹窗。

常见命名前缀：

- `UI_*`：只负责识别界面元素。
- `Status_*`：只负责判断场景状态。
- `SceneDo_*`：执行可复用动作。
- `AnySceneEnter_*`：从多个可能场景回到稳定场景。

## 使用 UI 节点

如果要点击主界面的任务入口，不要重新截图一个任务入口按钮。应优先复用已有节点，例如 `UI_MainMenu_list_task`。

推荐使用先确认所处界面，再使用  `box_index` 指定 And 节点输出自身的某个子识别命中范围以指定目标的方式：

```json
{
    "recognition": "And",
    "all_of": [
        "Status_In_MainMenu",                   // 确保处于主界面
        "UI_MainMenu_list_task"                 // 识别要点击的按钮
    ],
    "box_index": 1,
    "action": "Click",                          // 进行点击。target 默认为true，即上面通过box_index指定的"UI_MainMenu_list_task"
}
```

或者使用先确认所处界面，再使用 `param.target` 指定目标的方式（不推荐）：

> 可能出现某节点虽然作为 And 的子识别被执行并命中了，但它不是一个已经完成的前置 pipeline 节点，所以动作系统按 target 名称查不到它的 rect，于是还没真正发出点击，动作就失败了的情况。

```json
{
    "recognition": "And",
    "all_of": [
        "Status_In_MainMenu",                   // 确保处于主界面
        "UI_MainMenu_list_task"                 // 识别要点击的按钮
    ],
    "action": {
        "type": "Click",
        "param": {
            "target": "UI_MainMenu_list_task"   // 点击对应按钮
        }
    }
}
```

如果要点击的是仅在某一页面才可能出现的元素，也可以使用先识别 UI 再点击识别结果的方法（不推荐）：

```json
{
    "recognition": "And",
    "all_of": [
        "UI_MainMenu_list_task"                 // 识别要点击的按钮
    ],
    "action": "Click",                          // 点击对应按钮
}
```

## 使用状态节点

状态节点用于确认当前环境，不直接执行业务动作。

例如 `Status_In_MainMenu` 会通过多个主界面元素共同判断是否处于主界面。业务流程进入某个页面前，可以先确认主界面状态，再点击对应入口。

不要把状态判断写成固定等待。能识别状态时，优先识别状态。

## 使用动作节点

`SceneDo_*` 节点适合处理多个任务都会遇到的动作，例如：

- `SceneDo_PauseHomeButton`：识别 HOME 按钮并点击。
- `SceneDo_GetItem`：识别获得物品界面并点击关闭。
- `SceneDo_Alert_Close_safe`：只关闭已确认安全的弹窗。

这些节点一般是服务于万能跳转的。

新增通用动作前，要确认它是否真的能被多个任务复用。只服务某个任务的动作，应放在任务自己的命名空间下。

## 使用万能跳转

万能跳转入口是 `AnySceneEnter_MainMenu`，位置在 `assets/resource/pipeline/Scene/Do/Mainmenu.json`。

它会依次尝试：

1. `[JumpBack]SceneDo_PauseHomeButton`
2. `[JumpBack]SceneDo_GetItem`
3. `[JumpBack]Status_Loading_Screen`
4. `[JumpBack]SceneDo_Alert_Close_safe`
5. `[JumpBack]StartGame_wait`
6. `[JumpBack]StartGame_ClickStart`
7. `Status_In_MainMenu`

适合使用万能跳转的情况：

- 功能入口之后，用于确保处于某个界面开始。
- 功能完成后需要回到主界面。
- 失败时可能停在获得物品、加载、弹窗等中间状态。
- 当前流程需要一个稳定收尾节点。

不适合使用万能跳转的情况：

- 你其实知道当前页面，应写明确的 `Verify` 节点。
- 点击后没有确认页面变化，只想靠万能跳转兜底。
- 某个弹窗是业务流程的一部分，需要任务自己处理。

万能跳转是收尾和兜底工具，不是替代页面确认的工具。
