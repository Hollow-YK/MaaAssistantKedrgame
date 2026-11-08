---
title: 自动回礼管理器
---

# 自动回礼管理器

Custom Action：`Friend_ReturnGift`

文件：`agent/custom/action/friend.py`

依赖节点：`assets/resource/pipeline/Friend/ReturnGift.json`、`assets/resource/pipeline/Scene/UI/Friend.json`、`assets/resource/pipeline/Scene/Do/Friend.json`、`assets/resource/pipeline/Scene/Do/Common.json`

## 功能概述

扫描好友「互动履历」，筛出**目标游戏日**里「获赠」的友情点不为 0 的记录，再按时间先后回到好友列表逐个把友情点送回去。

- 数据来源是互动履历的**记录列表**：动作自己 OCR 记录区并按行拼接 玩家名称 / 类型 / 友情点 / 日期，滚动的动作、进出互动履历的动作仍交给 pipeline 节点；
- 时间判定按**游戏日**（北京时间 05:00 切换），目标日由调用方通过 `attach` 的 `day` 传入（`0` = 当天、`1` = 昨天……）；
- 好友定位靠**名片格子**：以头像白框为锚点切格，再用格子里的昵称做模糊匹配；
- 能不能赠送交给 `ReturnGiftFriend_Sendable` 节点（与 `SendGiftDo` 同判据），动作只负责把该节点的 ROI 平移到当前格子上。

## 快速使用

```jsonc
{
    "ReturnGift_Do:ReturnGift": {
        "action": {
            "type": "Custom",
            "param": {
                "custom_action": "Friend_ReturnGift"
            }
        },
        "attach": {
            "day": 1
        }
    }
}
```

调用前需先处于好友列表（`ReturnGiftMain` 里用 `SceneJump` 跳 `Friend_FriendList`）。

参数推荐写在节点 `attach`：`pipeline_override` 对 `attach` 按顶层键合并，选项 case 之间不会互相覆盖；`custom_action_param` 作为兼容回退，两边都有时 `attach` 优先。

### 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `day` | `1` | 目标游戏日偏移（`0` 当天、`1` 昨天……） |
| `dry_run` | `false` | 只扫描不赠送 |
| `max_gifts` | 每日上限 | 最多赠送几次 |
| `max_history_scrolls` | `25` | 互动履历最多滚动几次 |
| `max_friend_swipes` | `30` | 找一个好友时最多滑动几次好友列表 |
| `settle_interval` | `0.8` | 页面操作后的等待（秒） |
| `swipe_delay` | `1.0` | 滑动后的等待（秒） |
| `*_node` | 见下表 | 覆盖各步骤使用的节点名 |
| `geometry` | 见下表 | 覆盖格子几何参数（字符串会被转成对应类型） |

可覆盖的节点名：`history_open_node`（默认 `SceneDo_Click_Friend_InteractionHistory`）、
`history_close_node`（`SceneDo_Close_Friend_InteractionHistory`）、
`history_selected_node`（`UI_Friend_InteractionHistory_Selected`）、
`history_swipe_node`（`ReturnGiftHistory_SwipeNext`）、
`friend_swipe_node`（`ReturnGiftFriend_SwipeNext`）、
`sendable_node`（`ReturnGiftFriend_Sendable`）、
`quota_node`（`ReturnGiftQuota`）、
`add_friend_node`（`SceneDo_Click_Friend_AddFriend`）、
`friend_list_node`（`SceneDo_Click_Friend_FriendList`）、
`friend_list_selected_node`（`UI_Friend_FriendList_Selected`）。

## 名片格子

格子大小同 `assets/resource/image/0.png`：**1077x131**。锚点是头像白框（`[32,1,131,131]` 附近是头像），白框是 124x124 的圆角白边，其左上角被等级数字压住，但**右竖线**与**下边框**始终存在：

| 字段 | 默认 | 说明 |
| --- | --- | --- |
| `cell_left` / `cell_w` / `cell_h` | `19` / `1077` / `131` | 格子左沿（列表左边界）与尺寸 |
| `list_top` / `list_bottom` | `110` / `690` | 列表可视区，越界的半格不参与识别 |
| `frame_*` | `124` / `158` / `4` / `127` | 白框尺寸、右竖线相对格子左边的偏移、上沿/下沿偏移 |
| `frame_scan_w` / `frame_min_run` | `200` / `100` | 白框搜索宽度、竖线最短像素长度 |
| `white_min` | `220` | 近白阈值（RGB 三通道） |
| `name_roi` / `uid_roi` | `[185,4,185,31]` / `[185,32,185,26]` | 昵称、UID 区域 |
| `uid_center_offset` | `45` | 无白框时用 UID 文字中心反推格子 |
| `gift_roi` | `[960,18,112,108]` | 格子里「赠送」按钮的识别区域 |

算法：

1. 逐列找长度 ≥ `frame_min_run` 的连续近白竖线，相邻列合并成边线；
2. 同一条边线上不同 y 段对应不同格子，按 y 范围分组；
3. `x0 = 右竖线 x - 158`、`y0 = 白框上沿 - 4`；顶端被裁掉时改用 `白框下沿 - 127`；
4. 校验下边框存在且「赠送」按钮完整落在可视区（半格会被跳过，滑动后会再出现）。

白框不可用（名片皮肤不是白色）时退化为 **UID 文字锚点**：`y0 = UID 文字中心 - 45`。

