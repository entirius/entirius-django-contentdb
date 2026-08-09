---
title: ContentDB
description: CMS content management module — pages, blog posts, rich content for products and categories.
sidebar:
  label: Overview
  collapsed: true
---

django-contentdb manages CMS page content for the Volkanos platform. It stores structured JSON content (sections and tiles), handles draft/publish workflows, and serves content to storefronts via REST API.

## What It Does

- Stores page content as structured JSON (sections, tiles, ordering)
- Draft/publish workflow with content snapshots
- URL routing via Route model (slug-based)
- Channel-based content scoping (empty = public, assigned = restricted)
- Blog posts with extension fields and categories
- Product and category rich content (linked by SKU, no route)
- Image management with upload API
- Language and channel sync from PIM (optional — standalone mode supported)

## Architecture

```
CMS Blueprint (Vue 3)
  → Admin API (/api-admin/contentdb/v1/)
    → Django Models (Content → Draft → Published → Route)
      → Public API (/api/contentdb/v1/)
        → Storefront Builder (Nuxt 3)
```

Content flows from CMS editor to Django backend to storefront. The CMS creates/edits Drafts, publishes them (creating frozen snapshots), and the storefront reads Published content filtered by route, language, and channel.

## Content Types

| Slug | Purpose | Has Route | Has Extension |
|------|---------|-----------|---------------|
| `static-page` | CMS pages (home, about, contact) | Yes | No |
| `header` | Layout header content | No (special) | No |
| `blog-post` | Blog articles | Yes | Yes (title, excerpt, images) |
| `product-rich-content` | Product detail content | No (linked by SKU) | No |
| `category-rich-content` | Category page content | No (linked by category) | No |

## Key Concepts

**Draft** — The editable version of content. Links to a ContentType, Language, and ContentChannel (M2M).

**Published** — A frozen snapshot of a Draft's content at publish time. Each publish creates a new Content record. The storefront only reads Published content.

**Route** — A URL slug (e.g., `home`, `about`, `welcome-to-entirius`). M2M to Drafts. The storefront resolves slugs to content via the `routes` filter parameter.

**ContentChannel** — Controls which storefronts see the content. Empty channels = public (all storefronts). Assigned channels = restricted. Syncs from PIM or created manually.

## Related Modules

- **[ContentDB Translator](./contentdb-translator/)** — AI translation bridge for ContentDB content

## Next Steps

- [Data model and JSON structure](/volkanos/modules/contentdb/data-model/)
- [Rich content building](https://github.com/entirius/entirius-pwa-cms/blob/develop/docs/rich-content-building.md) — sections, tiles, dyes, configs, and patterns
- [API reference](/volkanos/modules/contentdb/api/)
- [CMS configuration](/volkanos/modules/contentdb/cms-config/)
