---
title: Quick Start
order: 1
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

This guide will walk you through installing and using MAK (the 《雪松》 Assistant). **Even if you know nothing about computers, you can succeed by following these steps one at a time!**

---

## Step 1: Check Your Computer

Before you begin, make sure your computer meets the following requirements:

1. Your computer runs **Windows 10 or Windows 11** (see [Which version of Windows operating system am I running?](https://support.microsoft.com/zh-cn/windows/查看你的-windows-版本-628bec99-476a-2c13-5296-9dd081cdd808))
2. You have an **Android emulator** installed on your computer (software that lets you play mobile games on a computer)

::: info What is an emulator?
An emulator is a program that lets you run mobile games on your computer. The following emulators are recommended:

- **MuMu 模拟器 (MuMu Player)**
- **雷电模拟器 (LDPlayer)**

In theory, any emulator that provides an ADB connection is also supported, as are physical devices.

If you have not installed an emulator yet, search for the relevant emulator, download and install it, and then continue.
:::

::: note
To use MAK with a physical device, refer to [ADB Devices](/en/guide/advanced/adb-device.md).
:::

---

## Step 2: Download MAK

1. Open your browser.
2. Enter the following URL in the address bar, then press Enter:

	``` text
	https://github.com/Hollow-YK/MaaAssistantKedrgame/releases
	```

3. On the downloads page, find the latest version—the one listed at the top. MAK provides two user interfaces, **MFAA** and **MXU**, and each is available as an installer and an archive:

	| UI | Package type | Example filename | Recommendation |
	|----|--------------|------------------|----------------|
	| **MXU** | Installer | `MAK-win-x86_64-xxx-MXU-Setup.exe` | ⭐ Recommended |
	| **MXU** | Archive | `MAK-win-x86_64-xxx-MXU.zip` | For users who prefer not to install the application |
	| **MFAA** | Installer | `MAK-win-x86_64-xxx-MFAA-Setup.exe` | Recommended |
	| **MFAA** | Archive | `MAK-win-x86_64-xxx-MFAA.zip` | For users who prefer not to install the application |

	MFAA and MXU differ only in their user interfaces; they provide the same MAK tasks. Choose either one according to your preference. You do not need to download both.

---

## Step 3: Install MAK

::: tabs#install-type

@tab MXU Installer

This method is recommended for beginners.

1. Download `MAK-win-x86_64-xxx-MXU-Setup.exe`.
2. When the download finishes, **double-click** the file (quickly press the left mouse button twice).
3. If a blue warning dialog appears, click **仍要运行** (“Run anyway”), or click **更多信息** (“More info”) → **仍要运行** (“Run anyway”).
4. Follow the installation wizard to complete the installation.
5. Wait for the installation to finish.

	 ::: tip Tip
	 Some antivirus software may block the installer. This is a false positive and is safe to ignore. If it is blocked, select **允许** (“Allow”) or **信任** (“Trust”) in your antivirus software.
	 :::

@tab MFAA Installer

This method is recommended for beginners.

1. Download `MAK-win-x86_64-xxx-MFAA-Setup.exe`.
2. When the download finishes, **double-click** the file (quickly press the left mouse button twice).
3. If a blue warning dialog appears, click **仍要运行** (“Run anyway”), or click **更多信息** (“More info”) → **仍要运行** (“Run anyway”).
4. Follow the installation wizard to complete the installation.
5. Wait for the installation to finish.

	 ::: tip Tip
	 Some antivirus software may block the installer. This is a false positive and is safe to ignore. If it is blocked, select **允许** (“Allow”) or **信任** (“Trust”) in your antivirus software.
	 :::

@tab MXU Archive

1. Download `MAK-win-x86_64-xxx-MXU.zip`.
2. When the download finishes, extract it into a dedicated folder.

	 ::: warning Warning
	 Use a path containing **ASCII/English characters only**, unless you are able to resolve the problems caused by other paths yourself.

	 For example, extracting to `D:\MAK` works, but extracting to `D:\我的软件\MAK` does not.

	 If you use a non-recommended directory, MAK and its developers reserve the right to decline support for any resulting issues.
	 :::

3. After extraction, open the extracted folder, find `MAK.exe`, and **double-click** it to run MAK.

@tab MFAA Archive

1. Download `MAK-win-x86_64-xxx-MFAA.zip`.
2. When the download finishes, extract it into a dedicated folder.

	 ::: warning Warning
	 Use a path containing **ASCII/English characters only**, unless you are able to resolve the problems caused by other paths yourself.

	 For example, extracting to `D:\MAK` works, but extracting to `D:\我的软件\MAK` does not.

	 If you use a non-recommended directory, MAK and its developers reserve the right to decline support for any resulting issues.
	 :::

3. After extraction, open the extracted folder, find `MAK.exe`, and **double-click** it to run MAK.

:::

---

## Step 4: Configure the Emulator and Game

Before using MAK, make sure your emulator and game are configured correctly.

### Emulator Resolution

MAK operates the game by recognizing images on the screen, so the emulator resolution is very important:

1. Open your emulator.
2. Go to **设置** (“Settings”) → **显示** (“Display”) or **分辨率** (“Resolution”).
3. Set the resolution to a **16:9** aspect ratio (**only 16:9 is currently supported; other aspect ratios will not work**).
4. The following resolutions are supported:

	| Resolution | Notes |
	|------------|-------|
	| `1280×720` (720p) | ⭐ Recommended |
	| `1920×1080` (1080p) | ⭐ Recommended |
	| Other 16:9 resolutions | Not recommended; issues may occur |

::: caution Very Important
The resolution must be changed in the emulator's **system settings**, not in the in-game settings. MAK will not work correctly if the emulator resolution is not 16:9.
:::

---

## Step 5: Use MAK for the First Time

1. **Launch MAK**:
	::: tabs#install-type

	@tab MXU Installer
	Find the `MAK` icon on the desktop and double-click it.

	@tab MFAA Installer
	Find the `MAK` icon on the desktop and double-click it.

	@tab MXU Archive
	Open the extracted folder and double-click `MAK.exe`.

	@tab MFAA Archive
	Open the extracted folder and double-click `MAK.exe`.
	:::

2. **Add a task**: Follow the instructions in the selected UI to add or select the tasks you want MAK to perform.

3. **Connect to the emulator**: Select your emulator in the device or connection settings. MAK will attempt to connect automatically.

4. **Start running**: Click the start button in the UI, and MAK will begin working!

---

## Having Problems?

Do not worry! Check the [FAQ](/en/guide/faq.md) first; the answer you need may already be there.

If the problem remains unresolved, join the QQ discussion group at `253843401` and report it there.
