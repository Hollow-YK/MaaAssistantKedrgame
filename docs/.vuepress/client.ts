import { defineClientConfig } from "vuepress/client";

import QuickStartWizard from "./components/QuickStartWizard.vue";

export default defineClientConfig({
  enhance({ app }) {
    app.component("QuickStartWizard", QuickStartWizard);
  },
});
