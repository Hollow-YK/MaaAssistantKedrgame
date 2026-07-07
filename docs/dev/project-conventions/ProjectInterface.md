---
title: ProjectInterface 规范
---

# ProjectInterface 规范

所谓 `ProjectInterface`，即 MaaFramework 的一个标准化的项目结构声明。通过定义 PI，你可以使用 MaaFramework 的各种衍生工具。因此，即使你打算纯粹依靠通用编程语言集成，也建议定义包含基础信息的 PI。

> 文中将使用 `PI` 代指 `ProjectInterface`

::: tip
更多内容可参考[MaaFramework Project Interface V2 协议](https://maafw.com/docs/3.3-ProjectInterfaceV2)
:::

## 任务配置

在添加任务时，应该创建任务的 PI 文件 `assets\resource\tasks\<TaskName>.json` ，并在 `interface.json` 的 `import` 内添加任务的 PI 文件，而不是直接在 `interface.json` 内添加 task 和 option。

## 国际化

虽然本项目目前仅支持简体中文，但是应使用国际化键，并将对应文本写在 `assets\resource\locales\interface\zh_cn.json` 内。

## 预设

未来会添加并补充该部分规范。
