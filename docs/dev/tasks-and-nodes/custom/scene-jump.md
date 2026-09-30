---
title: 界面跳转
---

# 界面跳转

<Badge text="开发中功能" type="warning" />

Custom Action：`SceneJump`

文件：`agent/custom/action/scene_jump.py`

数据表：`agent/custom/action/scene_jump_map.json`

Schema：`agent/custom/action/scene_jump_map.schema.json`

## 功能概述

用于从任意界面自动导航到目标界面。

根据`scene_jump_map.json`数据，自动判断当前场景、基于 Dijkstra 规划最短路径，并通过多次“一步跳转”最终到达目标场景。

相比与 Pipeline 写法：更易维护，理论上性能更高。

## 快速使用

在 pipeline 中调用：

```jsonc
{
    "MyJump": {
        "action": {
            "type": "Custom",
            "param": {
                "custom_action": "SceneJump",
                "custom_action_param": {
                    "target": "Combat_SkillMaterial"
                }
            }
        }
    }
}
```

`custom_action_param` 也支持直接写成目标场景名字符串：

```jsonc
"custom_action_param": "Combat_SkillMaterial"
```

### 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `target` | 必填 | 目标场景名（须在 `scenes` 中定义） |
| `max_attempts` | 3 | 单条边内 jump 重试次数 |
| `settle_interval` | 1.0 | 轮询检测间隔（秒） |
| `retry_interval` | 10 | jump 后仍停留在 from 时的重试间隔（秒） |
| `wait_timeout` | 300 | 未知界面/无路径/等待自然跳转的最大等待（秒），超时按失败处理 |
| `max_total_edges` | 30 | 整个流程最多执行的跳转边数（防循环） |
| `strict` | false | true 时遇到未记录的意外场景直接失败 |

## 数据表格式

`scene_jump_map.json` 由 `scenes`（场景定义）与 `edges`（跳转关系）两部分组成。
文件支持 JSONC 注释（`//` 与 `/* */`），注释不影响加载、校验与扩展功能，便于按 `region` 分组标注。

### scenes

```jsonc
{
    "scenes": {
        "Activity_1": { "desc": "活动1（抽象分组，仅作 parent）" },
        "MainMenu": { "desc": "主界面", "detect": "Status_In_MainMenu" },
        "Combat": { "desc": "出击界面", "detect": "Status_In_Combat" },
        "Combat_SkillMaterial": {
            "desc": "出击-技能演练",
            "detect": "UI_Combat_SkillMaterial_selected",
            "parent": "Combat"
        }
    }
}
```

| 字段 | 说明 |
| --- | --- |
| `desc` | 场景描述，用于日志与扩展悬停 |
| `detect` | （可选）用于识别该场景的识别条件；**缺省表示该场景仅作 `parent`** 的抽象场景，不直接识别，也不要求对应 pipeline 节点。支持字符串与组合两种写法，见下 |
| `parent` | （可选）父场景名。表示“处于子场景即视为处于父场景”，规划时子场景可使用父场景的出边 |

#### detect 的两种写法

**写法一：单个节点名字符串**

```jsonc
"detect": "UI_Shop_VipShop"
```

命中该节点即视为处于此场景。

**写法二：组合识别（And / Or）**

```jsonc
"detect": {
    "type": "And",
    "all_of": [
        "UI_Shop_VipShop",
        "UI_Shop_OCRSelected_1"
    ]
}
```

```jsonc
"detect": {
    "type": "Or",
    "any_of": [
        "UI_Shop_VipShop",
        "UI_Shop_Shop"
    ]
}
```

| type | 字段 | 语义 |
| --- | --- | --- |
| `And` | `all_of` | 全部子节点都命中才算处于该场景 |
| `Or` | `any_of` | 任一子节点命中即算处于该场景 |

组合写法用于区分**共用同一父界面节点**的多个子场景。例如商店各子页都长在同一个 `UI_Shop_VipShop`
界面上，靠标签页 OCR 区分：

```jsonc
"Shop":        { "desc": "常驻商店", "detect": "UI_Shop_VipShop" },
"Shop_Shop_1": { "desc": "推荐商店", "detect": { "type": "And", "all_of": ["UI_Shop_VipShop", "UI_Shop_OCRSelected_1"] } },
"Shop_Shop_2": { "desc": "兑换商店", "detect": { "type": "And", "all_of": ["UI_Shop_VipShop", "UI_Shop_OCRSelected_2"] } }
```

字段名与 pipeline 的 `And`/`Or` 一致（`And` 用 `all_of`、`Or` 用 `any_of`）；
列表元素**只支持节点名字符串**（不支持内联识别对象、`box_index`、`sub_name`）。

