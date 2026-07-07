import { hopeTheme } from "vuepress-theme-hope";

export default hopeTheme({
  hostname: "https://Hollow-YK.github.io",
  logo: "/MaaAssistantKedrgame/logo.png",

  repo: "Hollow-YK/MaaAssistantKedrgame",
  docsDir: "docs",

  locales: {
    "/": {
      navbar: [
        { text: "首页", link: "/" },
        {
          text: "用户文档",
          children: [
            { text: "快速开始", link: "/guide/quickstart" },
            { text: "FAQ", link: "/guide/faq" },
            { text: "问题排查手册", link: "/guide/trouble-shooting" },
            { text: "功能介绍", link: "/guide/features" },
          ],
        },
        {
          text: "开发文档", link: "/dev/" ,
          children: [
            { text: "快速开始", link: "/dev/quick-start" },
            { text: "新手入门", link: "/dev/beginner-guide/" },
            { text: "任务与节点", link: "/dev/tasks-and-nodes/" },
            { text: "项目规范", link: "/dev/project-conventions/" },
            { text: "文档站开发", link: "/dev/docs-site" },
          ],
        },
        { text: "MAAFW",
          children: [
            { text: "如何开发", link: "/maafw/how-to-develop" },
            { text: "自定义配置", link: "/maafw/custom-configure" },
            { text: "PR 规范", link: "/maafw/pull-request-guidelines" },
            { text: "FAQ", link: "/maafw/faq" },
          ],},
      ],

      sidebar: {
        "/guide/": [
          {
            text: "快速开始",
            link: "quickstart.md",
          },
          {
            text: "FAQ（常见问题）",
            link: "faq.md",
          },
          {
            text: "问题排查手册",
            link: "trouble-shooting.md",
          },
          {
            text: "功能介绍",
            prefix: "features/",
            link: "features/",
          },
          {
            text: "",
            children: [],
          },
          {
            text: "高级",
            prefix: "advanced/",
            collapsible: true,
            children: [
              "adb-device.md",
            ],
          },
        ],
        "/guide/features/": [
          {
            text: "功能介绍",
            link: "",
          },
          {
            text: "",
            children: [],
          },
          "start-game.md",
          "award.md",
        ],
        "/dev/": [
          "quick-start.md",
          {
            text: "新手入门",
            prefix: "beginner-guide/",
            link: "beginner-guide/",
            collapsible: true,
            children: [
              "pipeline-basics.md",
              "new-feature.md",
              "common-nodes.md",
              "start-game.md",
            ],
          },
          {
            text: "任务与节点",
            prefix: "tasks-and-nodes/",
            link: "tasks-and-nodes/",
            collapsible: true,
            children: [
              "any-scene-main-menu.md",
              "start-game.md",
              "award.md",
              "common-nodes.md",
            ],
          },
          {
            text: "",
            children: [],
          },
          {
            text: "项目规范",
            prefix: "project-conventions/",
            link: "project-conventions/",
            collapsible: true,
            children: [
              "ProjectInterface.md",
              "pipeline.md",
              "pull-request.md",
              "ai-usage.md",
            ],
          },
          {
            text: "",
            children: [],
          },
          {
            text: "文档站开发",
            link: "docs-site.md",
          },
        ],
        "/maafw/": [
          "",
          "how-to-develop.md",
          "custom-configure.md",
          "pull-request-guidelines.md",
          "faq.md",
        ],
      },
    },
    "/en/": {
      navbar: [
        { text: "Home", link: "/en/" },
        {
          text: "User Guide",
          children: [
            { text: "Quick Start", link: "/en/guide/quickstart" },
            { text: "FAQ", link: "/en/guide/faq" },
            { text: "Trouble Shooting", link: "/en/guide/trouble-shooting" },
            { text: "Features", link: "/en/guide/features" },
          ],
        },
        {
          text: "Development",
          children: [
            { text: "How to Develop", link: "/en/develop/how-to-develop" },
            { text: "Custom Config", link: "/en/develop/custom-configure" },
            { text: "PR Guidelines", link: "/en/develop/pull-request-guidelines" },
            { text: "FAQ", link: "/en/develop/faq" },
          ],
        },
        { text: "MAAFW", link: "https://maafw.com/" },
      ],

      sidebar: {
        "/en/guide/": [
          {
            text: "Quick Start",
            link: "quickstart.md",
          },
          {
            text: "FAQ",
            link: "faq.md",
          },
          {
            text: "Trouble Shooting",
            link: "trouble-shooting.md",
          },
          {
            text: "Features",
            prefix: "features/",
            link: "features/",
            collapsible: true,
            children: ["start-game.md", "award.md"],
          },
          {
            text: "Advanced",
            prefix: "advanced/",
            collapsible: true,
            children: ["adb-device.md"],
          },
        ],
        "/en/guide/features/": [
          {
            text: "Features",
            link: "",
          },
          "start-game.md",
          "award.md",
        ],
        "/en/develop/": [
          "",
          "how-to-develop.md",
          "custom-configure.md",
          "pull-request-guidelines.md",
          "faq.md",
        ],
        "/en/dev/": [
          "",
        ],
      },
    },
  },

  markdown: {
    mermaid: true,
      tabs: true,
    },

  plugins: {
    search: {
      locales: {
        "/": {
          placeholder: "搜索文档",
        },
        "/en/": {
          placeholder: "Search",
        },
      },
    },
  },
});
