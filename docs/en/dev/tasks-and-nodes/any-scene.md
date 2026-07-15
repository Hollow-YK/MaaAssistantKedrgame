---
title: Any-Scene Navigation
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# Any-Scene Navigation

Any-scene navigation entry points: `AnySceneEnter_*`

Purpose: navigate from almost any scene to a specific screen whenever possible.

## Currently Supported

### `AnySceneEnter_MainMenu`

Location: `assets/resource/pipeline/Scene/Do/Mainmenu.json`

Navigates to 主页 (Home). In theory, it can handle:

- Any screen with a `HOME` button
- Any 获得物品 (Items Obtained) screen
- The 每日登录签到 (Daily Login) screen
- The 月卡 (Monthly Pass) screen
- Screens shown when the user is not logged in
- Some pop-ups that can be handled safely

### `AnySceneEnter_Combat` and `AnySceneEnter_Combat_*`

#### `AnySceneEnter_Combat`

Location: `assets/resource/pipeline/Scene/Do/Combat.json`

Navigates to the 出击 (Combat) screen using `AnySceneEnter_MainMenu`.

#### `AnySceneEnter_Combat_*`

Location: `assets/resource/pipeline/Scene/Do/Combat.json`

Navigates to subscreens under 出击 (Combat) using `AnySceneEnter_Combat`.

These include:

| Node | Destination screen |
| --- | --- |
| `AnySceneEnter_Combat_MainStory` | 出击-主线任务 (Combat - Main Story) |
| `AnySceneEnter_Combat_MaterialQuests` | 出击-资源收集 (Combat - Resource Collection) |
| `AnySceneEnter_Combat_MaterialQuests_1` | 出击-资源收集-特别军费行动 (Combat - Resource Collection - Special Military Funding Operation) |
| `AnySceneEnter_Combat_MaterialQuests_2` | 出击-资源收集-作战体能训练 (Combat - Resource Collection - Combat Fitness Training) |
| `AnySceneEnter_Combat_MaterialQuests_3` | 出击-资源收集-兵种能力评级 (Combat - Resource Collection - Unit-Type Proficiency Assessment) |
| `AnySceneEnter_Combat_MaterialQuests_4` | 出击-资源收集-载具对抗演练 (Combat - Resource Collection - Vehicle Combat Exercise) |
| `AnySceneEnter_Combat_SkillMaterial` | 出击-技能演练 (Combat - Skill Training) |

## Usage Recommendations

- Because many recognition checks and operations are required, performance is relatively poor. Use these nodes only at the beginning or end of a task when possible.
- They are suitable as fallback nodes that return to the main screen after a feature fails or completes.
- They should not replace explicit screen verification. Prefer shared UI or state nodes whenever they can be used.
- When adding a pop-up that will be encountered frequently, add a safe-close rule first rather than handling the same pop-up throughout business-specific nodes.
