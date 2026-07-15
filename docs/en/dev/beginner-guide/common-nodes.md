---
title: Common Nodes and Universal Transitions
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# Common Nodes and Universal Transitions

Common nodes are recognition, state, and action nodes that can be reused by multiple tasks. Before adding a feature, first search for an existing common node that can be used.

For more complete node documentation, see [Tasks and Nodes](/en/dev/tasks-and-nodes/). For naming and reuse requirements, see [Pipeline Conventions](/en/dev/project-conventions/pipeline).

## Common Node Categories

Common nodes are mainly stored under `assets/resource/pipeline/Scene/`:

- `Scene/UI/`: common UI recognition nodes, such as main-screen entries, task-page tabs, back buttons, and pop-up buttons.
- `Scene/Status.json`: common state nodes, such as whether the current screen is the main screen or a loading screen. These are generally used to ensure that the workflow is in the correct place before performing an action.
- `Scene/Do/`: common action nodes, such as clicking HOME, closing the obtained-items screen, and safely closing pop-ups.

Common naming prefixes:

- `UI_*`: only recognizes UI elements.
- `Status_*`: only determines the scene state.
- `SceneDo_*`: performs reusable actions.
- `AnySceneEnter_*`: returns from multiple possible scenes to a stable scene.

## Using UI Nodes

If you need to click the task entry on the main screen, do not take another screenshot of a task-entry button. Prefer reusing an existing node such as `UI_MainMenu_list_task`.

The recommended approach is to confirm the current screen first, then use `box_index` to select the hit range of one of the And node's own child recognition results as the target:

```json
{
    "recognition": "And",
    "all_of": [
        "Status_In_MainMenu",                   // Ensure that the main screen is open
        "UI_MainMenu_list_task"                 // Recognize the button to click
    ],
    "box_index": 1,
    "action": "Click",                          // Click it. target defaults to true: the UI_MainMenu_list_task result selected by box_index above
}
```

Alternatively, confirm the current screen first and then use `param.target` to specify the target (not recommended):

> A node may execute and match as a child recognition of And, but it is not a completed prerequisite pipeline node. As a result, the action system cannot find its rect by the target name, and the action fails before a click is actually issued.

```json
{
    "recognition": "And",
    "all_of": [
        "Status_In_MainMenu",                   // Ensure that the main screen is open
        "UI_MainMenu_list_task"                 // Recognize the button to click
    ],
    "action": {
        "type": "Click",
        "param": {
            "target": "UI_MainMenu_list_task"   // Click the corresponding button
        }
    }
}
```

If the element to click can appear only on a particular page, you can also recognize the UI first and then click the recognition result (not recommended):

```json
{
    "recognition": "And",
    "all_of": [
        "UI_MainMenu_list_task"                 // Recognize the button to click
    ],
    "action": "Click",                          // Click the corresponding button
}
```

## Using State Nodes

State nodes confirm the current environment and do not directly perform business actions.

For example, `Status_In_MainMenu` determines whether the current screen is the main screen by checking multiple main-screen elements together. Before a business workflow enters a page, it can confirm the main-screen state and then click the corresponding entry.

Do not implement a state check as a fixed wait. When a state can be recognized, prefer state recognition.

## Using Action Nodes

`SceneDo_*` nodes are suitable for actions encountered by multiple tasks, such as:

- `SceneDo_PauseHomeButton`: recognizes and clicks the HOME button.
- `SceneDo_GetItem`: recognizes and closes the obtained-items screen.
- `SceneDo_Alert_Close_safe`: closes only pop-ups that have been confirmed safe.

These nodes generally support universal transitions.

Before adding a common action, confirm that multiple tasks can actually reuse it. An action that serves only one task should remain in that task's own namespace.

## Using Universal Transitions

The universal transition entry is `AnySceneEnter_MainMenu`, located in `assets/resource/pipeline/Scene/Do/Mainmenu.json`.

It tries the following in order:

1. `[JumpBack]SceneDo_PauseHomeButton`
2. `[JumpBack]SceneDo_GetItem`
3. `[JumpBack]Status_Loading_Screen`
4. `[JumpBack]SceneDo_Alert_Close_safe`
5. `[JumpBack]StartGame_wait`
6. `[JumpBack]StartGame_ClickStart`
7. `Status_In_MainMenu`

Universal transitions are suitable in these situations:

- After a feature entry, to ensure that the workflow starts from a particular screen.
- When a feature needs to return to the main screen after completion.
- When failure may leave the workflow in an intermediate state such as an obtained-items screen, loading screen, or pop-up.
- When the current workflow needs a stable final node.

Universal transitions are not suitable in these situations:

- You already know the current page and should write an explicit `Verify` node.
- You did not confirm that the page changed after clicking and only want a universal transition as a fallback.
- A pop-up is part of the business workflow and must be handled by the task itself.

A universal transition is a cleanup and fallback tool, not a substitute for page verification.
