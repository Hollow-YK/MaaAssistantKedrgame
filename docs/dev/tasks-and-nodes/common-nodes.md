---
title: 通用节点
---

# 通用节点

通用节点是多个任务都能复用的识别、状态和动作。新增业务节点前，先查找是否已有通用节点可用。

## 通用 UI 节点

通用 UI 节点位于 `assets/resource/pipeline/Scene/UI/`。

常用分类：

- `UI_MainMenu_*`：主界面入口，例如任务、资源派遣、邮件、商店。
- `UI_Task_*`：任务页标签、选中状态和领取按钮。
- `UI_Common_*`：返回、主页、弹窗、确认、关闭、获得物品等通用元素。

不要为同一个按钮反复新增模板和识别节点。

## 通用状态节点

文件：`assets/resource/pipeline/Scene/Status.json`

当前状态：

- `Status_In_MainMenu`：通过主界面多个元素确认处于主界面。
- `Status_Loading_Screen`：识别加载界面。

状态节点只做判断，不直接执行业务动作。业务流程应通过状态节点确认当前环境，再进入下一步。

## 通用动作节点

通用动作节点位于 `assets/resource/pipeline/Scene/Do/`。

当前常用节点：

- `SceneDo_PauseHomeButton`：识别 HOME 按钮并点击。
- `SceneDo_GetItem`：识别获得物品界面并点击关闭。
- `SceneDo_Alert_Close_safe`：只关闭已穷举确认安全的弹窗。
- `SceneDo_Alert_Close`：关闭普通弹窗。
- `SceneDo_Alert_Confirm`：确认普通弹窗。

新增通用动作前，要确认它是否真的通用。只服务某个任务的动作，应放在对应任务命名空间下。
