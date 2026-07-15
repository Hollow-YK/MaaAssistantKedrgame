---
title: Pull Request 规范
---

# PR 规范

PR 是项目协作的最小审核单元。请让每个 PR 都有明确目标、可复现验证和足够上下文，方便维护者判断改动是否可靠。

## 基本要求

- 一个 PR 只解决一个问题，不混入无关格式化、重构或临时文件。
- PR 标题遵循[约定式提交](https://www.conventionalcommits.org/zh-hans/v1.0.0/)，说明改动类型和范围，例如 `feat: 添加奖励领取任务`。
- PR 描述写清楚改动原因、改动内容、影响范围和验证方式。
- 涉及 pipeline 或资源时，遵循 [Pipeline 规范](./pipeline)。
- 使用 AI 辅助时，必须在 PR 描述中注明，并遵循 [AI 使用规范](./ai-usage)。
- 不提交构建产物、缓存、调试截图、大体积模型文件和本地环境文件。

### 可选要求

- 在开发功能前，先创建草稿（Draft PR）并写明要做的事情
- 参照现有文档，更新 PR 涉及的内容的文档

## 模板

请按仓库根目录的 `.github/PULL_REQUEST_TEMPLATE.md` 填写 PR 描述：

```markdown
# Pull Request

- [ ] 我已阅读并遵守 [项目规范](../docs/dev/project-conventions/) 的全部内容
- [ ] 我已阅读并遵守 [PR 规范](../docs/dev/project-conventions/pull-request.md)

## 关联 Issue

<!-- Closes #123 / Fixes #123 / Related #123；没有 Issue 时请说明需求来源。 -->

## 变更摘要

<!-- 用 2～5 条 bullet 说明改了什么。 -->

## 验证

<!-- 请写清楚执行了什么验证、结果如何。不要只写“已测试”。 -->

## 截图 / 日志 / 说明

<!-- 涉及界面、资源识别、工作流失败或 Bug 修复时，请提供截图、日志、Actions 链接或复现步骤。 -->

## AI 内容

- [ ] 我已阅读并遵守 [AI 使用规范](../docs/dev/project-conventions/ai-usage.md)

本 PR 中以下部分使用了 AI 工具：

- [ ] Pipeline
- [ ] Custom Action
- [ ] 图片资源文件
- [ ] ROI 区域
- [ ] PR 描述
- [ ] 没有任何地方使用了 AI

```
