---
title: 自动回礼
---

# 自动回礼

任务入口：`ReturnGift`

PI 文件：`assets/resource/tasks/Friend/ReturnGift.json`

Pipeline 入口文件：`assets/resource/pipeline/Friend/ReturnGift.json`

入口节点：`ReturnGiftMain`

## 功能概述

先扫描好友「互动履历」里**获赠**的友情点记录，筛出目标游戏日（默认昨天）里给过自己友情点、且额度不为 0 的好友，再按时间先后回到好友列表逐个把友情点回赠回去，直到今日赠礼次数用完或全部回礼完毕。

时间判定按**游戏日**：游戏日在北京时间凌晨 5 点更新，所以 `02:46` 的记录属于前一天。选项「回礼日期」给出偏移量（`0` = 当天、`1` = 昨天……），通过节点的 `attach` 传给 Custom。

流程骨架：

```
任意界面 --SceneJump--> 好友列表
  --SceneDo_Click_Friend_InteractionHistory--> 互动履历
  --多次 ReturnGiftHistory_SwipeNext--> 扫描记录
  --SceneDo_Close_Friend_InteractionHistory--> 好友列表
  --建立名片格子 + ReturnGiftFriend_Sendable + ReturnGiftFriend_SwipeNext--> 逐个回礼
  --> 今日赠礼用完 / 全部回礼完毕
```

## 主要节点

- `ReturnGiftMain`：`SceneJump`（`target: Friend_FriendList`）跳转好友列表。
- `ReturnGift_Do:ReturnGift`：Custom 动作 `Friend_ReturnGift`，整个回礼流程都在这里编排。
- `ReturnGiftQuota`：OCR `[1120,660,140,32]`，`expected: \d+\s*[/／]\s*\d+`，读出「今日赠礼 X/Y」判断额度是否用尽。
- `ReturnGiftFriend_Sendable`：Custom 识别 `Common_AllOfIntersect`，判据与 `SendGiftDo` 相同（模板 `sendgift.png` ∩ 金色连通块），`action: Click`。节点本身的 `roi` 是整列赠送按钮；Custom 会把其中的 `roi` 全部换成「当前格子内的赠送按钮区域」再识别，所以可赠送才点，已赠送的灰按钮自然不命中。
- `ReturnGiftHistory_SwipeNext`：一屏向下滚动互动履历，把更早的记录带进可视区。
- `ReturnGiftFriend_SwipeNext`：`(680,600) → (680,260)`，向上滑动好友列表继续找下一个好友。

## Custom：`Friend_ReturnGift`

`agent/custom/action/friend.py`。参数走节点 `attach`（`custom_action_param` 作为兼容回退，两者同时存在时 `attach` 优先）：

| 参数 | 说明 |
| --- | --- |
| `day` | 目标游戏日偏移，`0` = 当天、`1` = 昨天（默认），以此类推 |
| `dry_run` | `true` 时只扫描不赠送，用于调试 |
| `max_gifts` | 最多赠送几次，缺省用页面上的每日上限 |
| `max_history_scrolls` / `max_friend_swipes` | 两个列表的滑动上限 |
| `settle_interval` / `swipe_delay` | 页面操作与滑动后的等待（秒） |
| `*_node` | 覆盖各步骤的 pipeline 节点名（`history_open_node`、`sendable_node`、`quota_node` 等） |
| `geometry` | 覆盖格子几何参数（例如 `{"list_bottom": 700}`） |

### 一、扫描互动履历

1. 执行 `SceneDo_Click_Friend_InteractionHistory`，等 `UI_Friend_InteractionHistory_Selected` 命中；
2. 截图 OCR 记录区 `[205,242,858,328]`，以**日期列**的文字框为行锚点，再把同一行里落在 玩家名称 / 类型 / 友情点 列的文字归到这一行；
3. 反复执行 `ReturnGiftHistory_SwipeNext` 向下滚动，直到出现比目标游戏日更早的记录（列表按时间倒序，说明后面的都不用看）或连续两次滚动内容不变（已到底）；
4. 执行 `SceneDo_Close_Friend_InteractionHistory` 回到好友列表；
5. 只保留「获赠」且友情点不为 0、日期落在目标游戏日的记录；同一赠送者只回礼一次，按时间先后排序。

### 二、逐个回礼

