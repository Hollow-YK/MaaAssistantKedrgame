---
title: Adding a Feature
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# Adding a Feature

When adding a feature, do not start by writing nodes. First break the requirement down into a verifiable workflow, and then decide which tasks, pipelines, images, and configuration need to be added.

For detailed conventions, see [Pipeline Conventions](/en/dev/project-conventions/pipeline) and [PI Conventions](/en/dev/project-conventions/ProjectInterface). For submission requirements, see [PR Conventions](/en/dev/project-conventions/pull-request).

## 1. Describe the Feature Goal

First, clearly describe in natural language:

- Where the feature starts.
- Which page it needs to enter.
- Which UI elements or text it needs to recognize.
- Which target it needs to click.
- Where it should stop after success.
- Where it should fall back to if it fails or the page does not match expectations.

If this step cannot be explained clearly, the pipeline that follows will usually become a pile of nodes that is difficult to maintain.

## 2. Divide the Workflow into Stages

The following stages are recommended:

1. Entry: which node starts the task.
2. Enter: navigate from a stable scene to the target page.
3. Verify: verify that the target page was actually entered.
4. Execute: perform business actions such as clicking, OCR, claiming, and confirming.
5. Finish: return to the main screen or another stable state.

Each stage should correspond to one or a few nodes with clear responsibilities. Do not put page entry, button clicks, pop-up handling, and returning to the main screen into a single node.

## 3. Prepare the Task Entry

Adding a task usually involves these locations:

- `assets/resource/tasks/<TaskName>.json`: declares the task, tags, entry node, and options.
- `assets/interface.json`: imports the task file so that the UI can discover the task.
- `assets/resource/pipeline/<TaskName>.json`: defines the task entry and main workflow.
- `assets/resource/image/`: stores new template images.

The `entry` in the task file must point to a pipeline node that actually exists.

## 4. Write Recognition Nodes

Before every click, write the recognition conditions. Common approaches include:

- Reuse existing `UI_*` nodes to recognize buttons or entries.
- Reuse `Status_*` nodes to confirm the current scene.
- Use OCR to recognize actual in-game text.
- Use TemplateMatch to recognize stable icons or tab states.

If a new image is required, first check whether a reusable node already exists in [Common Nodes and Universal Transitions](/en/dev/beginner-guide/common-nodes), avoiding duplicate screenshots and duplicate recognition logic.

## 5. Write Actions and Verification

Clicks should be based on successful recognition. After a click, write a `Verify` node whenever possible to confirm that the page actually changed, rather than relying only on `post_delay`.

Recommended node relationship:

```text
Task_Enter:MainMenu_Target
	-> Task_Verify:TargetPage
	-> Task_Do:BusinessAction
	-> Task_End
```

Finish in an explicit state whenever possible. It is recommended that a task return to the home screen when it ends so that the next task can start.

## 6. Validate the Changes

Before submitting, complete at least the following:

- Validate the complete workflow in the actual game.
- Write a thorough PR description.
