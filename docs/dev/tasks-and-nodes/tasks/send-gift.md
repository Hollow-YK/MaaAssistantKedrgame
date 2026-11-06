---
title: 赠送礼物
---

# 赠送礼物

任务入口：`SendGift`

PI 文件：`assets/resource/tasks/Friend/SendGift.json`

Pipeline 入口文件：`assets/resource/pipeline/Friend/SendGift.json`

入口节点：`SendGiftMain`

## 功能概述

从任意界面跳到好友列表，每轮找**最靠上且可赠送**的好友点一次，再滑动一屏，直到 OCR 读到「今日赠礼 20/20」或轮数兜底用尽。「可赠送」由 [组合识别取交集](../custom/allof-intersect.md) 判定：模板命中框必须与金色连通块重叠，已赠送的灰色按钮自然被跳过。

无选项（`option` 为空）；任务分组 `Daily` / `Friend`，控制器限 `ADB`。

## 主要节点

- `SendGiftMain`：`SceneJump`（`target: Friend_FriendList`）跳转好友列表。
- `SendGiftLoop`：每轮依次尝试 `SendGiftQuotaFull` → `[JumpBack]SendGiftStep` → `SendGiftFinish`。
- `SendGiftQuotaFull`：OCR `[1120,665,135,25]`，`expected: 20\s*[/／]\s*20`；命中即进 `SendGiftFinish` 收尾。
- `SendGiftStep`：一轮的锚点（默认 `DirectHit`），`next: [SendGiftDo, SendGiftSwipe]`——点到就点、点不到直接滑，保证每轮必滑一次；`max_hit: 50` 兜底总轮数。
- `SendGiftDo`：Custom 识别 `Common_AllOfIntersect`（模板 `sendgift.png` ∩ 金色块，`order_by: Vertical`、`index: 0`），`action: Click`，`next: [SendGiftSwipe]`，`max_hit: 20`。
- `SendGiftSwipe`：`(680,420) → (680,270)`，`end_hold: 1000`，把下面几行带进可视区。
- `SendGiftFinish`：任务完成提示。

## 依赖

| 内容 | 位置 | 说明 |
| --- | --- | --- |
| `UI_Friend_*` | `pipeline/Scene/UI/Friend.json` | 好友名片、各页签选中态、赠送/已赠送图标 |
| `SceneDo_Click_Friend*`、`SceneDo_Close_Friend_InteractionHistory` | `pipeline/Scene/Do/Friend.json` | 进入好友界面与页签互跳 |
| `Friend`、`Friend_*` 场景；`MainMenu → Friend_FriendList`、`Friend → MainMenu`、页签互跳边 | `agent/custom/action/scene_jump_map.json` | 供 `SceneJump` 规划路径 |

## 起点与结束状态

- 起点：任意界面，`SceneJump` 负责跳转。
- 结束：好友列表；今日额度用满或轮数用尽时按成功结束。

## 注意事项

- `ColorMatch` 子识别必须 `connected: true`，否则整条 ROI 会被当成一个结果，交集失效。
- 每日上限数字写死在 `expected` 里，游戏改上限时需同步（也可用 `(\d+)\s*[/／]\s*\1`）。
- `max_hit` 计的是**成功次数**：`SendGiftDo` 满 20 次后被跳过，剩余轮次只滑动。
- 若赠送时出现二次确认或「获得物品」弹窗，当前流程未处理，需要另补节点。
