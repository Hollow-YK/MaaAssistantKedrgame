---
title: Troubleshooting Guide
order: 6
icon: fa-solid:info
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# Troubleshooting Guide

Encountered a problem while using MAK? Follow the steps below first—you may be able to resolve it yourself!

> 💡 You can also visit the [Frequently Asked Questions (FAQ)](/en/guide/faq.md) for conceptual answers.

---

## Runtime Issues

### MAK Does Not Start

::: details **MXU** displays `Could not find the WebView2 Runtime.`

MXU is missing WebView2.

Go to [Microsoft Edge WebView2](https://developer.microsoft.com/zh-cn/microsoft-edge/webview2), then download and install `Microsoft Edge WebView2`.

:::

::: details **MFAA** displays `To run this application, you must install .NET`

Go to [Download .NET 10.0](https://dotnet.microsoft.com/zh-tw/download/dotnet/thank-you/sdk-10.0.300-windows-x64-installer), then download and install the `.NET 10.0 Desktop Runtime`.

Double-click `DependencySetup_依赖库安装_win.bat` in the MAK directory, follow the prompts to install the dependencies required by MFAA, and then restart MAK.

:::

::: details **MFAA** does not start or reports missing dependencies

Double-click `DependencySetup_依赖库安装_win.bat` in the MAK directory, follow the prompts to install the dependencies required by MFAA, and then restart MAK.

Alternatively, download and install the required runtime according to the error message.

:::

::: details A “用户账户控制” (“User Account Control”) window appears when MAK starts

This is a Windows security mechanism. MAK requires administrator privileges to control the emulator window.

**Solution**: Click **是** (“Yes”). This prompt appears every time MAK starts; this is normal, so click **是** each time.

> If you do not want this prompt to appear every time, you can search for “disable UAC in Windows” to learn how to disable it. **This is not recommended**, because it reduces your computer's security.
>
> It is equivalent to telling the doorman who normally reports every visitor to your home to stop reporting them and let everyone enter directly.

:::

::: details The downloaded installer will not open and says “Windows 已保护你的电脑” (“Windows protected your PC”)

This is a Windows security warning because MAK does not have a signing certificate. **MAK is safe, open-source software**, so you can use it with confidence.

**Solution**: Click **更多信息** (“More info”) in the dialog, then click **仍要运行** (“Run anyway”).

:::

::: details Antivirus software deleted MAK

Some antivirus software incorrectly identifies MAK as a virus—a false positive.

**Solution**:

1. Open your antivirus software.
2. Find **隔离区** (“Quarantine”) or **恢复区** (“Recovery”).
3. Find the deleted MAK file, select **恢复** (“Restore”), and then **添加信任** (“Add to trusted items”).
4. If you do not know how, search for “how to add an exception in &lt;antivirus-name&gt;”.

> If you are concerned, all MAK source code is publicly available on [GitHub](https://github.com/Hollow-YK/MaaAssistantKedrgame), where anyone can inspect it.

:::

::: details An invalid-path error appears during extraction

The archive version must be extracted to a path containing **ASCII/English characters only**.

- ✅ Correct: `C:\MAK`, `D:\Games\MAK`
- ❌ Incorrect: `C:\我的软件\MAK`, `C:\游戏\雪松小助手`

:::

::: details The UI crashes

We have currently observed this issue among some MXU users.

This may be a UI issue. Try reinstalling first. If it still crashes, switch to the other UI.

:::

### Tasks Do Not Start

::: details Nothing happens after clicking 开始 (“Start”)

Check the following:

1. Has the emulator already started? The emulator must be running.
2. Is the game installed in the emulator?
3. Have you added at least one task in MAK?
4. Did you click **是** (“Yes”) when MAK started to grant administrator privileges? If not, close MAK and run it again as administrator.

:::

::: details The current controller is not supported

	::: tabs#ui-type

	@tab MXU Version
	Select an appropriate controller under **连接设置** (“Connection Settings”) in the upper-right corner of MAK.

	@tab MFAA Version
	Select an appropriate controller under **控制器类型** (“Controller Type”) near the upper-left area of MAK.
	:::

:::

::: details Unable to connect to a device

- Make sure the emulator is open or the device is connected.
- Make sure MAK is **running as administrator**.

:::

::: details Resource loading failed

Retrieve the files again according to your installation method:

	::: tabs#install-type

	@tab Installer (MFAA / MXU)

	Under **设置** (“Settings”) → **应用** (“Apps”) → **安装的应用** (“Installed apps”), find MAK, select **卸载** (“Uninstall”), and then reinstall it.

	@tab MXU Archive

	Delete everything in the MAK directory—you may keep the `config` folder—and then extract the archive again.

	@tab MFAA Archive

	Delete everything in the MAK directory—you may keep the `config` folder and `appsettings.json`—and then extract the archive again.

	:::

:::

::: details An `HD_python.exe` window appears

Your computer may be infected with a **computer worm**. Run an antivirus scan and reinstall the operating system as soon as possible. We do not provide support for this type of issue.

:::

### Tasks Behave Unexpectedly

::: details Why does MAK keep failing to recognize the screen?

Possible causes:

1. **Incorrect emulator resolution**: The emulator resolution must be 16:9. 1280×720 or 1920×1080 is recommended. Change it in the **emulator's system settings**, not in the in-game settings. Other aspect ratios are **not currently supported**.
2. **MAK is not running as administrator**: MAK requires administrator privileges. Click **是** (“Yes”) when the **用户账户控制** (“User Account Control”) prompt appears at startup.
3. **An old version is being used**: MAK only provides support for the latest version; older versions generally will not be considered.
4. **The game has changed**: If a game update changes the interface, MAK may need some time to adapt.

:::

::: details Taps or other operations do not work correctly

- Make sure MAK is located in a path containing **ASCII/English characters only**, with no full-width symbols.
- Make sure MAK is **running as administrator**.
- Make sure MAK is connected to the correct device.
- Try reinstalling MAK.

:::

::: details Tasks fail frequently

This may be caused by a bug in MAK, or it may be caused by 《雪松》.

:::

---

## Task-Specific Issues

### Launch Game (启动游戏)

::: details Unable to launch the game

Check the following:

1. Is the emulator resolution 16:9? 1280×720 or 1920×1080 is recommended.
2. Is MAK running as administrator?
3. Is the game installed correctly in the emulator?
4. Did you select the correct resource files, and are they for one of the distribution-channel versions supported by MAK?

:::

### Claim Rewards (领取奖励)

::: details Unable to claim rewards

Make sure you are logged in to the game and that the rewards can be claimed manually. If the game interface has been updated, MAK may need some time to adapt.

:::
