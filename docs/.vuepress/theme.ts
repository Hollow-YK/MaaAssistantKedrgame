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
            { text: "功能介绍", link: "/guide/features" },
          ],
        },
        {
          text: "开发文档", link: "/dev/" 
        },
        { text: "MAAFW",
          children: [
            { text: "如何开发", link: "/develop/how-to-develop" },
            { text: "自定义配置", link: "/develop/custom-configure" },
            { text: "PR 规范", link: "/develop/pull-request-guidelines" },
            { text: "FAQ", link: "/develop/faq" },
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
            text: "功能介绍",
            prefix: "features/",
            link: "features/",
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
          "start-game.md",
          "award.md",
        ],
        "/develop/": [
          "",
          "how-to-develop.md",
          "custom-configure.md",
          "pull-request-guidelines.md",
          "faq.md",
        ],
        "/dev/": [
          "",
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
  },

  plugins: {
    mdEnhance: {
      tabs: true,
    },
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
