---
title: 新手入门
---

# 新手入门

这一组文档面向第一次参与项目开发的贡献者，目标是从零开始走完一次“准备环境、理解 pipeline、添加功能、复用公共节点、阅读现有任务”的开发路径。

这里不会展开所有字段和规范细节，只说明学习顺序和每一步要完成什么。具体写法请跳转到对应页面，并在开发时遵守 [项目规范](../project-conventions/)。

## 1. 开发准备

先完成仓库克隆、依赖安装、资源检查和文档站运行。准备流程见 [快速开始](../quick-start)。

开始写代码前，请先阅读这些规范：

- [Pipeline 规范](../project-conventions/pipeline)
- [PR 规范](../project-conventions/pull-request)
- [AI 使用规范](../project-conventions/ai-usage)

## 2. Pipeline 基础

理解 pipeline 的基本组成：节点、识别、动作、跳转和日志说明。详见 [Pipeline 基础](./pipeline-basics)。

读完后，你应该能看懂一个节点为什么会执行、执行后会去哪里，以及为什么点击必须建立在视觉识别上。

## 3. 添加功能

新增功能时，先把需求拆成“任务入口、页面进入、状态确认、业务动作、收尾返回”。详见 [添加功能](./new-feature)。

这一页会说明新任务通常要改哪些文件，以及如何把功能拆成可审核的 pipeline 节点。

## 4. 使用公共节点

项目已有一批通用 UI、状态和动作节点。新增功能前，应先确认是否可以复用它们。详见 [公共节点与万能跳转](./common-nodes)。

这一页会说明如何使用 `AnySceneEnter_MainMenu`、`Status_In_MainMenu`、`SceneDo_*` 和 `UI_*` 节点。

## 5. 阅读 StartGame 示例

最后阅读 [StartGame 开发流程](./start-game)。`StartGame` 覆盖启动应用、等待加载、处理更新、点击开始、登录提示和主界面确认，适合作为第一个完整 pipeline 示例。
