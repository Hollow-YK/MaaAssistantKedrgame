---
title: PR Guidelines
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# PR Guidelines

This document describes the basic conventions for submitting a Pull Request (PR) to MaaPracticeBoilerplate. It can also serve as a collaboration reference after creating a MaaFramework project from this template.

## Basic Principles

- **Target branch**: When submitting a PR to this template repository, the default target branch is `main`.
- **Single scope**: Each PR should address one clearly defined issue. Avoid including unrelated formatting, refactoring, or feature changes.
- **Complete description**: The PR description should clearly explain the reason for the change, its scope of impact, and how it was validated.
- **Prefer reuse**: Before modifying template capabilities, first check whether an existing MaaFramework, MaaCommonAssets, or workflow configuration can be reused.
- **Take responsibility**: AI assistance may be used, but the contributor must understand and be able to explain the key changes in the PR.

## Branches and Commits

### Branch Naming

The following formats are recommended:

| Type | Example | Use Case |
| ------ | ------ | ---------- |
| `feat/<name>` | `feat/add-sample-task` | Add a template capability or example |
| `fix/<name>` | `fix/check-workflow` | Fix a bug |
| `docs/<name>` | `docs/pr-guidelines` | Documentation changes |
| `refactor/<name>` | `refactor/resource-layout` | Structural adjustments that do not change behavior |
| `chore/<name>` | `chore/update-deps` | Maintenance of tools, dependencies, builds, and similar areas |

### Commit Messages

Following [Conventional Commits](https://www.conventionalcommits.org/zh-hans/v1.0.0/) is recommended:

```text
<type>(<scope>): <subject>
```

Examples:

```text
docs: add PR guidelines
fix(ci): fix resource-check trigger paths
chore: update the MaaFramework dependency
```

`scope` is optional; specifying the affected area is recommended. Use a short description for `subject` and do not end it with a period.

## PR Titles

The PR title should be consistent with the commit message so that maintainers can quickly identify the type of change:

| Recommended Title | Not Recommended |
| ---------- | ------------ |
| `docs: add PR guidelines` | `update docs` |
| `fix(ci): fix resource-check trigger paths` | `fix the workflow` |
| `feat: add sample task configuration` | `add something` |

If the PR is still under development, use a GitHub Draft PR instead of retaining `WIP` at the beginning of the title for an extended period.

## PR Description

The PR description should include at least the following information:

### Related Items

- Related Issue: `Closes #123`, `Fixes #123`, or `Related #123`
- If there is no Issue, explain the source of the requirement, how to reproduce it, or why the change is needed

### Change Summary

Use 2–5 bullet points to describe what changed, for example:

- Update configuration instructions in the development documentation
- Adjust the GitHub Actions resource-check process
- Add PR submission instructions for template projects

### Validation Records

Describe what validation you performed. Do not merely write "tested"; clearly state what was run and what the result was.

Recommended format:

```markdown
## Validation

- [x] Ran `npm ci && npx @nekosu/maa-tools check`
- [x] Ran `python tools/validate_schema.py --schema-dir deps/tools --resource-dirs assets/resource --exclude-dirs assets/resource/announcement --interface-files assets/interface.json`
- [x] Verified that the documentation links work correctly
```

### Screenshots, Logs, and Assets

For changes involving interfaces, resource recognition, workflow failures, or bug fixes, provide the following whenever possible:

- A comparison of the behavior before and after the change
- Failure logs or a GitHub Actions link
- Paths of added or modified resource files
- Any necessary screenshots or reproduction steps

## Change Requirements

### Template Resource Changes

- Resources such as coordinates, ROIs, and template images should follow MaaFramework's 720p baseline convention.
- When adding tasks or resources, check that `assets/interface.json`, `assets/resource`, and the task configuration are consistent.
- Do not commit local caches, runtime outputs, debugging screenshots, or large downloaded model files.
- When modifying schemas, resource directories, or workflows, explain the impact on projects created from the template.

### Python / Tool Changes

- Keep script logic simple and readable, and avoid introducing unnecessary dependencies.
- After modifying tool scripts, include the validation results for the corresponding commands.
- For long-running processes or operations that users can interrupt, consider exception handling and exit paths.

### Documentation and Configuration Changes

- When user-visible processes, template usage, or development conventions change, update the documentation accordingly.
- Changes related to dependencies, builds, or releases must explain their motivation and include changes to the corresponding lockfiles.
- If a change affects new projects created from the template, clearly describe the migration impact in the PR description.

## Pre-submission Checklist

Before submitting a PR, check at least the following:

- [ ] The PR target branch is `main`
- [ ] The PR title is clear and preferably follows the Conventional Commits format
- [ ] The scope of the change is focused and contains no unrelated changes
- [ ] The branch is up to date with the latest `origin/main`
- [ ] The reason for the change, scope of impact, and validation results are documented
- [ ] Necessary logs or reproduction information are provided for changes involving resources, workflows, or scripts
- [ ] Documentation has been updated to reflect changes in user-visible behavior or development conventions
- [ ] No caches, build artifacts, debugging files, or large model files are committed

## Review and Merge

- Maintainers may request additional logs, reproduction steps, screenshots, or validation records. Continue making the requested corrections in the same PR.
- If review feedback concerns the design direction, reply to confirm the approach before proceeding with extensive changes.
- If an issue is discovered after the PR is merged, open a new Issue or PR to follow up. Do not continue discussing new, unrelated matters in the merged PR.