> **识别性能**：一次检测周期（一次截屏）内，每个 pipeline 节点最多识别一次；且组合写法保留短路
> （`And` 遇假即停、`Or` 遇真即停）。因此上例中 `UI_Shop_VipShop` 只识别一次，若它未命中，
> `Shop_Shop_*` 会直接短路、不再识别各自的 OCR 节点。全量扫描时 34 个引用可降到 29 次识别。

### edges

```jsonc
{
    "edges": [
        {
            "from": "MainMenu",
            "to": "Combat_SkillMaterial",
            "cost": 10,
            "jump": ["AnySceneEnter_Combat_SkillMaterial"],
            "via": ["Loading_Screen", "Combat"]
        },
        {
            "from": "StartGame",
            "to": ["MainMenu", "DailyAward"],
            "cost": 1,
            "jump": ["StartGame_ClickStart"]
        }
    ]
}
```

| 字段 | 说明 |
| --- | --- |
| `from` | 当前场景名（须在 `scenes` 中） |
| `to` | 目标场景名，**或场景名列表**（操作后有概率进入其中任意一个） |
| `cost` | 该一步跳转的成本（缺省 1，越小越优先） |
| `jump` | 一步跳转要执行的 pipeline 节点名（可多个，按序执行）；**可为空 `[]`**，表示无需操作、等待自然跳转。执行时**仅跑该节点本身，忽略其 `next` 链**，不会级联后续节点 |
| `via` | 跳转过程中“可能经过”的中间场景（**并不保证一定经过**，也可能略过） |

## 语义要点

- **路径规划**：当两个场景间存在多条路径时，用 Dijkstra 求“总成本最小”的路径（路径成本 = 各边
  `cost` 之和），而非单纯的步数最少。
- **多候选 `to`**：执行 jump 后有概率落到其中任意一个候选；落到非目标候选时，会沿该候选继续规划下一步。
- **空 `jump`**：表示 `from` 场景无需任何操作，等待后必然会在某一刻自然进入 `to`。
- **`jump` 忽略 `next` 链**：执行 jump 节点时只做该节点本身（识别+动作），不跟随其 `next` 链。
  例如用 `Award_DailyAward_Click:Get` 做 jump 时，不会顺带执行它 `next` 里的月卡检测/回主界面节点；
  点完后由 SceneJump 重新识别场景并按 `to` 判断。
- **无 `detect` 的抽象场景**：仅作 `parent` 的抽象分组（如 `Activity_1`），不参与识别；
  可被 `parent` 引用，也可作为目标（子场景经 `parent` 链满足它）。
- **组合 `detect`**：`{"type":"And","all_of":[...]}` 需全部命中，`{"type":"Or","any_of":[...]}`
  任一命中即可；用于区分共用同一父界面节点的多个子场景。列表元素只支持节点名。
- **识别性能**：一次检测周期内每个节点最多识别一次（节点级缓存），组合写法保留短路，
  因此共用节点不会重复识别、失败时后续组合场景直接短路。
- **`parent` 出边继承**：处于子场景即可使用父场景（沿 `parent` 链）的出边。例如
  `MainMenu → Combat_MainStory`（子场景），再借 `Combat` 的出边到达 `Combat_SkillMaterial`。
- **多起点选择**：同一时刻可能有多个场景同时满足识别（如出击页与其子 Tab），这些场景都可作起点，
  自动选择“到目标总成本最小”的那一个。

## 容错行为

- 未知界面、或当前场景没有通往目标的路径时，会等待场景自行变化，最多 `wait_timeout` 秒，超时按失败处理。
- 因游戏 bug 点击/事件可能丢失：执行 jump 后若仍停留在 `from`，等待 `retry_interval` 秒后重试 jump
  （最多 `max_attempts` 次）。

## Schema 校验

`scene_jump_map.schema.json` 描述了数据表的合法结构（如 `to` 支持字符串或列表、`jump` 可空、
`detect` 支持字符串或 And/Or 组合等），已在 `.vscode/settings.json` 注册，
编辑时 VS Code 会实时校验并给出补全提示。

## 校验工具

`tools/validate_scene_map.py` 用于跨文件一致性校验：把 `scene_jump_map.json` 中每一处节点引用
（场景引用 → `scenes` 定义，节点引用 → pipeline 定义）解析到对应定义，并揪出写错/不存在的节点名。

```sh
python tools/validate_scene_map.py          # 输出全部引用解析 + 校验
python tools/validate_scene_map.py --quiet  # 仅输出错误（适合 CI）
```

## VS Code 扩展

工作区扩展 `.vscode/extensions/maak-scene-jump/` 为 `scene_jump_map.json` 提供：定义跳转
（Ctrl+Click / F12）、悬停、查找引用、文档链接与节点名补全。详见扩展自带的 `README.md`。
