# Maximo MCP Server — Documentation

VitePress documentation site for [`@soumyaprasadrana/maximo-mcp-server`](https://www.npmjs.com/package/@soumyaprasadrana/maximo-mcp-server).

This folder is a **self-contained docs project** meant to live in its own public repository and publish to **GitHub Pages** automatically via GitHub Actions.

## Structure

```
.
├─ package.json                 # vitepress + scripts
├─ .github/workflows/deploy.yml # auto-build + deploy to GitHub Pages
└─ docs/
   ├─ .vitepress/config.mts     # site config (nav, sidebar, base path)
   ├─ index.md                  # home
   ├─ guide/                    # introduction, install, config, clients
   ├─ concepts/                 # metadata engine, working set, child records, security
   ├─ tools/                    # full tool reference
   └─ recipes/                  # orchestration patterns
```

## Local development

```bash
npm install
npm run docs:dev      # http://localhost:5173
npm run docs:build    # output → docs/.vitepress/dist
npm run docs:preview   # serve the production build locally
```

## Publish to GitHub Pages (one-time setup)

1. Create a new **public** repo (e.g. `maximo-mcp-server-docs`) and push the contents of this folder to its `main` branch.
2. In the repo: **Settings → Pages → Build and deployment → Source → "GitHub Actions"**.
3. That's it. Every push to `main` runs `.github/workflows/deploy.yml`, which builds VitePress and deploys the output to Pages. No `gh-pages` branch, no committed build output.

The site will be served at `https://<your-user>.github.io/<repo-name>/`.

### Base path

GitHub Pages serves a project repo under `/<repo-name>/`, so VitePress needs a matching `base`. The workflow sets it automatically:

```yaml
env:
  DOCS_BASE: /${{ github.event.repository.name }}/
```

No manual edit is required as long as the repo name matches the Pages URL. For a **user/org page** (`<user>.github.io`) or a **custom domain**, set `DOCS_BASE=/` (and for a custom domain add `docs/public/CNAME`).

To build locally with the same base the site will use in production:

```bash
DOCS_BASE=/maximo-mcp-server-docs/ npm run docs:build
```

## Alternative: publish from a `gh-pages` branch

If you prefer the classic branch-based flow instead of the GitHub Actions source, replace `deploy.yml` with a step that pushes `docs/.vitepress/dist` to a `gh-pages` branch (e.g. `peaceiris/actions-gh-pages`) and set **Settings → Pages → Source → Deploy from a branch → `gh-pages`**. The GitHub Actions source (default here) is recommended.

## Updating content

The docs are plain Markdown under `docs/`. Edit, commit, push — the workflow redeploys. Update the version label in `docs/.vitepress/config.mts` (the `nav` `v1.2.0` entry) when the package version changes.
