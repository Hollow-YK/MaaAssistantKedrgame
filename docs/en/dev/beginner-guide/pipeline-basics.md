---
title: Pipeline Basics
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# Pipeline Basics

A pipeline consists of a set of nodes. Each node describes "when to execute, what to execute, and where to go afterward."

::: tip
For more information, see the [MaaFramework Task Pipeline Protocol](https://maafw.com/docs/3.1-PipelineProtocol).
:::

When you first start reading pipelines, remember these three core components:

1. Determine whether the current screen matches expectations; this is `recognition`.
2. Perform an action after successful recognition; this is `action`.
3. Decide where to go next; this is `next`.

A minimal clickable node looks roughly like this:

```json
{
    "recognition": {
        "type": "OCR",
        "param": {
            "expected": ["确定"],
            "roi": [425, 468, 190, 35]
        }
    },
    "action": "Click"
}
```

This means that the recognized position is clicked only when the actual UI text “确定” (“Confirm”) is recognized in the specified region. Do not write a click first and then hope it clicks the right place. First prove what is on the screen, and then decide where to click.

For the complete rules, see [Pipeline Conventions](/en/dev/project-conventions/pipeline).

## What Is a Node?

A node is the smallest execution unit in a pipeline. A node can be responsible only for checking a state, or it can perform a click, launch an application, or transition to subsequent nodes after successful recognition.

A node name should indicate which task it belongs to, what action it performs, and what target it addresses. For example:

- `StartGame_ClickStart`: clicks start in the start-game workflow.
- `Award_Task_Verify:EnterTaskPage`: confirms entry into the task page in the reward task.
- `Status_In_MainMenu`: determines whether the current screen is the main screen.

## Common Fields

- `desc`: node description for logs and maintenance.
- `recognition`: recognition method, which can be OCR, TemplateMatch, And, Or, or a reference to another recognition node.
- `action`: action performed after successful recognition, such as Click or StartApp.
- `next`: list of subsequent nodes.
- `post_delay`: wait time after an action.
- `max_hit`: limits how many times a node can be hit; commonly used to prevent a sub-process from executing repeatedly.

Not every node must have every field. For example, state nodes usually contain only `recognition`, while entry nodes may contain only `next`.

## Recognition Methods

Common recognition methods include:

- OCR: recognizes text and is suitable for button labels, prompt text, and state text.
- TemplateMatch: recognizes image templates and is suitable for icons, buttons, and tab states.
- And: requires multiple conditions to be satisfied simultaneously.
- Or: requires any one of multiple conditions to be satisfied.
- References to other nodes: reuse common recognition nodes such as `UI_*` and `Status_*`.

When writing recognition logic, choose stable regions whenever possible. OCR text and ROIs should come from actual in-game screens; template images should be cropped to stable recognition regions.

## Actions and Transitions

An `action` should only execute after successful recognition. Click actions require particular care: the click target must come from the recognition result of the current node or from a UI node that participated in recognition.

`next` specifies the subsequent workflow. When reading `next`, confirm two things:

- Which node the workflow continues to after success.
- Whether it can return to a stable state after failure or completion.

`[JumpBack]` is commonly used for optional steps that mean "handle it if possible; otherwise, return and continue the current workflow."

## Order for Reading a Node

When examining a node, read it in this order:

1. First inspect the node name to determine which task or common category it belongs to.
2. Then inspect `desc` to confirm the node's purpose.
3. Inspect `recognition` to confirm which visual conditions it depends on.
4. Inspect `action` to confirm what happens after successful recognition.
5. Inspect `next` to confirm the success, failure, or cleanup path.

If a node's purpose is unclear, prioritize improving its `desc`, splitting the node, or adjusting its name instead of continuing to pack more recognition logic and actions into it.
