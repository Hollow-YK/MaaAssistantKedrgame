import { defineUserConfig } from "vuepress";
import { viteBundler } from "@vuepress/bundler-vite";
import theme from "./theme.js";

export default defineUserConfig({
  base: "/MaaAssistantKedrgame/",

  locales: {
    "/": {
      lang: "zh-CN",
      title: "MAK - 雪松小助手",
      description: "MaaAssistantKedrgame 文档中心",
    },
    "/en/": {
      lang: "en-US",
      title: "MAK",
      description: "MaaAssistantKedrgame Document Center",
    },
    // 未来扩展:
    // "/zh-TW/": { lang: "zh-TW", title: "MAK - 雪松小助手", description: "..." },
  },

  bundler: viteBundler(),

  // 排除旧版 zh_cn 目录，避免被 VitePress 改版前的文件干扰
  pagePatterns: ["**/*.md", "!zh_cn/**", "!node_modules/**", "!.vuepress/**"],

  theme,
});
