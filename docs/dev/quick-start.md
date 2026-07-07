---
title: 快速开始
---

# 快速开始

本文说明从 fork 仓库到提交 PR 的完整开发流程。开始前建议先了解 MaaFramework 的基本概念：任务、pipeline 节点、识别、动作、跳转和资源目录。

::: tip
更多内容可参考 [MaaFramework 术语解释](https://maafw.com/docs/1.2-ExplanationOfTerms)
:::

## 1. Fork 与克隆仓库

1. 登录 GitHub，打开本项目仓库。
2. 点击右上角 Fork，把仓库复制到自己的账号下。
3. 克隆你 fork 后的仓库。请克隆时必须带上子模块，否则 `assets/MaaCommonAssets` 不会被拉取。

::: tabs#git-remote-type

@tab HTTPS

```bash
git clone --recurse-submodules https://github.com/<你的用户名>/MaaAssistantKedrgame.git
cd MaaAssistantKedrgame
```

@tab SSH

```bash
git clone --recurse-submodules git@github.com:<你的用户名>/MaaAssistantKedrgame.git
cd MaaAssistantKedrgame
```

使用 SSH 前需要先在 GitHub 配置 SSH key。不会配置时可暂时使用 HTTPS。

@tab GitHub CLI

```bash
gh repo fork Hollow-YK/MaaAssistantKedrgame --clone=false
gh repo clone <你的用户名>/MaaAssistantKedrgame -- --recurse-submodules
cd MaaAssistantKedrgame
```

使用 GitHub CLI 前需要先安装 `gh` 并执行 `gh auth login` 登录。

:::

如果已经用普通 `git clone` 克隆过仓库，请在仓库根目录补拉子模块：

```bash
git submodule update --init --recursive
```

4. 添加上游仓库，便于同步主仓库更新。这里也请选择和克隆方式一致的地址：

::: tabs#git-remote-type

@tab HTTPS

```bash
git remote add upstream https://github.com/Hollow-YK/MaaAssistantKedrgame.git
git fetch upstream
```

@tab SSH

```bash
git remote add upstream git@github.com:Hollow-YK/MaaAssistantKedrgame.git
git fetch upstream
```

@tab GitHub CLI

```bash
gh repo set-default Hollow-YK/MaaAssistantKedrgame
git remote add upstream https://github.com/Hollow-YK/MaaAssistantKedrgame.git
git fetch upstream
```

GitHub CLI 负责登录和后续 GitHub 操作，但 `git fetch upstream` 仍然需要一个 Git 远程地址。这里保留 HTTPS；如果你已经配置 SSH，也可以把地址换成 `git@github.com:Hollow-YK/MaaAssistantKedrgame.git`。

:::

5. 第一次提交前配置 Git 身份：

```bash
git config user.name "你的 GitHub 昵称"
git config user.email "你的 GitHub 邮箱"
```

如果你只想对当前仓库生效，不要加 `--global`。如果希望以后所有仓库共用这组身份，可以改用 `git config --global ...`。

6. 开发前创建新分支：

```bash
git switch -c feat/<简短功能名>
```

不要直接在 `main` 分支上开发。一个分支只做一件事，例如新增一个任务、修复一个识别点或补一组文档。

## 2. 准备开发环境

本项目主要需要这些工具：

- Git：管理代码和提交 PR。
- Python：运行 Agent、工具脚本和基础检查。
- Node.js 与 pnpm：构建文档站。
- Maa Pipeline Support 或 MaaFramework 调试工具：截图、取 ROI、调试 pipeline。

本项目使用 `assets/MaaCommonAssets` 子模块提供 MaaFramework 公共资源。确认子模块已初始化：

```bash
git submodule status
```

如果输出前面有 `-`，说明子模块还没有初始化，请执行：

```bash
git submodule update --init --recursive
```

常用目录：

- `assets/interface.json`：通用 UI 的任务入口、资源组、Agent 配置。
- `assets/resource/tasks/`：通用 UI 任务定义。
- `assets/resource/pipeline/`：识别、动作和流程节点。
- `assets/resource/image/`：模板图片。
- `agent/`：自定义 Action 和 Recognition。
- `tools/`：安装、校验和 CI 辅助脚本。
- `docs/`：文档站源码。

安装 Python 依赖：

```bash
python -m pip install -r requirements.txt
```

OCR 模型位于 `assets/resource/model/ocr/`，本地调试 OCR 时需要确保目录中存在这些文件：

```tree
assets/resource/model/ocr/
├── det.onnx
├── keys.txt
└── rec.onnx
```

如果缺少这些文件，可以从 [ppocr_v6-small.zip](https://download.maafw.xyz/MaaCommonAssets/OCR/ppocr_v6/ppocr_v6-small.zip) 下载并解压到该目录。不要把本地下载的模型文件提交进仓库；发布流程会自动配置 OCR 资源。

安装文档站依赖：

```bash
cd docs
pnpm install
```

## 3. 阅读开发文档

第一次参与项目开发时，建议按这个顺序阅读：

1. [新手入门](./beginner-guide/)：了解学习路径。
2. [Pipeline 基础](./beginner-guide/pipeline-basics)：理解节点、识别、动作和跳转。
3. [添加功能](./beginner-guide/new-feature)：了解新增任务通常要改哪些文件。
4. [公共节点与万能跳转](./beginner-guide/common-nodes)：优先复用已有节点。
5. [项目规范](./project-conventions/) ：确认写法和禁止事项。
6. [PR 规范](./project-conventions/pull-request)：提交前检查 PR 描述和验证内容。

如果你已经熟悉 MaaFramework，可以直接从 [项目规范](./project-conventions/) 和 [任务与节点](./tasks-and-nodes/) 开始。

## 4. 修改与验证

修改 pipeline 或资源后，可以运行 schema 校验：

```bash
python -m pip install jsonschema==4.26.0 referencing==0.37.0
python tools/validate_schema.py --schema-dir deps/tools --resource-dirs assets/resource --exclude-dirs assets/resource/announcement --interface-files assets/interface.json
```

如果改了 Python Agent 或工具脚本：

```bash
python -m compileall agent tools
```

如果改了文档：

```bash
cd docs
pnpm docs:build
```

除了命令检查，还需要做实际运行验证：打开工具，选择对应任务，确认它能从预期场景开始、完成目标动作，并在异常场景下有可接受的退路。

## 5. 本地构建

需要检查安装目录时，可以运行：

```bash
python tools/ci/install_mxu.py v0.0.1
```

执行前需要保证 `deps/bin` 已存在。该脚本会组装 `install-mxu/` 目录，复制 MaaFramework 运行库、项目资源、`interface.json`、`README.md`、`LICENSE` 和 `agent/`。

可以将 MXU 放入 `install-mxu/` 目录并测试构建后是否能正常运行。

正式发布和 MXU 安装包由 GitHub Actions 处理。普通 PR 不需要手动上传构建产物，也不要提交 `install/`、`install-mxu/`、缓存目录或本地调试截图。

## 6. 提交 PR

提交前同步上游并确认分支干净：

```bash
git fetch upstream
git rebase upstream/main
git status
```

提交修改并推送当前分支：

```bash
git add .
git commit -m "feat: 添加奖励领取任务"
git push origin HEAD -u
```

提交信息建议使用约定式提交：

```text
feat: 添加奖励领取任务
fix(pipeline): 修复开始游戏登录检测
docs: 重写开发文档
```

推送分支后，在 GitHub 上向主仓库发起 PR。PR 描述必须写清楚改了什么、为什么改、如何验证。详细要求见 [PR 规范](./project-conventions/pull-request)。
