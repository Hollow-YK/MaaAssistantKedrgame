---
title: ProjectInterface Conventions
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# ProjectInterface Conventions

`ProjectInterface` is a standardized declaration of a MaaFramework project structure. By defining a PI, you can use the various tools built on MaaFramework. Therefore, even if you intend to integrate purely through a general-purpose programming language, defining a PI that contains the basic information is still recommended.

> This document uses `PI` to refer to `ProjectInterface`.

::: tip
For more information, see the [MaaFramework Project Interface V2 Protocol](https://maafw.com/docs/3.3-ProjectInterfaceV2).
:::

## Task Configuration

When adding a task, create its PI file at `assets\resource\tasks\<TaskName>.json` and add that task PI file to `import` in `interface.json`, rather than adding the task and options directly to `interface.json`.

## Internationalization

Although this project currently supports only Simplified Chinese, internationalization keys should be used, with the corresponding text placed in `assets\resource\locales\interface\zh_cn.json`.

## Presets

Conventions for this section will be added and expanded in the future.
