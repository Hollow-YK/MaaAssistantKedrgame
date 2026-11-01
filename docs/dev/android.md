---
title: 安卓打包
---

# 安卓打包

本文说明如何为 MAK 构建 Android APK。Android 客户端以
[MaaFwApp](https://github.com/Aliothmoon/MaaFwApp) 作为外壳，将本仓库的 Project Interface（PI）
在**构建期**打入 APK。运行时通过 [Shizuku](https://shizuku.rikka.app/) 或 root 提权，截屏与
点击由本机 native controller 完成，不经过 ADB。

::: tip
如需下载安装包，请参阅 [MaaFwApp（安卓）向导](../guide/quickstart/maafwapp)。本文面向需要本地
出包或修改打包流程的开发者。
:::

## 接入方式

MaaFwApp 以 **git submodule** 的形式置于 `Android/MaaFwApp`，并固定在具体 commit（当前为
`de65f7a4` / v0.2.2）。`.gitmodules` 中**不写 `branch`**，因此 `git submodule update --remote`
不会改变其版本；升级时须显式切换 commit。

CI 还会以 `MAAFWAPP_REF` 对 submodule 的 gitlink 进行额外断言，二者不一致时构建直接失败。

```text
MaaAssistantKedrgame/
├── Android/
│   ├── MaaFwApp/               # 外壳 submodule，固定 commit
│   ├── profile.yaml            # 打包配方（入库）
│   └── requirements-android.txt
├── assets/                     # PI 根目录（interface.json / resource / resource_*）
├── agent/                      # Python Agent
└── tools/android/              # 构建脚本
```

::: warning 注意
`Android/MaaFwApp/` 是 submodule，**不得**加入 `.gitignore`。`Android/pi/` 与 `Android/agent-dist/`
才是构建产物。
:::

## 版本对齐

APK 内的 MaaFramework `.so` 与 agent 内核自带的 Python 绑定必须版本一致，否则前后端协议可能
不匹配。`requirements.txt` 中的 `maafw==X` 为目标版本，由 `tools/android/resolve_versions.py`
解析：

| 组件 | 来源 |
| --- | --- |
| 目标版本 | `requirements.txt` 中的 `maafw==X` |
| Android client `.so` | resolver 解析出的 MaaFramework tag |
| Android agent 内核 | resolver 解析出的 `MaaAgentCoreAndroid` release |
| MaaFwApp 外壳 | submodule gitlink（CI 以 `MAAFWAPP_REF` 断言） |

resolver 会在 [MaaAgentCoreAndroid](https://github.com/AliothMoon/MaaAgentCoreAndroid) 中查找
`*-maafwX` 配对的内核 release：

- 存在精确配对：`.so` 与内核均使用 `X`。
- 内核尚未发布 `X`：降级至**不高于 X 的最高配对**，并输出 `core_fallback=true`。client `.so`
  随内核版本，APK 内前后端仍保持一致，仅比 `requirements.txt` 所固定的版本旧；上游发布对应
  版本后，降级会自动取消。
- 若不存在可降级的版本：直接失败，并列出当前可用的配对。

预发布版本的拼写会先经归一化处理，例如 `5.15.0-beta.1` 与 `5.15.0b1` 视为同一版本。

```bash
# 查看解析结果
python tools/android/resolve_versions.py

# 与 CI 一致：先解析，再构建
python tools/android/build_apk.py --assemble release --resolve-versions
```

::: note
本地默认要求内核与 `.so` 精确等于 `requirements.txt` 所固定的版本。仅当传入
`--resolve-versions`（或 `--allow-core-fallback`）时，才允许降级。
:::

## 本地构建

### 前置条件

- 已初始化 submodule：`git submodule update --init --recursive`
- JDK 17 及以上（CI 使用 25；Gradle 9.4.1）
- Android SDK（设置 `ANDROID_HOME` 或 `ANDROID_SDK_ROOT`）
- Android NDK 与 CMake `3.22.1`（CI 固定 NDK `29.0.13113456`）
- Python 3.13 及以上

### 命令

```bash
# 1. 整理 PI（会从 MaaCommonAssets 补充 OCR 模型）
python tools/android/stage_pi.py

# 2. 构建 debug APK（arm64-v8a）
python tools/android/build_apk.py --assemble debug

# 3. 构建 release 通用包（arm64-v8a + x86_64）
python tools/android/build_apk.py --assemble release

# 4. 构建单 ABI release 包（体积约为通用包的一半）
python tools/android/build_apk.py --assemble release --abi arm64-v8a
python tools/android/build_apk.py --assemble release --abi x86_64
```

`build_apk.py` 会依次完成版本校验、PI 暂存、MaaFramework `.so` 铺设、agent 运行时构建、
`local.properties` 写入与 Gradle 构建。产物位于：

```text
Android/MaaFwApp/app/build/outputs/apk/debug/*.apk
Android/MaaFwApp/app/build/outputs/apk/release/*.apk
```

如需仅重跑某一步：

```bash
# 仅重新生成 PI
python tools/android/stage_pi.py

# 仅重新铺设 MaaFramework / 仅重建 agent 运行时
python tools/android/build_apk.py --assemble debug --skip-stage --skip-agent
python tools/android/build_apk.py --assemble debug --skip-stage --skip-framework

# 仅校验版本与 submodule，不执行构建
python tools/android/build_apk.py --check-only --resolve-versions
```

### release 签名

MaaFwApp 读取以下环境变量；缺少 `KEYSTORE_PATH` 时将输出未签名 APK：

```bash
set KEYSTORE_PATH=D:\path\to\release.jks
set KEYSTORE_PASSWORD=******
set KEY_ALIAS=******
set KEY_PASSWORD=******
python tools/android/build_apk.py --assemble release
```

### 国内网络

```bash
# 通过镜像 clone / 更新 submodule（.gitmodules 仍保留 GitHub 原始 URL）
git config --global url."https://mirror.example.com/https://github.com/".insteadOf "https://github.com/"

# MaaFramework / 内核下载脚本使用 urllib，设置代理即可
set HTTPS_PROXY=http://127.0.0.1:7890
set HTTP_PROXY=http://127.0.0.1:7890
```

## 升级 MaaFwApp

```bash
git -C Android/MaaFwApp fetch
git -C Android/MaaFwApp checkout <新的 commit>
git add Android/MaaFwApp
```

同时须更新 `.github/workflows/android-build.yml` 中的 `MAAFWAPP_REF`，否则 CI 断言将失败。

## CI 与发布

`.github/workflows/android.yml` 在 push / PR / 手动触发时调用可复用的 `android-build.yml`。
四个 job 均运行于 `ubuntu-latest`：

| job | 内容 |
| --- | --- |
| `meta` | 解析 `maafw_tag` / `core_tag` / `core_fallback`，并运行版本单元测试 |
| `verify` | 执行 `verifyReleaseResources`，校验库模块资源 |
| `build` | 构建通用包：debug 为单 ABI，release 为双 ABI |
| `abi-split` | 仅 release：以矩阵方式构建 `arm64-v8a` / `x86_64` 单 ABI 包 |

release 共产出三个 APK：

```text
MAK-android-universal-<tag>.apk
MAK-android-arm64-v8a-<tag>.apk
MAK-android-x86_64-<tag>.apk
```

::: warning 注意
文件命名是应用内更新选择安装包的依据：**通用包不得带有 ABI 标记，单 ABI 包必须带有 ABI 标记**。
请勿随意修改文件名。
:::

`.github/workflows/install.yml` 在 `v*` tag 上调用 `android-build.yml`，三个 APK 与桌面包一并
发布至 GitHub Release。本仓库暂未接入 Mirror 酱，不执行 Mirror 酱上传。

`v*` tag 发版要求签名：缺少 `KEYSTORE_BASE64` 时构建直接失败（未签名 APK 无法安装，也无法
进入应用内更新）。手动 dispatch 或 PR 的 release 仍允许生成未签名包，仅在日志中告警。

## 运行要求

- Android 10（API 29）及以上。
- 需要 Shizuku 或 root 提权。
- 资源以 720P 为基准制作，后台虚拟屏固定为 1280×720@240dpi；配方已关闭前台模式。
- 包名为 `com.aliothmoon.maafw.mak`，修改包名会改变应用身份。

## 故障排查

| 现象 | 原因与处理 |
| --- | --- |
| `MaaFwApp 子模块未初始化` | 执行 `git submodule update --init --recursive` |
| `子模块检出的 commit 与索引不一致` | 执行 `git submodule update -- Android/MaaFwApp`，请勿手工切换 branch |
| `子模块有未提交的修改` | 外壳目录被修改过，可使用 `git -C Android/MaaFwApp checkout .` 还原 |
| `找不到 OCR 模型` | `assets/MaaCommonAssets` 未检出 |
| `未设置 ANDROID_HOME` | 安装 Android SDK 并设置环境变量 |
| `the agent runtimes ... do not match` | `agent-dist` 缺少对应 ABI，请检查 `--abi` 与 `build.debugAbi/releaseAbi` 是否一致 |
| 设备上 agent 启动失败 | 使用 `adb logcat -s MaaFw` 查看特权进程日志，并确认 APK 内含 `libMaaAgentServer.so` |
| APK 体积异常增大 | 增量构建在 `assets/pi.zip` 中残留旧条目，删除旧 APK 后重新出包 |

### 增量构建的体积问题

MaaFwApp 打包时会就地更新 APK 内的 `assets/pi.zip`，被替换的旧数据会以孤儿条目的形式保留在
文件中。APK 仍可正常安装，但体积会持续累积。若发现安装包体积异常增大，请删除旧产物后重新
出包：

```bash
rm Android/MaaFwApp/app/build/outputs/apk/release/app-release.apk
./gradlew :app:assembleRelease
```
