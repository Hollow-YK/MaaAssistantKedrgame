---
title: Frequently Asked Questions (FAQ)
order: 5
icon: fa-solid:question
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# Frequently Asked Questions (FAQ)

This section mainly provides conceptual answers about MAK (the 《雪松》 Assistant).

> ⚠️ **Encountered a runtime error or unexpected behavior?** Check the [Troubleshooting Guide](/en/guide/trouble-shooting.md) first for detailed troubleshooting steps.

---

## MXU (User Interface)

::: details What is MXU?

**MXU** (MaaFramework Next UI) is a general-purpose GUI client based on the [MaaFramework PI V2](https://github.com/MaaXYZ/MaaFramework/blob/main/docs/zh_cn/3.3-ProjectInterfaceV2%E5%8D%8F%E8%AE%AE.md) protocol. It provides this project with a ready-to-use graphical interface.

:::

::: details Why was MXU chosen?

Drawing on experience contributing to [MaaNTE](https://github.com/1bananachicken/MaaNTE), and after considering projects such as [M9A](https://github.com/MAA1999/M9A) and [MaaEnd](https://github.com/MaaEnd/MaaEnd), the developer decided to use MXU.

For this project, MXU offers advantages such as straightforward configuration, convenient interface interactions, and excellent log management. Although it still has a few shortcomings, it is currently the most suitable of the mainstream MaaFramework GUIs.

:::

### Configurations/Tabs

::: details What is a configuration/tab?

MXU presents MaaFramework configurations as tabs, allowing users to select appropriate configurations for different purposes. Each tab represents an independent set of settings, so you can create different configurations for different scenarios.

:::

::: details What is covered by a configuration?

MXU describes this as “the task and device settings of each configuration are independent.” In practice:

- **Independent tasks**: Each configuration has its own task list, detailed task settings, task enabled states, task expanded states, and so on.
- **Independent scheduling**: Scheduled execution settings do not affect other configurations.
- **Independent connection settings**: Each configuration has its own controller, connection window, live screenshot display state, and so on.
- **Shared global settings**: Settings under **设置** (“Settings”) are shared by all configurations.

:::

::: details About preset configurations

In the future, some commonly used configurations will be consolidated into several presets and applied automatically the first time the software starts. If you do not need one, you can delete that configuration by closing its tab.

If you accidentally delete a preset configuration and want to add it back, simply select the corresponding preset when creating a new configuration.

:::

::: details About scheduled-execution configurations

At the bottom right of a configuration, you can use the scheduling feature to run that configuration at set times. Scheduling is independent for each configuration.

:::

### Tasks

::: details What is a task?

Each automation feature in MAK is an independent “task” that you can freely enable or disable as needed. Every task corresponds to a specific in-game action or game mode.

Select the tasks you want to run in the task list, and MAK will execute them sequentially in list order.

:::

::: details In what order are tasks executed?

Tasks are executed **from top to bottom in the task list**, and unselected tasks are skipped. To change the order, drag the six dots to the left of a task title.

:::

::: details Why can't multiple tasks run simultaneously?

MAK automates the game through image recognition and simulated mouse and keyboard operations. Running multiple tasks simultaneously would cause their operations to interfere with each other, so MAK is designed to execute tasks sequentially.

:::

::: details What is a controller, and how do controllers differ?

A controller is a MaaFramework component used to interact with the game window. MAK provides one controller: `ADB`.

You can select the appropriate controller under **连接设置** (“Connection Settings”) in the upper-right corner.

:::

::: details How can I tell whether a task is running normally?

While a task is running, you can view live logs in MAK's log panel. If a task encounters an error or fails, the log will show a corresponding error message.

:::

---

## Usage

::: details What emulator resolution should I use?

MAK **only supports 16:9 resolutions**. The following two are recommended:

- `1280×720` (720p)
- `1920×1080` (1080p)

	::: warning Warning
	Change the resolution in the **emulator's system settings**, not in the in-game settings!
	:::

:::

::: details Can I use my computer while MAK is operating?

Yes, but do not interact with the emulator. MAK automatically taps the screen and recognizes what is displayed while it runs. Interacting with the emulator may cause MAK to fail.

Recommendation: While MAK is running, use another application or take a break and wait for it to finish.

:::

::: details Which game versions does MAK support?

MAK currently supports the **official version** of 《雪松》 (downloaded from the official website). The Bilibili and other distribution-channel versions may have some adaptations and should theoretically work as well.

:::

::: details There are too few features. When will new ones be added?

This project is still in an early stage of development and is maintained by developers in their spare time. New features will be added over time. Follow the [GitHub Releases](https://github.com/Hollow-YK/MaaAssistantKedrgame/releases) page for updates.

:::

::: details Could using MAK get my account banned?

MAK only simulates your finger tapping the screen. It does not modify any game data and is essentially equivalent to operating the game manually.

However, using third-party assistance tools carries some risk under the game's user agreement. **Assess the risk yourself before using MAK.** This project accepts no responsibility for any consequences.

:::

::: details Can I use MAK on a Mac?

MAK currently supports Windows only. macOS is not supported at this time.

:::

---

## Other Questions

::: details How can I suggest an improvement or report a bug to the developers?

If you use GitHub:

- Submit a suggestion or bug report through [GitHub Issues](https://github.com/Hollow-YK/MaaAssistantKedrgame/issues).

If you do not use GitHub:

- Join the QQ group **253843401** and report it there.

:::

::: details How can I develop a new feature or fix a bug?

Refer to the [development documentation](/en/dev/).

:::

---

> 💡 Still have questions? Join the QQ discussion group **253843401** and ask there.