## 昵称匹配

互动履历里的名字与好友列表里的名字可能被截断或 OCR 有出入，因此按分数匹配：

| 情况 | 分数 |
| --- | --- |
| 完全一致 | `1.0` |
| 一方是另一方的前缀（截断） | `0.9` |
| 一方是另一方的后缀 | `0.85` |
| 一方包含另一方（长度 ≥ 2） | `0.75` |
| `difflib` 相似度 ≥ 0.8 | `0.7` |

低于 `0.6` 不视为目标好友，但会把最接近的候选与分数打进日志。单字名只认完全一致，避免误送。

## ROI 覆盖的做法

`ReturnGiftFriend_Sendable` 节点自身的两个 `roi` 覆盖整列赠送按钮；赠送时动作读取该节点的解析后数据（`context.get_node_data`），递归把其中的 `roi` 全部换成「当前格子内的赠送按钮区域」，再用这份 override 先 `run_recognition` 判断是否可赠送、命中后 `run_action` 点击。

好处是**节点定义仍是唯一来源**（模板、颜色区间、连通域参数都写在 pipeline 里），代码只做平移，不复制识别参数。

## 流程图

```mermaid
flowchart TD
    subgraph ENTRY["入口（Pipeline）"]
        E1["ReturnGiftMain<br/>SceneJump → Friend_FriendList"]
        E2["ReturnGift_Do:ReturnGift<br/>Custom Action: Friend_ReturnGift"]
        E3["ReturnGiftFinish<br/>日志：自动回礼完成"]
        E1 --> E2
    end

    subgraph SCAN["一、扫描互动履历"]
        S0{"在好友列表？<br/>UI_Friend_FriendList_Selected"}
        S1["SceneDo_Click_Friend_InteractionHistory<br/>点击“互动履历”"]
        S2{"UI_Friend_InteractionHistory_Selected<br/>最长轮询 8 次"}
        S3["截图 + OCR 记录区 205,242,858,328"]
        S4["以“日期”文字框为行锚点分行<br/>归入 玩家名称 / 类型 / 友情点 / 日期"]
        S5["收下 获赠 且 友情点≠0 的记录"]
        S6{"出现早于目标游戏日的记录？"}
        S7{"本页与上一页完全相同？"}
        S8["ReturnGiftHistory_SwipeNext<br/>等 1s"]
        S9["SceneDo_Close_Friend_InteractionHistory<br/>等 0.8s，最多 3 次"]
        S10{"连续 2 次无变化 / 已达 25 页？"}
        S11["筛选 day==目标游戏日<br/>同名只留最早一条 → 按时间升序"]
        S12{"有需要回礼的好友？"}
        S0 -->|是| S1
        S1 --> S2
        S2 -->|命中| S3
        S3 --> S4 --> S5 --> S6
        S6 -->|是，后面的更早| S9
        S6 -->|否| S7
        S7 -->|是| S10
        S7 -->|否| S8
        S8 --> S3
        S10 -->|是| S9
        S10 -->|否| S8
        S9 --> S11 --> S12
    end

    subgraph GIFT["二、逐个回礼（按时间先后）"]
        G0{"今日赠礼 X/Y 已满<br/>或 已赠送 ≥ max_gifts？"}
        G1{"上一轮滑动过列表？"}
        G2["SceneDo_Click_Friend_AddFriend<br/>等 1s"]
        G3["SceneDo_Click_Friend_FriendList<br/>等 1s（回到顶部）"]
        G4["截图 → find_cells 建立名片格子<br/>头像白框（右竖线＋下边框）<br/>找不到则用 UID 文字锚点"]
        G5["OCR 名字列 → 每格 名字 / UID"]
        G6{"昵称匹配 ≥ 0.6？"}
        G7["ReturnGiftFriend_Sendable<br/>节点 ROI 平移到该格子按钮区"]
        G8{"可赠送？"}
        G9["run_action Click<br/>等 1.2s"]
        G10["回读 ReturnGiftQuota + 复查该格按钮"]
        G11{"次数 +1 或 按钮变灰？"}
        G12["已回礼"]
        G13["赠送失败（6 次校验都不过）"]
        G14["今天已送过 → 跳过"]
        G15["下一个赠送者<br/>need_reset = 本轮是否滑动过"]
        G16{"与上次扫描的可见好友（UID）相同？"}
        G17{"已连续 2 次？"}
        G18["判定已遍历整个好友列表 → 没找到"]
        G19{"滑动次数达 max_friend_swipes？"}
        G20["ReturnGiftFriend_SwipeNext<br/>等 1s，scrolled=True"]
        G0 -->|是| E3
        G0 -->|否| G1
        G1 -->|是| G2
        G1 -->|否| G4
        G2 --> G3 --> G4
        G4 --> G5 --> G6
        G6 -->|是| G7
        G6 -->|否| G16
        G7 --> G8
        G8 -->|是| G9 --> G10 --> G11
        G8 -->|否| G14
        G11 -->|是| G12
        G11 -->|否| G13
        G16 -->|是| G17
        G16 -->|否| G19
        G17 -->|是| G18
        G17 -->|否| G19
        G19 -->|是| G18
        G19 -->|否| G20
        G20 --> G4
        G12 --> G15
        G13 --> G15
        G14 --> G15
        G18 --> G15
        G15 --> G0
    end
```
