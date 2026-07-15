---
title: Quick Start
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# Quick Start

This guide describes the complete development workflow, from forking the repository to submitting a PR. Before you begin, it is recommended that you familiarize yourself with the basic concepts of MaaFramework: tasks, pipeline nodes, recognition, actions, transitions, and resource directories.

::: tip
For more information, see [MaaFramework Terminology](https://maafw.com/docs/1.2-ExplanationOfTerms).
:::

## 1. Fork and Clone the Repository

1. Sign in to GitHub and open this project's repository.
2. Click Fork in the upper-right corner to copy the repository to your own account.
3. Clone your fork. You must include the submodules when cloning; otherwise, `assets/MaaCommonAssets` will not be downloaded.

::: tabs#git-remote-type

@tab HTTPS

```bash
git clone --recurse-submodules https://github.com/<your-username>/MaaAssistantKedrgame.git
cd MaaAssistantKedrgame
```

@tab SSH

```bash
git clone --recurse-submodules git@github.com:<your-username>/MaaAssistantKedrgame.git
cd MaaAssistantKedrgame
```

Before using SSH, you need to configure an SSH key on GitHub. If you do not know how to configure one, you can use HTTPS for now.

@tab GitHub CLI

```bash
gh repo fork Hollow-YK/MaaAssistantKedrgame --clone=false
gh repo clone <your-username>/MaaAssistantKedrgame -- --recurse-submodules
cd MaaAssistantKedrgame
```

Before using GitHub CLI, install `gh` and sign in by running `gh auth login`.

:::

If you have already cloned the repository with a regular `git clone`, fetch the submodules from the repository root:

```bash
git submodule update --init --recursive
```

4. Add the upstream repository so that you can synchronize updates from the main repository. Choose an address that matches the cloning method you used:

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

GitHub CLI handles sign-in and subsequent GitHub operations, but `git fetch upstream` still requires a Git remote URL. HTTPS is retained here. If you have already configured SSH, you can replace the URL with `git@github.com:Hollow-YK/MaaAssistantKedrgame.git`.

:::

5. Configure your Git identity before your first commit:

```bash
git config user.name "your GitHub username"
git config user.email "your GitHub email address"
```

If you only want these settings to apply to the current repository, do not add `--global`. If you want all repositories to use this identity in the future, use `git config --global ...` instead.

6. Create a new branch before development:

```bash
git switch -c feat/<short-feature-name>
```

Do not develop directly on the `main` branch. Each branch should do only one thing, such as adding one task, fixing one recognition point, or completing one set of documentation.

## 2. Prepare the Development Environment

This project primarily requires the following tools:

- Git: manage code and submit PRs.
- Python: run the Agent, utility scripts, and basic checks.
- Node.js and pnpm: build the documentation site.
- Maa Pipeline Support or MaaFramework debugging tools: take screenshots, capture ROIs, and debug pipelines.

This project uses the `assets/MaaCommonAssets` submodule to provide shared MaaFramework resources. Confirm that the submodule has been initialized:

```bash
git submodule status
```

If the output begins with `-`, the submodule has not been initialized. Run:

```bash
git submodule update --init --recursive
```

Common directories:

- `assets/interface.json`: task entries, resource groups, and Agent configuration for the common UI.
- `assets/resource/tasks/`: task definitions for the common UI.
- `assets/resource/pipeline/`: recognition, action, and workflow nodes.
- `assets/resource/image/`: template images.
- `agent/`: custom Actions and Recognitions.
- `tools/`: installation, validation, and CI helper scripts.
- `docs/`: documentation site source.

Install the Python dependencies:

```bash
python -m pip install -r requirements.txt
```

The OCR models are located in `assets/resource/model/ocr/`. When debugging OCR locally, ensure that the following files exist in that directory:

```tree
assets/resource/model/ocr/
├── det.onnx
├── keys.txt
└── rec.onnx
```

If these files are missing, download [ppocr_v6-small.zip](https://download.maafw.xyz/MaaCommonAssets/OCR/ppocr_v6/ppocr_v6-small.zip) and extract it to that directory. Do not commit locally downloaded model files to the repository; the release workflow configures the OCR resources automatically.

Install the documentation site dependencies:

```bash
cd docs
pnpm install
```

## 3. Read the Development Documentation

If this is your first time contributing to the project, read the documentation in this order:

1. [Beginner Guide](/en/dev/beginner-guide/): understand the learning path.
2. [Pipeline Basics](/en/dev/beginner-guide/pipeline-basics): understand nodes, recognition, actions, and transitions.
3. [Adding a Feature](/en/dev/beginner-guide/new-feature): learn which files usually need to change when adding a task.
4. [Common Nodes and Universal Transitions](/en/dev/beginner-guide/common-nodes): reuse existing nodes first.
5. [Project Conventions](/en/dev/project-conventions/): confirm required practices and prohibited practices.
6. [PR Conventions](/en/dev/project-conventions/pull-request): check the PR description and validation details before submitting.

If you are already familiar with MaaFramework, you can start directly with [Project Conventions](/en/dev/project-conventions/) and [Tasks and Nodes](/en/dev/tasks-and-nodes/).

## 4. Make and Validate Changes

After modifying pipelines or resources, you can run schema validation:

```bash
python -m pip install jsonschema==4.26.0 referencing==0.37.0
python tools/validate_schema.py --schema-dir deps/tools --resource-dirs assets/resource --exclude-dirs assets/resource/announcement --interface-files assets/interface.json
```

If you changed the Python Agent or utility scripts:

```bash
python -m compileall agent tools
```

If you changed the documentation:

```bash
cd docs
pnpm docs:build
```

In addition to command-based checks, you must perform an actual runtime validation: open the tool, select the relevant task, confirm that it can start from the expected scene, complete the target action, and provide an acceptable fallback in exceptional scenarios.

## 5. Build Locally

To inspect the installation directory, run:

```bash
python tools/ci/install_mxu.py v0.0.1
```

Before running it, make sure `deps/bin` exists. The script assembles the `install-mxu/` directory and copies the MaaFramework runtime libraries, project resources, `interface.json`, `README.md`, `LICENSE`, and `agent/`.

You can place MXU in the `install-mxu/` directory and test whether it runs correctly after the build.

Official releases and MXU installation packages are handled by GitHub Actions. Regular PRs do not need to upload build artifacts manually. Do not commit `install/`, `install-mxu/`, cache directories, or local debugging screenshots.

## 6. Submit a PR

Before submitting, synchronize with upstream and confirm that the branch is clean:

```bash
git fetch upstream
git rebase upstream/main
git status
```

Commit your changes and push the current branch:

```bash
git add .
git commit -m "feat: add reward-claiming task"
git push origin HEAD -u
```

Conventional Commits are recommended for commit messages:

```text
feat: add reward-claiming task
fix(pipeline): fix login detection in Start Game
docs: rewrite development documentation
```

After pushing the branch, open a PR to the main repository on GitHub. The PR description must clearly explain what changed, why it changed, and how it was validated. For detailed requirements, see [PR Conventions](/en/dev/project-conventions/pull-request).