1. 截图并建立**名片格子**（见下），OCR 格子里的玩家名，与目标好友做模糊匹配；
2. 用 `ReturnGiftFriend_Sendable` 判断该格子能否赠送：能送就点一下，按钮不可赠说明今天已经送过，跳过；
3. 本页没有目标好友时执行 `ReturnGiftFriend_SwipeNext` 继续往下找，**连续两次滑动后可见好友不再变化**即认为已遍历整个好友列表；
4. 下一个好友开始前先执行 `SceneDo_Click_Friend_AddFriend` 切页、等一秒再执行 `SceneDo_Click_Friend_FriendList` 切回来，瞬间回到列表顶部；
5. 每次赠送后用 `ReturnGiftQuota` 回读今日赠礼次数，次数用尽即结束。

### 名片格子的建立

格子就是 `assets/resource/image/0.png` 的大小（1077x131）。锚点是**头像白框**：约 `[32,1,131,131]` 是头像，白框是 124x124 的圆角白边，其左上角会被等级数字挡住，但**右侧竖线**（格子内 x≈158）与**下边框**始终存在：

- 在列表左侧 200 px 内逐列找长度 ≥100 的近白竖线，相邻列合并成边线；
- 同一条边线上不同的 y 段对应不同格子，按 y 范围分组；
- `x0 = 右竖线 x - 158`、`y0 = 白框上沿 - 4`（顶端被列表裁掉时改用 `白框下沿 - 127`）；
- 校验下边框存在、且「赠送」按钮完整落在可视区内（半格不用，滑动后还会再出现）。

白框不可用（名片皮肤不是白色）时退化为 **UID 文字锚点**：`y0 = UID 文字中心 - 45`（UID 区域约 `[185,32,185,26]`，昵称区域约 `[185,4,185,31]`）。

## 依赖

| 内容 | 位置 | 说明 |
| --- | --- | --- |
| `UI_Friend_*` | `pipeline/Scene/UI/Friend.json` | 好友列表/互动履历页签、名片、赠送图标 |
| `SceneDo_Click_Friend_*`、`SceneDo_Close_Friend_InteractionHistory` | `pipeline/Scene/Do/Friend.json` | 页签互跳、开关互动履历 |
| `Common_AllOfIntersect` | `agent/custom/recognition/common.py` | 判断“可赠送”的组合识别 |
| `Friend`、`Friend_FriendList` 场景 | `agent/custom/action/scene_jump_map.json` | 供 `SceneJump` 规划路径 |

## 起点与结束状态

- 起点：任意界面，`SceneJump` 负责跳转。
- 结束：好友列表；今日额度用满或全部回礼完毕时按成功结束。

## 注意事项

- 本任务的 ROI、模板与几何参数来自 `assets/resource/image/0.png`、`1.png`、`2.png` 的实测，**必须在实机分辨率 1280x720 下逐项验证**。
- 「获赠」记录要求友情点不为 0：界面上的 `获赠 0` 表示对方没有送成功或送的是 0 点，这类不会回礼。
- 游戏日按北京时间 05:00 切换，且假定设备时间与北京时间一致；设备时区不对会筛错日期。
- 好友名在列表里可能被截断，匹配允许「首/尾截断」「包含」「相似度 ≥ 0.8」，单字名只认完全一致；低于阈值的近似名字会打日志但不赠送。
- 赠送后如果游戏弹出结算/二次确认窗口，本任务没有处理（未在实机确认是否会出现），此时后续点击会失效；需要时再补对应节点。
- 每日上限来自页面上的 `X/Y`（实测 20），游戏改上限不需要改代码。
- **单独调试两个 Swipe 节点（`ReturnGiftHistory_SwipeNext` / `ReturnGiftFriend_SwipeNext`）时会失败**，报 `Actuator::swipe failed to get swipe begin rect`：这两个节点是纯 `DirectHit` + `Swipe`，框架识别阶段不需要画面也就不会截图，新开的 Tasker 里 `controller.cached_image()` 是空的，`begin`/`end` 的矩形在按画面尺寸裁剪时被压成 0×0，于是判定取不到起点。`SendGiftSwipe`、`Award_Activity_1_DailyAward_Swipe` 单独跑也是同样的失败。正式流程里不会踩到：Custom 在调滑动节点之前一定先 `post_screencap`。要在插件里单独试滑动，先跑一次任意识别型节点（或先跑一遍本任务），让控制端有缓存截图。
