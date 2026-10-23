---
title: MaaFwApp（安卓）常见问题
order: 8
---

# MaaFwApp（安卓）常见问题

本页收录安卓端（MaaFwApp）相关的常见问题。通用问题见[常见问题总览](./)。

## 安装

::: details 应该下载哪个 APK？

| 文件 | 适用场景 |
| --- | --- |
| `MAK-android-universal-xxx.apk` | 不确定设备架构时选用 |
| `MAK-android-arm64-v8a-xxx.apk` | 绝大多数手机 |
| `MAK-android-x86_64-xxx.apk` | 模拟器（x86 镜像） |

通用包包含两种架构，体积较大；单架构包体积较小，但仅能在对应架构的设备上安装。

:::

::: details 安装时提示「解析包时出现问题」应如何处理？

通常由下载不完整或架构不匹配导致。请重新下载，并确认选择 `arm64-v8a` 或 `universal` 版本。

:::

::: details 安装时提示「签名冲突」应如何处理？

设备上已存在同包名的其他版本（例如测试包）。请先卸载旧包，再安装新包。

:::

---

## 权限与运行

::: details 为什么需要 Shizuku 或 root？

安卓端通过本机 native controller 完成截屏与模拟点击，不经过 ADB，因此需要提权。Shizuku 无需
root，按照其引导授权即可；已获取 root 权限的设备也可直接向 MAK 授予 root 权限。

:::

::: details 点击开始后提示权限不足应如何处理？

请确认 Shizuku 正在运行且已授权 MAK，然后重新启动 MAK。使用 root 时，请确认已在权限管理中
允许 MAK。

:::

::: details 支持哪些 Android 版本？

Android 10（API 29）及以上。安卓端仅提供后台虚拟屏模式，Android 9 及以下版本会被系统拦截。

:::

::: details 任务运行期间可以锁屏或切换到其他应用吗？

可以。任务在后台虚拟屏上运行，不依赖前台界面。

:::

---

## 更新与资源

::: details 为什么应用内没有提示新版本？

应用内更新检查依赖 Mirror 酱，本仓库暂未接入。请前往
[Release](https://github.com/Hollow-YK/MaaAssistantKedrgame/releases) 页面手动下载新版本。

:::

::: details 是否支持热更新资源？

不支持。资源在构建期打入 APK，更换资源需重新安装新包。

:::

::: details 为什么不需要设置分辨率？

安卓端使用后台虚拟屏，分辨率固定为 1280×720@240dpi，与资源基准一致。电脑端才需要手动将
模拟器设置为 16:9。

:::
