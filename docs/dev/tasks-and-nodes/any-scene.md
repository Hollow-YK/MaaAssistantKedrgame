---
title: 万能跳转
---

# 万能跳转

万能跳转入口：`AnySceneEnter_*`

作用：尽量从任意场景前往特点界面。

## 当前支持

### `AnySceneEnter_MainMenu`

位置：`assets/resource/pipeline/Scene/Do/Mainmenu.json`

前往主页。理论上可以处理：
- 任何有 `HOME` 按钮的界面
- 任意获得物品界面
- 每日登录签到界面
- 月卡界面
- 未登录时的界面
- 部分可以安全处理的弹窗

### `AnySceneEnter_Combat` 及 `AnySceneEnter_Combat_*`

#### `AnySceneEnter_Combat`

位置：`assets/resource/pipeline/Scene/Do/Combat.json`

前往出击页面，利用`AnySceneEnter_MainMenu`实现。

#### `AnySceneEnter_Combat_*`

位置：`assets/resource/pipeline/Scene/Do/Combat.json`

前往出击页面的子页面，利用`AnySceneEnter_Combat`实现。

包括：

| 节点 | 前往的界面 |
| --- | --- |
| `AnySceneEnter_Combat_MainStory` | 出击-主线任务 |
| `AnySceneEnter_Combat_MaterialQuests` | 出击-资源收集 |
| `AnySceneEnter_Combat_MaterialQuests_1` | 出击-资源收集-特别军费行动 |
| `AnySceneEnter_Combat_MaterialQuests_2` | 出击-资源收集-作战体能训练 |
| `AnySceneEnter_Combat_MaterialQuests_3` | 出击-资源收集-兵种能力评级 |
| `AnySceneEnter_Combat_MaterialQuests_4` | 出击-资源收集-载具对抗演练 |
| `AnySceneEnter_Combat_SkillMaterial` | 出击-技能演练 |

## 使用建议

- 由于有较多要识别和进行的操作，性能较差，建议仅在任务的开始/结尾使用。
- 适合作为功能失败或完成后的兜底回主界面节点。
- 不适合替代明确的页面确认。能利用通用 UI / 状态节点节点时，优先使用通用节点。
- 新增会频繁遇到的弹窗时，应先补充安全关闭规则，而不是让业务节点到处处理同一个弹窗。
