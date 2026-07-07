---
title: 添加功能
---

# 添加功能

新增功能不要一开始就写节点。先把需求拆成能验证的流程，再决定要新增哪些任务、pipeline、图片和配置。

详细规范见 [Pipeline 规范](../project-conventions/pipeline)、[PI 规范](../project-conventions/ProjectInterface)，提交要求见 [PR 规范](../project-conventions/pull-request)。

## 1. 描述功能目标

先用自然语言写清楚：

- 功能从哪里开始。
- 要进入哪个页面。
- 要识别哪些界面元素或文字。
- 要点击什么目标。
- 成功后停在哪里。
- 失败或页面不符合预期时退到哪里。

这一步写不清楚，后面 pipeline 通常也会变成难以维护的节点堆叠。

## 2. 拆分流程阶段

推荐按这些阶段拆：

1. 入口：任务从哪个节点开始。
2. 进入：从稳定场景进入目标页面。
3. 确认：验证是否真的进入目标页面。
4. 执行：点击、OCR、领取、确认等业务动作。
5. 收尾：回到主界面或另一个稳定状态。

每个阶段尽量对应一个或几个职责清楚的节点。不要把进入页面、点击按钮、处理弹窗和返回主界面都写进同一个节点。

## 3. 准备任务入口

新增任务通常涉及这些位置：

- `assets/resource/tasks/<TaskName>.json`：声明任务、标签、入口节点和选项。
- `assets/interface.json`：导入任务文件，让界面能发现任务。
- `assets/resource/pipeline/<TaskName>.json`：编写任务入口和主流程。
- `assets/resource/image/`：放置新增模板图。

任务文件中的 `entry` 必须指向真实存在的 pipeline 节点。

## 4. 编写识别节点

每次点击前，先写识别条件。常见做法：

- 复用已有 `UI_*` 节点识别按钮或入口。
- 复用 `Status_*` 节点确认当前场景。
- 用 OCR 识别实际游戏文字。
- 用 TemplateMatch 识别稳定图标或标签状态。

如果需要新增图片，先确认 [公共节点与万能跳转](./common-nodes) 中是否已有可复用节点，避免重复截图和重复识别。

## 5. 编写动作与验证

点击应建立在识别成功的基础上。点击后尽量写 `Verify` 节点确认页面确实变化，而不是只依赖 `post_delay`。

推荐节点关系：

```text
Task_Enter:MainMenu_Target
	-> Task_Verify:TargetPage
	-> Task_Do:BusinessAction
	-> Task_End
```

收尾时优先回到明确状态。建议在任务结束后回到首页，以便下一项任务开始。

## 6. 验证改动

提交前至少完成：

- 在实际游戏内验证完整流程。
- 编写完善的 PR 描述。
