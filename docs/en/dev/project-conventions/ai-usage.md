---
title: AI Usage Conventions
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# AI Usage Conventions

AI-assisted development is permitted, but contributors are responsible for all content in their PRs and must be able to explain, validate, and maintain it.

## Basic Requirements

- Follow the project's existing conventions. Changes involving pipelines or resources must follow the [Pipeline Conventions](/en/dev/project-conventions/pipeline).
- AI may assist with writing pipelines, Custom Action code, and PR descriptions. Template images, ROIs, and OCR `expect` values must not be generated with AI.
- Developers must understand how and why AI-generated content works and be able to explain why key nodes, fields, or code are written as they are.
- Developers must know how the code will run, including its entry point, recognition conditions, click targets, transition paths, and failure fallbacks.
- All AI-generated code must be tested in the actual game and verified to work entirely as expected.

## Disclosure in the PR Description

If AI assistance was used in a PR, identify which parts used AI in the PR description. For example:

```markdown
## AI-Generated Content

- [x] I have read and followed the [AI Usage Conventions](../docs/dev/project-conventions/ai-usage.md)

AI tools were used for the following parts of this PR:

- [x] Pipeline
- [ ] Custom Action
- [ ] Image resource files
- [ ] ROI regions
- [x] PR description
- [ ] AI was not used anywhere
```
