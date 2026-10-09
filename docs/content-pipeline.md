---
title: Content Pipeline
description: ContentDB content pipeline (Content → Draft → Published → Route) and image handling.
---

## Pipeline

```
Content (UUID pk, JSON blob: {tiles, sections, tiles_order, sections_order})
  → Draft (links ContentType + Content + Language + ContentChannel M2M)
    → Published (immutable snapshot of Draft + Content)
      → Route (URL path, M2M→Draft, placement: top|bottom)
```

- **ContentType** defines the template: `static-page`, `header`, `blog-post`, `product-rich-content`, `category-rich-content`
- **ContentType.is_layout_extender** = true → header type (separate API routes)
- **ContentType.supports_authors** = true → enables author picker in the CMS (only `blog-post` by default)
- **Author** — author profiles with name, slug, role/bio/tag translations, photo, contacts, social links
- **DraftAuthor / DraftCoAuthor** — through-tables linking Draft ↔ Author with position ordering
- **ContentChannel** — local mirror of PIM Channel (idx↑, name, default_language FK, is_default). Syncs from PIM via admin action or management command. Empty `Draft.channels` M2M = content is public (all channels).
- **AccessRights** — DEPRECATED. Replaced by ContentChannel. Kept for backward compatibility during transition.
- Content/Route `delete()` prevents deletion of `home` and `header` records

## Image Handling

- **HashedImageField** — SHA256 content-addressed storage: `aa/bb/cccccccc...{ext}`
- **Auto-resize** on upload: max width = `CONTENTDB_IMAGE_MAX_WIDTH` (default 2560)
- **Thumbnail** model: unique per (method, source, width, height)
- **Deduplication**: same file content → same hash → same path (no duplicates)
- Uses `image_transformations` library with PIL fallback
