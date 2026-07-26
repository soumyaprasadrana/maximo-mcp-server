import { defineConfig } from "vitepress";

// ─────────────────────────────────────────────────────────────────────────────
// IMPORTANT — GitHub Pages base path
// For a PROJECT page the site is served at https://<user>.github.io/<repo>/,
// so `base` MUST equal "/<repo-name>/" (with leading & trailing slash).
// Override at build time without editing this file:  DOCS_BASE=/my-repo/ npm run docs:build
// Use "/" for a user/org page (<user>.github.io) or a custom domain (CNAME).
// ─────────────────────────────────────────────────────────────────────────────
const base = process.env.DOCS_BASE ?? "/maximo-mcp-server/";

const REPO = "https://github.com/soumyaprasadrana/maximo-mcp-server";
const NPM = "https://www.npmjs.com/package/@soumyaprasadrana/maximo-mcp-server";

export default defineConfig({
  base,
  lang: "en-US",
  title: "Maximo MCP Server",
  description:
    "Enterprise MCP server for IBM Maximo — metadata-aware query building and a staged Working Set transaction model for AI agents.",
  cleanUrls: true,
  lastUpdated: true,
  ignoreDeadLinks: true,

  head: [
    ["meta", { name: "theme-color", content: "#3c7eff" }],
    // SEO Meta Tags
    ["meta", { name: "viewport", content: "width=device-width, initial-scale=1.0" }],
    ["meta", { name: "keywords", content: "Maximo, MCP, OSLC, IBM, query builder, working set, AI agent, OAuth" }],
    ["meta", { name: "author", content: "Soumya Prasad Rana" }],
    ["meta", { name: "description", content: "Enterprise MCP server for IBM Maximo — metadata-aware query building and staged Working Set transactions for AI agents" }],
    // Open Graph / Social Media
    ["meta", { property: "og:type", content: "website" }],
    ["meta", { property: "og:title", content: "Maximo MCP Server — Enterprise AI Integration" }],
    ["meta", {
      property: "og:description",
      content: "Governed AI-agent access to IBM Maximo: metadata discovery, validated OSLC queries, and staged preview/commit changes.",
    }],
    ["meta", { property: "og:url", content: "https://soumyaprasadrana.github.io/maximo-mcp-server" }],
    ["meta", { property: "og:site_name", content: "Maximo MCP Server" }],
    // Twitter Card
    ["meta", { name: "twitter:card", content: "summary_large_image" }],
    ["meta", { name: "twitter:title", content: "Maximo MCP Server" }],
    ["meta", { name: "twitter:description", content: "Metadata-aware OSLC queries and Working Set transactions for Maximo AI agents" }],
    // Canonical URL
    ["link", { rel: "canonical", href: "https://soumyaprasadrana.github.io/maximo-mcp-server" }],
    // Robots
    ["meta", { name: "robots", content: "index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1" }],
    // Language alternatives
    ["link", { rel: "alternate", hreflang: "en", href: "https://soumyaprasadrana.github.io/maximo-mcp-server" }],
  ],

  themeConfig: {
    logo: undefined,
    outline: { level: [2, 3], label: "On this page" },

    nav: [
      { text: "Guide", link: "/guide/introduction", activeMatch: "/guide/" },
      { text: "Concepts", link: "/concepts/working-set", activeMatch: "/concepts/" },
      { text: "Tools", link: "/tools/", activeMatch: "/tools/" },
      { text: "Recipes", link: "/recipes/", activeMatch: "/recipes/" },
      {
        text: "v1.2.0",
        items: [
          { text: "npm package", link: NPM },
          { text: "Changelog / Releases", link: `${REPO}/releases` },
          { text: "Report an issue", link: `${REPO}/issues` },
        ],
      },
    ],

    sidebar: {
      "/guide/": [
        {
          text: "Getting Started",
          items: [
            { text: "Introduction", link: "/guide/introduction" },
            { text: "Installation & Setup", link: "/guide/getting-started" },
            { text: "Configuration Reference", link: "/guide/configuration" },
            { text: "Connecting Clients", link: "/guide/clients" },
          ],
        },
      ],
      "/concepts/": [
        {
          text: "Core Concepts",
          items: [
            { text: "Metadata Engine", link: "/concepts/metadata-engine" },
            { text: "Working Set Model", link: "/concepts/working-set" },
            { text: "Child Records", link: "/concepts/child-records" },
            { text: "Security & Audit", link: "/concepts/security-audit" },
          ],
        },
      ],
      "/tools/": [
        {
          text: "Tool Reference",
          items: [{ text: "All Tools", link: "/tools/" }],
        },
      ],
      "/recipes/": [
        {
          text: "Recipes",
          items: [{ text: "Orchestration Patterns", link: "/recipes/" }],
        },
      ],
    },

    socialLinks: [{ icon: "github", link: REPO }],

    search: { provider: "local" },

    editLink: {
      pattern:
        "https://github.com/soumyaprasadrana/maximo-mcp-server-docs/edit/main/docs/:path",
      text: "Edit this page on GitHub",
    },

    footer: {
      message: "Released under the package LICENSE.",
      copyright: "© Soumya Prasad Rana",
    },
  },
});
