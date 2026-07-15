---
title: Pipeline Conventions
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# Pipeline Conventions

Pipelines are the preferred way to implement automation features in this project. These conventions aim to make workflows readable, debuggable, and reusable while minimizing accidental clicks, false recognition, and infinite loops.

::: tip
For more information, see the [MaaFramework Task Pipeline Protocol](https://maafw.com/docs/3.1-PipelineProtocol).
:::

## Scope and Goals

These conventions apply to all additions or modifications involving pipelines, image resources, task entry points, task switches, and custom code used with pipelines.

When writing a pipeline, prioritize the following:

- Behavior is based on reproducible visual recognition or state checks.
- Node responsibilities are clear, and their purpose can be understood from the name, `desc`, and logs.
- The workflow has an explicit success path, failure fallback, and exit condition.
- Resource placement and naming are stable, making later maintenance and replacement straightforward.
- PR reviewers can determine whether a change is reliable from documentation, screenshots, logs, or validation on a real device.

## Core Principles

### Prefer Pipelines

Any feature should be expressed with a pipeline first. Do not prefer custom merely because it feels more like ordinary code.

Consider custom only in the following cases:

- Complex computation would make pipeline nodes difficult to maintain.
- Runtime data must be read or processed.
- State must be retained across multiple recognition attempts.
- MaaFramework's current built-in actions and recognition methods cannot express the requirement.

### Actions Must Be Based on Visual Recognition

Actions must be performed only after successful visual recognition. Fixed-coordinate operations without recognition conditions are not allowed.

Consider the `StartGame_ClickStart` node in `assets\resource\pipeline\StartGame.json`:

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

This node first performs OCR within `"roi": [450,555,390,40]`, then clicks the OCR result.

::: tip
When Click has no explicit target, it defaults to `true` (the target is the position just recognized by the current node, i.e., the node itself). See the [MaaFramework Task Pipeline Protocol](https://maafw.com/docs/3.1-PipelineProtocol#click) for details.
:::

### Workflows Must Be Able to Exit

Every loop, retry, and optional step should make it possible to explain when execution continues, when it exits, and where it goes after a failure.

### Nodes Must Be Easy to Review

Node names, `desc` values, image paths, and transition relationships should allow maintainers to quickly determine each node's purpose. Do not put multiple stages into one enormous node.

## Node Design

### Node Responsibilities

Business workflows should preferably be divided into several stages:

- `Enter`: enter a screen or entry point.
- `Verify`: confirm the current screen, state, or prerequisite.
- `Click`: click a target that has already been recognized.
- `Do`: perform one business action or a tightly related set of actions.
- `OCR`: perform only OCR checks or text extraction.

### Node Naming

Task-specific nodes must begin with the task name, for example:

- `StartGame_...`
- `Award_...`
- `Award_Task_...`
- `Award_MaintenanceArea_...`

Shared nodes use fixed prefixes:

- `UI_`: pure visual-recognition nodes, such as `UI_Task_ClaimAll`.
- `Status_`: state-detection nodes, such as `Status_In_MainMenu`.
- `SceneDo_`: reusable action nodes, such as `SceneDo_GetItem`.
- `AnySceneEnter_`: any-scene navigation entry points, such as `AnySceneEnter_MainMenu`.

Action-oriented semantics are recommended for task nodes:

- `Task_Enter:Target`: enter a screen or entry point.
- `Task_Verify:State`: confirm a screen or state.
- `Task_Click:Target`: click a recognized target.
- `Task_Do:Action`: perform a business action.
- `Task_OCR:Meaning`: perform only an OCR check.

Put the target or state after the colon so that the node's purpose is immediately visible in debugging logs.

### Writing `desc`

Business nodes should include `desc`. The description should state the node's purpose rather than repeat a field name.

Recommended:

```json
"Award_Task_Do:DailyTask_ClaimAll": {
    "desc": "每日任务-尝试领取全部"
}
```

Not recommended:

```json
"desc": "Click the button"
```

## Recognition and Clicking

### Recommended Pattern

Recognize the target before clicking it:

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

### Acceptable Click Patterns

- After a node recognizes a target, use `action: "Click"` to click the current recognition result.
- Use `box_index` to select one child recognition hit range output by an And node and click it, or use `param.target` to click another UI node that participated in recognition.
- Before clicking in custom code, use a pipeline or screenshot analysis to confirm the current screen and target position.

### Prohibited Click Patterns

- Clicking coordinates directly without `recognition`.
- Relying only on `post_delay` to assume that a screen is ready before clicking.
- Calling `post_click(x, y)` directly in custom code without protection from visual recognition or a state check.

If coordinates are genuinely necessary, explain why in the PR and add sufficient visual-recognition conditions before the coordinate click.

### OCR and State Recognition

OCR and state-recognition nodes should only perform checks or extract information; they should not also handle complex flow control. OCR `expect` values must come from the actual game screen and must not be invented.

Template matching should use stable regions with distinct features. Avoid including large background areas, dynamic numbers, notification dots, countdowns, or other changeable content in template images unless recognizing that state is the node's purpose.

## Flow Control

Some unconventional techniques allow a pipeline to accomplish many things. The following are examples.

### Optional Subtasks

Use `[JumpBack]` together with multiple nodes that each have `max_hit: 1` to implement optional subtasks.

Example: `assets\resource\pipeline\Award.json`

``` json
{
    "AwardMain": {
        "desc": "奖励领取入口",                    // Description
        "next": [
            "[JumpBack]AwardSub_MaintenanceArea", // Use [JumpBack] to return and run this node again after the child node finishes
            "[JumpBack]AwardSub_Task",            // Use [JumpBack] to return and run this node again after the child node finishes
            "AwardEnd"                            // End node
        ]
    },
    "AwardSub_MaintenanceArea": {                 // Nodes use DirectHit by default and match immediately
        "max_hit": 1,                             // "max_hit": 1 allows this node to be entered only once during the current task run
        "next": [
            "Award_MaintenanceArea"               // Specify the subtask entry node in next
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

## File and Resource Organization

### Pipeline Files

Organize pipelines by responsibility:

- `assets/resource/pipeline/<TaskName>.json`: the task's pipeline file.
- `assets/resource/pipeline/<TaskName>/`: the task's subflows.
- `assets/resource/pipeline/Scene/UI/`: shared UI-recognition nodes.
- `assets/resource/pipeline/Scene/Do/`: shared action nodes.
- `assets/resource/pipeline/Scene/Status.json`: shared state nodes.

When adding a task, place its entry point in `assets/resource/pipeline/<TaskName>.json`; put complex subflows in the directory with the same name.

### Image Resources

Place images in `assets/resource/image/`, categorized by screen and function:

- `<TaskName>/`: images required by a task.
- `UI/`: shared UI elements.

Naming requirements:

- A filename should describe the screen, element, and state, for example, `dailytask_selected_withredpoint.png`.
- Use one naming style consistently within a resource group.
- Do not use arbitrary screenshot names, Chinese filenames, date-based filenames, or meaningless numbers.
- Crop template images to stable recognition regions and avoid including large background areas that may change.

After adding an image, reference it in a pipeline with a path relative to the `image` directory, for example, `UI/task/ClaimAll.png`.

## Boundaries for Custom Code

When using custom code, clearly establish that it solves a problem that is difficult to express with a pipeline rather than replacing an ordinary pipeline flow.

Requirements for custom code:

- Visual recognition or a state check must guard every click.
- The basis for key branch decisions should be visible in logs.
- On failure, return to a recoverable state or expose the reason for failure to the upper-level workflow.
- Do not hide extensive screen navigation in custom code, making the actual flow impossible to understand from the pipeline entry point.

If custom code is used with a pipeline, the PR should explain the entry point, recognition conditions, click targets, transition paths, and failure fallbacks.

## PR Self-Check List

Before submitting a PR involving pipelines or resources, verify at least the following:

- Click actions are based on successful visual recognition.
- Fixed-coordinate clicks without recognition conditions have been avoided.
- Node names begin with either the task name or a shared-category prefix.
- Business nodes have a `desc` that explains their purpose.
- New images are in the correct categorized directory, with names that describe the screen and state.
- Template images are cropped to stable recognition regions.
- `next`, `[JumpBack]`, `max_hit`, and similar settings do not cause an infinite loop or premature termination.
- A task switch's `pipeline_override` points to a real node.
- Validation on a real device has been completed, with the device, resolution, starting scene, and result documented.
