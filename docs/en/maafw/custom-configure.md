---
title: Custom Configuration
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# Custom Configuration

## Table of Contents

- [Issue Templates](#issue-templates)
- [VSCode Extensions](#vscode-extensions)
- [Code Formatting Tools](#code-formatting-tools)

## Issue Templates

Good templates can reduce the time you spend communicating with users and help you locate problems more quickly.

Drawing on the templates from the [MAA](https://github.com/MaaAssistantArknights/MaaAssistantArknights) project, we provide a practical option tailored to actual `MaaFramework` usage.

Simply replace `MXX` with your own project name in the `cn-bug-report.yaml` and `en-bug-report.yaml` files under the `.github/ISSUE_TEMPLATE` directory, and the templates are ready to use.

## VSCode Extensions

Good extensions can improve your development efficiency and help you accomplish more with less effort.

- [Maa Pipeline Support](https://marketplace.visualstudio.com/items?itemName=nekosu.maa-support) | MaaFramework extension that provides debugging, screenshots, ROI retrieval, color picking, and other features
- [markdownlint](https://marketplace.visualstudio.com/items?itemName=DavidAnson.vscode-markdownlint) | Markdown syntax-checking extension

## Code Formatting Tools

Code formatting unifies code style, improves readability, and reduces maintenance costs.

The following formatting tools are currently enabled:

| File Type | Formatting Tool |
| --- | --- |
| JSON/Yaml | [prettier](https://prettier.io/) |
| Markdown | [MarkdownLint](https://github.com/DavidAnson/markdownlint-cli2) |

In addition, `oxipng` is used for lossless compression of PNG images.

### Automatically Format Code with Pre-commit Hooks

1. Make sure Python and Node are installed on your computer.

2. Run the following commands in the project root directory.

    ```bash
    pip install pre-commit
    pre-commit install
    ```

If pre-commit still cannot run after installation with pip, make sure the pip installation location has been added to PATH.

From then on, the formatting tools will run automatically with every commit to ensure that your code format complies with the conventions.

### Formatting Configuration

#### Oxipng

This corresponds to the following section in `.pre-commit-config.yaml`:

```yaml
- repo: https://github.com/shssoichiro/oxipng
  rev: v9.1.2
  hooks:
    - id: oxipng
      args: ["-q", "-o", "2", "-s", "--ng"]
```

[Parameter documentation](https://github.com/shssoichiro/oxipng)

#### MarkdownLint

This corresponds to the following section in `.pre-commit-config.yaml`:

```yaml
- repo: https://github.com/DavidAnson/markdownlint-cli2
  rev: v0.13.0
  hooks:
    - id: markdownlint-cli2
      files: ^docs/.*|^README\.md$
      types:
        - markdown
      args: ["--fix", "--config", "docs/.markdownlint.yaml", "#**/node_modules"]
```

The configuration file is `docs/.markdownlint.yaml`; see the [specific rules](https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md).

#### Prettier

This corresponds to the following section in `.pre-commit-config.yaml`:

```yaml
- repo: https://github.com/pre-commit/mirrors-prettier
  rev: v4.0.0-alpha.8
  hooks:
    - id: prettier
      types_or:
        - yaml
        - json
```

The configuration file is `.prettierrc.yaml`; see the [specific rules](https://prettier.io/docs/en/options.html).

The "prettier-plugin-multiline-arrays" extension is used here to preserve multiline arrays. It can be removed if it is not needed.
The related files are `package.json` and `package-lock.json`.
