---
title: Pull Request Conventions
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# Pull Request Conventions

A PR is the smallest reviewable unit of project collaboration. Give each PR a clear objective, reproducible validation, and sufficient context so that maintainers can determine whether the changes are reliable.

## Basic Requirements

- A PR should address only one issue. Do not mix in unrelated formatting, refactoring, or temporary files.
- PR titles must follow [Conventional Commits](https://www.conventionalcommits.org/zh-hans/v1.0.0/) and state the type and scope of the change, for example, `feat: add reward-claiming task`.
- The PR description must clearly explain why the change is needed, what was changed, its scope of impact, and how it was validated.
- Changes involving pipelines or resources must follow the [Pipeline Conventions](/en/dev/project-conventions/pipeline).
- If AI assistance was used, disclose it in the PR description and follow the [AI Usage Conventions](/en/dev/project-conventions/ai-usage).
- Do not commit build artifacts, caches, debugging screenshots, large model files, or local environment files.

### Optional Requirements

- Before developing a feature, create a draft PR and describe the planned work.
- Refer to the existing documentation and update any documentation affected by the PR.

## Template

Complete the PR description using `.github/PULL_REQUEST_TEMPLATE.md` in the repository root:

```markdown
# Pull Request

- [ ] I have read and followed all [Project Conventions](../docs/dev/project-conventions/)
- [ ] I have read and followed the [PR Conventions](../docs/dev/project-conventions/pull-request.md)

## Related Issue

<!-- Closes #123 / Fixes #123 / Related #123. If there is no Issue, explain the source of the requirement. -->

## Change Summary

<!-- Use 2–5 bullet points to explain what changed. -->

## Validation

<!-- Clearly state what validation was performed and its results. Do not merely write "tested." -->

## Screenshots / Logs / Notes

<!-- For UI changes, resource recognition, workflow failures, or bug fixes, provide screenshots, logs, an Actions link, or reproduction steps. -->

## AI-Generated Content

- [ ] I have read and followed the [AI Usage Conventions](../docs/dev/project-conventions/ai-usage.md)

AI tools were used for the following parts of this PR:

- [ ] Pipeline
- [ ] Custom Action
- [ ] Image resource files
- [ ] ROI regions
- [ ] PR description
- [ ] AI was not used anywhere

```
