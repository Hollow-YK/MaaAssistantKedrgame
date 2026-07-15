---
title: How to Develop
---

::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# How to Develop

Before you begin development, read the [Quick Start](https://maafw.com/docs/1.1-QuickStarted) chapter of the MaaFramework development documentation to gain a basic understanding of MaaFramework.

~~We also provide a [🎞️ video tutorial](https://www.bilibili.com/video/BV1yr421E7MW) for reference.~~ The version used in the video is outdated. Always refer to the latest documentation if you encounter any issues.

## Prerequisites

By following this tutorial, you are assumed to comply with the relevant development conventions and consensus for MaaFramework derivative projects. All discussions will also be based on the following prerequisites.

0. You have a GitHub account and are signed in.
1. Use git as the version control tool.
   If you do not yet know how to use it, you can first learn from the [Rookie Tutorial](https://www.runoob.com/git/git-tutorial.html).
2. Host your code on GitHub and use the relevant [CI/CD workflows](https://docs.github.com/zh/actions).
   The project includes several CI/CD workflow configurations based on [GitHub Actions](https://docs.github.com/zh/actions). You can use them to automatically run tests and package and release the project.
3. Understand some common terms used in this framework.
   The [Explanation of Terms](https://maafw.com/docs/1.2-ExplanationOfTerms) chapter of the MaaFramework manual introduces some basic terminology.

## Development Steps

0. On the [project homepage](https://github.com/MaaXYZ/MaaPracticeBoilerplate), select `Use this template` - `Create a new repository` in the upper-right corner to create your own project from this template.
    _(If you cannot find this button, you are not signed in to your GitHub account.)_

1. Clone your project (replace the URL with that of the new project you created from this template).

    ```bash
    git clone https://github.com/<your-username>/<your-project-name>.git
    ```

2. Download the OCR (text recognition) resource file [ppocr_v6.zip](https://download.maafw.xyz/MaaCommonAssets/OCR/ppocr_v6/ppocr_v6-small.zip) and extract it to the `assets/resource/model/ocr/` directory. Make sure the resulting paths are as follows:

    ```tree
    assets/resource/model/ocr/
    ├── det.onnx
    ├── keys.txt
    └── rec.onnx
    ```

    > [!warning]
    > Note that you do not need to upload the OCR resource files to your code repository. The `assets/resource/model/ocr/` directory is already ignored by `.gitignore`, and the GitHub workflow will automatically configure these resource files when releasing a version.

    _If you want to use a different model version, refer to [these instructions](https://github.com/MaaXYZ/MaaCommonAssets/tree/main/OCR)._

3. Begin development. Refer to the [MaaFramework documentation](https://maafw.com/docs/1.1-QuickStarted), modify the `resource` files under the `assets` directory and the `interface.json` file according to your business requirements, and then use the [development tools](https://maafw.com/docs/1.1-QuickStarted#%E8%B0%83%E8%AF%95) for debugging.

    In general, you **do not need** to develop a separate UI for your project. This template includes continuous integration (CI) that automatically configures a _generic UI_. See the following steps for usage instructions.

4. After development is complete, upload your code and release a version.

    ```bash
    # Configure your git identity (required only once)
    git config user.name "your GitHub username"
    git config user.email "your GitHub email address"

    # Commit your changes
    git add .
    git commit -m "feat: add a new feature"
    git push origin HEAD -u
    ```

    If you plan to collaborate with others through a PR, refer to the [PR Guidelines](/en/maafw/pull-request-guidelines) and include a change summary, validation records, and any necessary logs or screenshots.

5. Release your version.

    This template includes a GitHub Actions workflow [configuration file](/.github/workflows/install.yml). When CI detects a tag, it will automatically package and release the project. By default, the configuration file packages and releases [MFAAvalonia](https://github.com/SweetSmellFox/MFAAvalonia) together with your project.

    > [!note]
    > Before doing this for the first time, you must **first** change the GitHub repository setting `Settings` - `Actions` - `General` - `Read and write permissions` - `Save`.

    ```bash
    # Tag the latest commit as v1.0.0 and push the tag
    git tag v1.0.0
    git push origin v1.0.0
    ```

    After running the commands above, CI will automatically package and release the project. You can view the workflow run on the `Actions` page of the project repository. If everything goes well, once the run finishes, you will find the newly released version on the repository's `Releases` page. For more information about GitHub Actions, refer to the [GitHub Actions documentation](https://docs.github.com/zh/actions).

    _If you want to use another [generic UI](https://github.com/MaaXYZ/MaaFramework/#%E9%80%9A%E7%94%A8-ui), modify the workflow [configuration file](/.github/workflows/install.yml) yourself._

## FAQ

Refer to the [FAQ](/en/maafw/faq).

## Further Steps

Refer to [Custom Configuration](/en/maafw/custom-configure) (optional).
