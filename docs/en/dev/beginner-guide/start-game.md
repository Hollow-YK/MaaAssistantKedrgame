---
title: StartGame Development Workflow
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# StartGame Development Workflow

`StartGame` is a complete example suitable for beginners. It covers launching the application, waiting for loading, handling resource updates, clicking start, handling login prompts, and confirming the main screen.

Before reading this page, it is recommended that you first read:

- [Pipeline Basics](/en/dev/beginner-guide/pipeline-basics)
- [Adding a Feature](/en/dev/beginner-guide/new-feature)
- [Common Nodes and Universal Transitions](/en/dev/beginner-guide/common-nodes)

## Entry Relationship

Entry chain:

```text
assets/resource/tasks/StartGame.json
  entry: StartGameMain

assets/resource/pipeline/StartGame.json
  StartGameMain -> StartGameApp -> StartGame_ClickStart -> StartGame_Scene_Check_Homepage
```

The `entry` in `assets/resource/tasks/StartGame.json` points to `StartGameMain`. This means that after the task starts, it first enters `StartGameMain`, and the pipeline then determines the subsequent workflow.

## Workflow Breakdown

`StartGame` can be divided into several stages according to the development workflow:

1. Task entry: `StartGameMain`
2. Launch application: `StartGameApp`
3. Optional handling: icons, resource updates, and loading waits
4. Click start: `StartGame_ClickStart`
5. Login prompt: `StartGame_Login`
6. Main-screen confirmation: `StartGame_Scene_Check_Homepage`

This breakdown follows the approach of "enter, verify, execute, and finish" in the [Pipeline Conventions](/en/dev/project-conventions/pipeline).

## Key Nodes

- `StartGameMain`: task entry; it is responsible only for entering `StartGameApp`.
- `StartGameApp`: launches the game with `StartApp`, then tries updates, waits, and clicking start in sequence.
- `GameResources_update_OCR`: uses OCR to determine whether the resource-update pop-up appears.
- `GameResources_update_confirm`: recognizes “确定” (“Confirm”) and then clicks it.
- `StartGame_ClickStart`: recognizes “点击任意处开始” (“Tap Anywhere to Start”) and then clicks it.
- `StartGame_Login`: recognizes verification-code login and displays a prompt asking the user to sign in manually.
- `StartGame_Scene_Check_Homepage`: uses `Status_In_MainMenu` to determine whether the main screen has been reached.

## Optional Steps and JumpBack

`StartGameApp` makes extensive use of `[JumpBack]`. These nodes are optional steps that mean "handle it if possible; otherwise, return and continue the original workflow."

For example, if there is no resource update, failure of `[JumpBack]GameResources_update_OCR` does not stop the entire task. Instead, the workflow continues trying subsequent nodes.

This pattern is suitable for the startup workflow because startup can encounter different states such as updates, loading, and waiting. However, every optional step must have a clear responsibility; unrelated handling must not be packed into a single node.

## Recognize Before Clicking

`StartGame_ClickStart` does not click fixed coordinates directly. Instead, it first uses OCR to recognize the actual UI text “点击任意处开始” (“Tap Anywhere to Start”):

```text
StartGame_ClickStart
  recognition: OCR "点击任意处开始"
  action: Click
```

This is a basic example of the rule that clicks must be based on visual recognition. During maintenance, do not change it to a fixed-coordinate click without recognition conditions.

## Login Handling

`StartGame_Login` only recognizes verification-code login and prompts the user to handle it manually. It does not attempt to bypass the verification code or automatically handle sensitive login workflows.

The responsibility of this kind of node is to inform the user of the state and leave the workflow at an understandable point.

## Main-Screen Confirmation

Finally, the workflow uses `Status_In_MainMenu` to determine whether the main screen has been reached. This state node recognizes multiple main-screen elements simultaneously, making it more stable than recognizing a single button.

If a new feature also needs to start from the main screen, prefer reusing `Status_In_MainMenu` or `AnySceneEnter_MainMenu` instead of writing another main-screen check.

## Maintenance Priorities

- OCR text in the startup workflow may change with game versions. Maintain the `expected` candidates based on actual game screens.
- The login node only prompts the user and must not attempt to bypass the verification code.
- Clicking start must be based on OCR recognition; do not change it to a fixed-coordinate click.
- After modifying the startup workflow, validate at least the cold-start scenario, the already-signed-in scenario, and the resource-update-required scenario.
