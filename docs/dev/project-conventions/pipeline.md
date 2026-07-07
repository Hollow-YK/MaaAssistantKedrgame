---
title: Pipeline 规范
---

# Pipeline 规范

Pipeline 是本项目实现自动化功能的首选方式。规范的目标是让流程可读、可调试、可复用，并尽量减少误点、误判和死循环。

::: tip
更多内容可参考 [MaaFramework 任务流水线（Pipeline）协议](https://maafw.com/docs/3.1-PipelineProtocol)
:::

## 适用范围与目标

本规范适用于所有新增或修改 pipeline、图片资源、任务入口、任务开关以及与 pipeline 配合的 custom 代码。

编写 pipeline 时，应优先保证：

- 行为建立在可复现的视觉识别或状态判断上。
- 节点职责清楚，能从名称、`desc` 和日志中理解用途。
- 流程有明确的成功路径、失败退路和退出条件。
- 资源文件放置和命名稳定，便于后续维护和替换。
- PR 审核者能根据文档、截图、日志或实机验证结果判断改动是否可靠。

## 核心原则

### 优先使用 pipeline

实现任何功能都应该优先用 Pipeline 表达。不要因为 custom 写起来更像普通代码就优先使用 custom。

只有这些情况才考虑 custom：

- 需要复杂计算，pipeline 节点会变得难以维护。
- 需要读取或处理运行时数据。
- 需要跨多次识别保存状态。
- MaaFramework 当前内置动作和识别无法表达需求。

### 动作必须基于视觉识别

动作必须建立在视觉识别成功的基础上。不允许写没有识别条件的固定坐标操作。

以 `assets\resource\pipeline\StartGame.json` 的 `StartGame_ClickStart` 节点为例：

``` json
    "StartGame_ClickStart": {
        "pre_wait_freezes": 500,
        "recognition": {
            "type": "OCR",
            "param": {
                "expected": [
                    "点击任意处开始"
                ],
                "roi": [
                    450,
                    555,
                    390,
                    40
                ]
            }
        },
        "action": {
            "type": "Click"
        },
        "next": [
            "[JumpBack]StartGame_ClickStart_again",
            "StartGame_Login",
            "[JumpBack]StartGame_Login_wait",
            "StartGame_Scene_Check_Homepage"
        ]
    }
```

该节点先进行一次 `"roi": [450,555,390,40]` 的 OCR ，之后 Click 刚才 OCR 的结果。

::: tip
Click 在没有显式指定 target 时，默认为 `true`（目标为本节点中刚刚识别到的位置（即自身）。详见 [MaaFramework 任务流水线协议](https://maafw.com/docs/3.1-PipelineProtocol#click)
:::

### 流程必须能退出

任何循环、重试和可选步骤都应该能解释：什么时候继续、什么时候退出、失败后去哪里。

### 节点必须便于审核

节点命名、`desc`、图片路径和跳转关系应能让维护者快速判断节点用途。不要把多个阶段塞进一个巨大节点里。

## 节点设计

### 节点职责

业务流程推荐优先拆成几个阶段：

- `Enter`：进入某个页面或入口。
- `Verify`：确认当前页面、状态或前置条件。
- `Click`：点击已经识别到的目标。
- `Do`：执行一个业务动作或一组强相关动作。
- `OCR`：只负责 OCR 判断或文本提取。

### 节点命名

任务专属节点必须以任务名开头，例如：

- `StartGame_...`
- `Award_...`
- `Award_Task_...`
- `Award_MaintenanceArea_...`

通用节点使用固定前缀：

- `UI_`：纯视觉识别节点，例如 `UI_Task_ClaimAll`。
- `Status_`：状态判断节点，例如 `Status_In_MainMenu`。
- `SceneDo_`：可复用动作节点，例如 `SceneDo_GetItem`。
- `AnySceneEnter_`：万能跳转入口，例如 `AnySceneEnter_MainMenu`。

推荐在任务节点中使用动作语义：

- `Task_Enter:Target`：进入某个页面或入口。
- `Task_Verify:State`：确认页面或状态。
- `Task_Click:Target`：点击某个已识别目标。
- `Task_Do:Action`：执行某个业务动作。
- `Task_OCR:Meaning`：只负责 OCR 判断。

冒号后面写目标或状态，便于调试日志中快速看出节点用途。

### desc 编写

业务节点应写 `desc`。描述要说明节点目的，而不是重复字段名。

推荐：

```json
"Award_Task_Do:DailyTask_ClaimAll": {
    "desc": "每日任务-尝试领取全部"
}
```

不推荐：

```json
"desc": "点击按钮"
```

## 识别与点击

### 推荐写法

识别目标后再点击目标：

```json
    "Award_Task_Do:DailyTask_ClaimAll": {
        "desc": "每日任务-尝试领取全部",
        "recognition": "And",
        "all_of": [
            "UI_Task_DailyTask_selected",
            "UI_Task_ClaimAll"
        ],
        "box_index": 1,
        "action": {
            "type": "Click"
        },
        "next": [
            "[JumpBack]SceneDo_GetItem",
            "Award_Task_Weekly",
            "Award_Task_Achievement",
            "AnySceneEnter_MainMenu"
        ],
        "post_delay": 2000
    },
```

### 可以接受的点击形式

- 节点自身识别到目标后，使用 `action: "Click"` 点击当前识别结果。
- 使用 `box_index` 指定 And 节点输出自身的某个子识别命中范围并点击自身，或使用 `param.target` 点击另一个已经参与识别的 UI 节点。
- 在 custom 中点击前，先通过 pipeline 或截图分析确认当前界面和目标位置。

### 不允许的点击形式

- 没有 `recognition` 就直接点击坐标。
- 只靠 `post_delay` 猜测页面已经到位后点击。
- custom 中直接 `post_click(x, y)`，但没有任何视觉识别或状态判断保护。

如果确实必须使用坐标，需要在 PR 中说明原因，并在坐标点击前增加足够的视觉识别条件。

### OCR 与状态识别

OCR 和状态识别节点应只负责判断或提取信息，不要同时承担复杂流程控制。OCR 的 `expect` 应来自实际游戏画面，不应凭空编写。

模板匹配应使用稳定、特征明确的区域。避免把大面积背景、动态数字、红点、倒计时等容易变化的内容放进模板图，除非节点目的就是识别这些状态。

## 流程控制

有一些奇妙的方法可以让 Pipeline做到许多事情。下面是一些例子：

### 可选子任务

通过利用 `[JumpBack]` 配合多个 `max_hit: 1` 的节点实现可选子任务

示例：`assets\resource\pipeline\Award.json`

``` json
{
    "AwardMain": {
        "desc": "奖励领取入口",                    // 描述
        "next": [
            "[JumpBack]AwardSub_MaintenanceArea", // 通过 [JumpBack] 使节点执行完毕后返回并再次执行该节点
            "[JumpBack]AwardSub_Task",            // 通过 [JumpBack] 使节点执行完毕后返回并再次执行该节点
            "AwardEnd"                            // 结束节点
        ]
    },
    "AwardSub_MaintenanceArea": {                 // 节点默认为 DirectHit ，直接命中
        "max_hit": 1,                             // 通过 "max_hit": 1 实现在本次执行任务时只会进入一次本节点
        "next": [
            "Award_MaintenanceArea"               // next 内填写子任务入口节点
        ]
    },
    "AwardSub_Task": {
        "max_hit": 1,
        "next": [
            "Award_Task"
        ]
    },
    "AwardEnd": {}
}
```

## 文件与资源组织

### Pipeline 文件

推荐按职责放置 pipeline：

- `assets/resource/pipeline/<TaskName>.json`：任务 Pipeline 文件。
- `assets/resource/pipeline/<TaskName>/`：任务的子流程。
- `assets/resource/pipeline/Scene/UI/`：通用 UI 识别节点。
- `assets/resource/pipeline/Scene/Do/`：通用动作节点。
- `assets/resource/pipeline/Scene/Status.json`：通用状态节点。

新增任务时，任务入口放在 `assets/resource/pipeline/<TaskName>.json`，复杂子流程再放到同名目录下。

### 图片资源

图片放在 `assets/resource/image/`，按界面和功能分类：

- `<TaskName>/`：任务所需图片。
- `UI/`：通用 UI 元素

命名要求：

- 文件名表达界面、元素和状态，例如 `dailytask_selected_withredpoint.png`。
- 同一组资源使用同一命名风格。
- 不使用随手截图名、中文文件名、日期文件名或无意义编号。
- 模板图片应裁剪到稳定识别区域，避免包含会变化的大面积背景。

新增图片后，在 pipeline 中使用相对 `image` 目录的路径，例如 `UI/task/ClaimAll.png`。

## Custom 使用边界

使用 custom 时，必须明确它解决的是 pipeline 难以表达的问题，而不是替代普通 pipeline 流程。

custom 中需要注意：

- 点击前必须有视觉识别或状态判断保护。
- 关键分支应能从日志中看出判断依据。
- 失败时应返回可恢复状态，或把失败原因暴露给上层流程。
- 不要在 custom 中隐藏大量页面跳转，导致 pipeline 入口看不出真实流程。

如果 custom 与 pipeline 配合使用，PR 中应说明入口、识别条件、点击目标、跳转路径和失败退路。

## PR 自查清单

提交涉及 pipeline 或资源的 PR 前，至少检查：

- 点击动作是否建立在视觉识别成功的基础上。
- 是否避免了无识别条件的固定坐标点击。
- 节点命名是否以任务名或通用分类前缀开头。
- 业务节点是否写了能说明目的的 `desc`。
- 新图片是否放在正确分类目录，命名能表达界面和状态。
- 模板图片是否裁剪到稳定识别区域。
- `next`、`[JumpBack]`、`max_hit` 等是否会导致无限循环或提前结束。
- 任务开关的 `pipeline_override` 是否指向真实节点。
- 是否完成实机验证，并能说明设备、分辨率、起始场景和结果。
