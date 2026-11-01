# 文档站开发

本文档说明如何开发和维护 MAK 文档站。

## 技术栈

- **框架**: [VuePress 2](https://vuejs.press/zh/) (v2.0.0-rc.30)
- **主题**: [VuePress Theme Hope](https://theme-hope.vuejs.press/zh/) (v2.0.0-rc.107)
- **打包工具**: Vite
- **包管理**: pnpm
- **部署**: GitHub Pages + GitHub Actions

## 目录结构

```
docs/
├── .vuepress/              ← VuePress 配置
│   ├── config.ts           ← 站点配置（base、locales、插件）
│   ├── theme.ts            ← 主题配置（导航栏、侧边栏）
│   └── public/             ← 静态资源
├── README.md               ← 首页（简体中文）
├── guide/                  ← 用户文档
│   ├── quickstart/         ← 快速开始（平台 / 界面向导）
│   ├── faq/                ← 常见问题（按 UI 拆分）
│   └── features/
├── maafw/                  ← MaaFramework 相关文档
│   ├── how-to-develop.md
│   ├── custom-configure.md
│   ├── pull-request-guidelines.md
│   └── faq.md
├── dev/                    ← 文档站开发（本文档）
│   └── README.md
├── en/                     ← 英文文档
│   ├── README.md
│   ├── guide/
│   ├── develop/
│   └── dev/
├── .gitignore
├── package.json
└── pnpm-lock.yaml
```

## 本地开发

```bash
cd docs
pnpm docs:dev
```

启动后访问 `http://localhost:8080/MaaAssistantKedrgame/`。

## 构建

```bash
cd docs
pnpm docs:build
```

构建产物输出到 `docs/.vuepress/dist/`。

## 添加新页面

1. 在对应目录下创建 `.md` 文件
2. 添加 Frontmatter：

   ```yaml
   ---
   title: 页面标题
   ---
   ```

3. 更新 `.vuepress/theme.ts` 中的导航栏（`navbar`）和侧边栏（`sidebar`）

## 配置导航栏和侧边栏

导航栏和侧边栏在 `docs/.vuepress/theme.ts` 中配置。

### 导航栏

```ts
navbar: [
  { text: "首页", link: "/" },
  { text: "用户文档", link: "/guide/quickstart/" },
]
```

### 侧边栏

```ts
sidebar: {
  "/guide/": [
    {
      text: "快速开始",
      prefix: "quickstart/",
      link: "quickstart/",
      children: ["mxu.md", "mfaa.md", "maafwapp.md"],
    },
    {
      text: "FAQ",
      prefix: "faq/",
      link: "faq/",
      children: ["mxu.md", "mfaa.md", "maafwapp.md"],
    },
    { text: "功能介绍", prefix: "features/", link: "features/", children: ["start-game.md", "award.md"] },
  ],
}
```

路径规则：侧边栏的 key 是路径前缀，value 数组中的链接相对于该前缀。

## 多语言

文档站支持简体中文（`/`）和英语（`/en/`）两种语言。

**新增内容先写简体中文**，其它语言先放占位页，格式：

```md
---
title: Page Title (待翻译)
---

# Page Title (待翻译 / Pending Translation)

> 本页待翻译。中文原文见 [/guide/quickstart/](/guide/quickstart/)。
> This page is pending translation. See the Chinese original at [/guide/quickstart/](/guide/quickstart/).
```

占位页仍需出现在 `theme.ts` 的对应侧边栏中，避免导航断链。

添加新语言：

1. 在 `config.ts` 的 `locales` 中添加语言配置
2. 在 `theme.ts` 的 `locales` 中添加对应导航栏和侧边栏
3. 创建对应语言的目录和文件

## 部署

推送到 `main` 分支后，GitHub Actions 会自动构建并部署到 GitHub Pages。

查看部署状态：仓库 → Actions → Deploy Docs

## 注意事项

- 所有命令在 `docs/` 目录下执行
- `docs/` 目录有独立的 `package.json` 和 `.gitignore`，与项目根目录隔离
- 非简体中文的页面若内容为空，提示 "Under construction" 并链接到中文版
