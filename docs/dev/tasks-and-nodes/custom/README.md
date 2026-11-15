---
title: Custom
---

# Custom

这里记录项目中的自定义扩展（Custom）：自定义动作（Custom Action）与自定义识别（Custom Recognition）
等由 `agent/custom/` 承载的能力。与 [任务与节点](../) 的 pipeline 节点不同，
这里描述的是用代码实现的、更复杂的业务能力。

当前内容：

1. [SceneJump 通用场景跳转](./scene-jump)
2. [Stage_Select 通用选关](./stage-select)
3. [Shop_VIP_Manager 高账商店购物](./shop-manager-VIP)
4. [Friend_ReturnGift 自动回礼](./friend-return-gift)
5. [Common_AllOfIntersect 组合识别取交集](./allof-intersect)

## 停止响应

custom 运行时占用着 pipeline 线程：上层点「停止任务」后，框架只能等当前 custom 返回才会真正停下。
因此带循环或等待的 custom 必须主动响应停止，否则停止延迟会取决于循环长度（等待、
扫荡、回礼等场景可能长达数分钟）。

助手函数在 `agent/custom/action/general.py`：

- `stop_requested(context)`：查询 `context.tasker.stopping`，收到停止请求后为 `True`。
- `interruptible_sleep(context, seconds)`：替代 `time.sleep`，每 250ms（对齐 MaaEnd）
  检查一次停止标志；返回 `False` 表示期间收到了停止请求。

约定：

- 循环每次迭代检查一次 `stop_requested`，命中后立即 `return CustomAction.RunResult(success=False)`。
- 等待一律用 `interruptible_sleep`，并检查返回值。
- 停止后不要再做关闭弹窗、回划列表等收尾操作，这些操作既会被框架拒绝，也会拖慢停止。
- pipeline 里的长 `pre_delay` / `post_delay` 是框架内不可中断的 sleep，约 5 秒以上的固定等待
  应改用 `InterruptibleSleep` custom action（参数 `duration_ms`），否则停止会卡在等待中间；
  `Click` + 长等待用 `ClickAndSleep`（参数 `duration_ms`），可保持原节点与 `[JumpBack]` 跳回目标不变。
- custom 如果保留跨任务模块状态，参考 MaaEnd 的 `runStateResetSink`，注册 `TaskerEventSink`
  在任务 `Succeeded` / `Failed` 时清理；当前 PVP 剩余次数已这样处理。
