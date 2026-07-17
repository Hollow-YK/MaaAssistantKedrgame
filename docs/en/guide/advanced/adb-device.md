---
title: ADB Devices
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

## What Is ADB?

ADB (Android Debug Bridge) is an official, versatile command-line tool from Google for communicating with Android devices, including emulators and physical devices. It consists of three components:

- **Client**: Runs on the computer and sends ADB commands.
- **Daemon (`adbd`)**: Runs on the Android device and executes commands.
- **Server**: Runs in the background on the computer and manages communication between the client and daemon.

ADB can be used to install applications, run shell commands, transfer files, take screenshots, and more.

### How MAK Uses ADB

MAK implements automation using **MaaFramework**, which communicates with Android devices through ADB at the underlying level. The complete workflow is as follows:

``` mermaid
flowchart LR
	A[MAK<br/>Main Program] -->|1. Issue task| B[MaaFramework]
	B -->|2. ADB command| C[ADB Client]
	C -->|3. USB / Network| D[Android Device<br/>Emulator / Physical Device]
	D -->|4. Capture screenshot| E[Screen Image]
	E -->|5. Return image| B
	B -->|6. Image recognition| F[Recognition Result]
	F -->|7. Calculate tap position| G[Generated Tap Command]
	G -->|8. Simulate ADB input| D
```

More specifically:

1. **Screenshot**: MaaFramework obtains the device's current screen image through the ADB `screencap` command.
2. **Recognition**: MaaFramework uses its built-in image-recognition algorithms, such as template matching and feature detection, to locate the target button or interface in the screenshot.
3. **Tap**: It simulates a touch by using the ADB `input tap` command.
4. **Loop**: It continuously repeats the steps above to form a complete automation workflow.

MAK defines task flows and recognition targets, such as button screenshots. MaaFramework performs the underlying operations, including taking screenshots, recognizing targets, and tapping.

Therefore, **MAK can control any device that MaaFramework can connect to through ADB**, whether it is an emulator or a physical device.

---

## Connecting to an Emulator with ADB

MAK automatically detects and lists currently running emulator devices. Select the target emulator from the device list in MXU or under Controller Type in MFAA to connect; **you do not need to enter an ADB address manually**.

### Finding an Emulator's ADB Port

If multiple emulators are running at the same time, knowing their default ADB ports can help you quickly identify the target in the device list:

::: note Note
The following information comes from the internet and may be inaccurate. Refer to your actual environment.
:::

| Emulator | Default ADB port | Multi-instance port pattern | Notes |
|----------|------------------|-----------------------------|-------|
| MuMu 模拟器 12 (MuMu Player 12) | `16384` | **+32** (instance 0=16384, 1=16416, 2=16448, …) | Check the ADB icon in the upper-right corner of MuMu 多开器 (MuMu Multi-instance Manager) |
| MuMu 模拟器 6 (MuMu Player 6, legacy) | `7555` | — | Older MuMu versions use this port |
| 雷电模拟器 (LDPlayer) | `5555` | **+2** (instance 0=5555, 1=5557, 2=5559, …) | The device name appears as `emulator-5554`, etc. |
| 夜神模拟器 (NoxPlayer) | `62001` | `59865` (multiple instances) | Check the port for each instance in 夜神多开器 (Nox Multi-Drive) |
| 逍遥模拟器 (MEmu Play) | `21503` | — | Check it in the emulator settings |
| BlueStacks 蓝叠 5 (BlueStacks 5) | `5555` | Several preset ports: `5555/5556/5565/5575/5585/5595` | The **Hyper-V edition uses a random port**; check its configuration file |
| 腾讯手游助手 (Tencent Mobile Game Assistant) | `5555` | — | Fixed port |

::: tip How do I confirm the port number?
Open the emulator's **设置** (“Settings”) → **其他设置** (“Other Settings”) or **ADB 调试** (“ADB Debugging”). The ADB port is usually shown there. You can also run `adb devices` from the command line to view currently connected devices and their ports.

Once you know the port number, find the device with the corresponding port in MAK's device or connection settings.
:::

### Connection Steps

1. **Start the emulator**: Make sure the emulator has opened normally.
2. **Open MAK**: Go to the main interface.
3. **Select the device**: Find and select your emulator in the device list in MXU or under Controller Type in MFAA.
4. **Start using MAK**: Once connected, add tasks and start running them.

### Common Issues

- **Emulator not listed**: Check whether ADB debugging is enabled in the emulator, or try scanning again.
- **Connection refused**: Restart the emulator, or re-enable ADB in the emulator settings.
- **Port conflict**: If multiple emulators are running, their ports may conflict. Close unnecessary emulators and try again.
- **Device list is empty**: Make sure the emulator has started normally and ADB debugging is enabled.

---

## Connecting to a Physical Device with ADB

If you want to use MAK directly on a phone, you can connect an Android physical device through ADB.

::: caution Dangerous Feature
Using MAK with a physical device is extremely dangerous. Make sure you know what you are doing!

You are solely responsible for any consequences caused by using MAK with a physical device. Neither the MAK project nor its developers accept any liability.

Before using MAK with a physical device, understand all potential risks and make sure you know both how to operate it and how to recover from an accident!
:::

### Prerequisites

1. **Enable developer options**: On the phone, go to **设置** (“Settings”) → **关于手机** (“About Phone”) → tap **版本号** (“Build Number”) seven times in succession. The exact steps may vary by manufacturer.
2. **Enable USB debugging**: Go to **设置** (“Settings”) → **开发者选项** (“Developer Options”) → enable **USB 调试** (“USB Debugging”).
3. **Connect the phone to the computer with a data cable**.

### Wired Connection Steps

1. Connect the phone to the computer with a data cable.
2. The first time it connects, the phone will display **允许 USB 调试吗？** (“Allow USB debugging?”). Select **始终允许** (“Always allow”), then tap **确定** (“OK”).
3. Open MAK.
4. On the device selection screen, find your phone and click it.
5. If it does not appear automatically, unplug and reconnect the cable, or restart MAK and scan again.

### Wireless Connection Steps (No Cable Required)

If a data cable is inconvenient, you can use wireless debugging when the phone and computer are on the **same network**.

Detailed steps are omitted.

### Common Issues

- **Device not listed**: Check whether USB debugging is enabled, or unplug and reconnect the cable.
- **Connection failed**: Some phones require the manufacturer's USB driver, which can be downloaded from the phone manufacturer's official website.
- **Driver issue**: If the computer cannot recognize the phone, try installing the [Android USB Driver](https://developer.android.com/studio/run/win-usb) or updating the driver with driver-management software.
- **Unstable wireless connection**: Make sure the phone and computer are on the same network with a strong signal. A wired connection is more stable.
