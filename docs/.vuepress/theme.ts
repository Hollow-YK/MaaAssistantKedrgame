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
            { text: "功能介绍", link: "/guide/features/" },
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
            icon: "fa-solid:question",
            link: "faq.md",
          },
          {
            text: "问题排查手册",
            icon: "fa-solid:info",
            link: "trouble-shooting.md",
          },
          {
            text: "功能介绍",
            icon: "fa7-solid:list-squares",
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
            icon: "fa7-solid:list-squares",
            link: "",
          },
          {
            text: "",
            children: [],
          },
          {
            text: "日常",
            collapsible: true,
            children: [
              "start-game.md",
              "award.md",
              "auto-battle.md",
            ],
          },
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
              "common-nodes.md",
              "any-scene.md",
              {
                text: "任务",
            prefix: "tasks/",
                collapsible: true,
                children: [
                  "start-game.md",
                  "award.md",
                  "auto-battle.md",
                ],
              },
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
            { text: "Troubleshooting", link: "/en/guide/trouble-shooting" },
            { text: "Features", link: "/en/guide/features/" },
          ],
        },
        {
          text: "Development Docs", link: "/en/dev/" ,
          children: [
            { text: "Quick Start", link: "/en/dev/quick-start" },
            { text: "Beginner Guide", link: "/en/dev/beginner-guide/" },
            { text: "Tasks and Nodes", link: "/en/dev/tasks-and-nodes/" },
            { text: "Project Conventions", link: "/en/dev/project-conventions/" },
            { text: "Documentation Site Development", link: "/en/dev/docs-site" },
          ],
        },
        { text: "MAAFW",
          link: "https://maafw.com/en/docs/1.1-QuickStarted",
        },
      ],

      sidebar: {
        "/en/guide/": [
          {
            text: "Quick Start",
            link: "quickstart.md",
          },
          {
            text: "FAQ",
            icon: "fa-solid:question",
            link: "faq.md",
          },
          {
            text: "Troubleshooting",
            icon: "fa-solid:info",
            link: "trouble-shooting.md",
          },
          {
            text: "Features",
            icon: "fa7-solid:list-squares",
            prefix: "features/",
            link: "features/",
          },
          {
            text: "",
            children: [],
          },
          {
            text: "Advanced",
            prefix: "advanced/",
            collapsible: true,
            children: [
              "adb-device.md",
            ],
          },
        ],
        "/en/guide/features/": [
          {
            text: "Features",
            icon: "fa7-solid:list-squares",
            link: "",
          },
          {
            text: "",
            children: [],
          },
          {
            text: "Daily",
            collapsible: true,
            children: [
              "start-game.md",
              "award.md",
              "auto-battle.md",
            ],
          },
        ],
        "/en/dev/": [
          "quick-start.md",
          {
            text: "Beginner Guide",
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
            text: "Tasks and Nodes",
            prefix: "tasks-and-nodes/",
            link: "tasks-and-nodes/",
            collapsible: true,
            children: [
              "common-nodes.md",
              "any-scene.md",
              {
                text: "Tasks",
            prefix: "tasks/",
                collapsible: true,
                children: [
                  "start-game.md",
                  "award.md",
                  "auto-battle.md",
                ],
              },
            ],
          },
          {
            text: "",
            children: [],
          },
          {
            text: "Project Conventions",
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
            text: "Documentation Site Development",
            link: "docs-site.md",
          },
        ],
        "/en/maafw/": [
          "",
          "how-to-develop.md",
          "custom-configure.md",
          "pull-request-guidelines.md",
          "faq.md",
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
