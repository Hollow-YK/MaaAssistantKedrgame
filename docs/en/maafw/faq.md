---
title: Development FAQ
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# FAQ

## 0. This is my first time using git. What is it? Where did the black command-line window in the video demonstration come from?

The black command-line window is git bash. Nearly all modern software development relies on git. It is recommended that you first refer to the [Rookie Tutorial](https://www.runoob.com/git/git-install-setup.html) or search for video tutorials, learn git, and then continue with the subsequent development work.

## 1. This is my first time using Python. Why does nothing happen after I enter `python ./configure.py` or `python -m pip install MaaFW` on the command line? There is no error, no success message, and no output at all

Windows 10 and Windows 11 include a "Python," but it is actually only an installer and cannot be used as Python.
You need to disable it or remove its environment variable, then download and install Python yourself from the official Python website.
[Instructions for reference](https://www.bilibili.com/read/cv24692025/)

## 2. A pop-up error appears when I use MaaDebugger or MaaPiCli: Application Error — The application was unable to start correctly

![Missing runtime library](https://github.com/user-attachments/assets/942df84b-f47d-4bb5-98b5-ab5d44bc7c2a)

Your computer is generally missing certain runtime libraries. Install [vc_redist](https://aka.ms/vs/17/release/vc_redist.x64.exe).

## 3. How should I package my project?

You need to release a version by following the project's recommended [development workflow](/en/maafw/how-to-develop). [CI](/.github/workflows/install.yml) will automatically package it. For details about how this works, refer to the [GitHub Actions documentation](https://docs.github.com/zh/actions).

## 4. I opened an Issue in this repository a long time ago, but no one has replied

This is the "Project Template" repository. It is only a template, is generally modified infrequently, and receives less attention from developers.
Only ask template-related questions in this repository. Other questions are best raised in the corresponding repository. If you have a log, it is also best to include it (the `debug/maa.log` file).

- Issues with MaaFW itself or MaaPiCli: [MaaFramework/issues](https://github.com/MaaXYZ/MaaFramework/issues)
- Issues with MaaDebugger: [MaaDebugger/issues](https://github.com/MaaXYZ/MaaDebugger/issues)
- Questions you are unsure where to ask, or other questions: [Discussions](https://github.com/MaaXYZ/MaaFramework/discussions)

## 5. OCR text recognition never produces any results and reports "Failed to load det or rec" or "ocrer_ is null"

**Read the documentation carefully.** You ignored the error reported in an earlier step. I do not want to explain it again; please read this document carefully from beginning to end!

## 6. I encountered another problem during development

Working in isolation is unlikely to solve any problems. You can join the [MaaFramework development discussion group](http://qm.qq.com/cgi-bin/qm/qr?_wv=1027&k=9sleK6URhEG0v3QeTmpFueCjF26wibEH&authKey=LBZc5FxWa3M%2BiWj3rpBfRmqg9PD9jJNaxpp3xTqTcGxsp1Am3kd1uzxQXiP4w8w4&noverify=0&group_code=595990173) to seek help.

::: warning
Before asking a question, read the [MaaFramework development documentation](https://maafw.com/docs/1.1-QuickStarted) and [How to Develop](/en/maafw/how-to-develop) in full. In most cases, they can resolve the majority of problems.

When asking a question, **specify the exact section of the documentation that confuses you** / **share the specific contents of your project files** / **provide the complete error message**. Otherwise, the only response you are likely to receive will be something like _"Please read the documentation first"_.
:::
