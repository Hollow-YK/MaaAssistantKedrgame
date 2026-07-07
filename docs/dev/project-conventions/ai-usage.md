---
title: AI 使用规范
---

# AI 使用规范

可以使用 AI 辅助开发，但提交者必须对 PR 中的全部内容负责，并能解释、验证和维护这些内容。

## 基本要求

- 遵循项目已有规范。涉及 pipeline 或资源时，必须遵循 [Pipeline 规范](./pipeline)。
- AI 可用于辅助编写 Pipeline、Custom Action 代码和 PR 描述。模板图、ROI 以及 OCR 的 `expect` 不允许使用 AI 生成。
- 开发者必须了解 AI 生成内容的做法及原因，能说明关键节点、字段或代码为什么这样写。
- 开发者必须知道代码会如何运行，包括入口、识别条件、点击目标、跳转路径和失败退路。
- 必须在实际游戏内测试全部 AI 生成的代码，并保证全部按预期运行。

## PR 描述标注

如果 PR 使用了 AI 辅助，请在 PR 描述中标注哪些部分使用了 AI，例如：

```markdown
## AI 内容

- [x] 我已阅读并遵守 [AI 使用规范](../docs/dev/project-conventions/ai-usage.md)

本 PR 中以下部分使用了 AI 工具：

- [x] Pipeline
- [ ] Custom Action
- [ ] 图片资源文件
- [ ] ROI 区域
- [x] PR 描述
- [ ] 没有任何地方使用了 AI
```
