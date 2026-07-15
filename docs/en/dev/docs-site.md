::: warning AI Translation Notice
This document was translated using AI. Please refer to the Chinese documentation for the definitive version.
:::

# Documentation Site Development

This document explains how to develop and maintain the MAK documentation site.

## Technology Stack

- **Framework**: [VuePress 2](https://vuejs.press/zh/) (v2.0.0-rc.30)
- **Theme**: [VuePress Theme Hope](https://theme-hope.vuejs.press/zh/) (v2.0.0-rc.107)
- **Bundler**: Vite
- **Package Manager**: pnpm
- **Deployment**: GitHub Pages + GitHub Actions

## Directory Structure

```
docs/
├── .vuepress/              ← VuePress configuration
│   ├── config.ts           ← Site configuration (base, locales, and plugins)
│   ├── theme.ts            ← Theme configuration (navbar and sidebar)
│   └── public/             ← Static assets
├── README.md               ← Home page (Simplified Chinese)
├── guide/                  ← User documentation
│   ├── quickstart.md
│   ├── faq.md
│   └── features/
├── maafw/                  ← MaaFramework documentation
│   ├── how-to-develop.md
│   ├── custom-configure.md
│   ├── pull-request-guidelines.md
│   └── faq.md
├── dev/                    ← Documentation-site development (this document)
│   └── README.md
├── en/                     ← English documentation
│   ├── README.md
│   ├── guide/
│   ├── develop/
│   └── dev/
├── .gitignore
├── package.json
└── pnpm-lock.yaml
```

## Local Development

```bash
cd docs
pnpm docs:dev
```

After the server starts, visit `http://localhost:8080/MaaAssistantKedrgame/`.

## Build

```bash
cd docs
pnpm docs:build
```

Build output is written to `docs/.vuepress/dist/`.

## Add a New Page

1. Create a `.md` file in the corresponding directory.
2. Add Frontmatter:

   ```yaml
   ---
  title: Page Title
   ---
   ```

3. Update the navigation bar (`navbar`) and sidebar (`sidebar`) in `.vuepress/theme.ts`.

## Configure the Navigation Bar and Sidebar

The navigation bar and sidebar are configured in `docs/.vuepress/theme.ts`.

### Navigation Bar

```ts
navbar: [
  { text: "Home", link: "/" },
  { text: "User Guide", link: "/guide/quickstart" },
]
```

### Sidebar

```ts
sidebar: {
  "/guide/": [
    "quickstart.md",
    "faq.md",
    { text: "Features", prefix: "features/", link: "features/", children: ["start-game.md", "award.md"] },
  ],
}
```

Path rule: a sidebar key is a path prefix, and links in its value array are relative to that prefix.

## Multiple Languages

The documentation site supports Simplified Chinese (`/`) and English (`/en/`).

To add a new language:

1. Add the language configuration to `locales` in `config.ts`.
2. Add the corresponding navigation bar and sidebar to `locales` in `theme.ts`.
3. Create the corresponding language directory and files.

## Deployment

After changes are pushed to the `main` branch, GitHub Actions automatically builds and deploys the site to GitHub Pages.

View deployment status: repository → Actions → Deploy Docs

## Notes

- Run all commands from the `docs/` directory.
- The `docs/` directory has its own `package.json` and `.gitignore` and is isolated from the project root.
- If a page in a language other than Simplified Chinese has no content, display "Under construction" and link to the Chinese version.
