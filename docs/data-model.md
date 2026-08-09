---
title: Data Model
description: ContentDB data model — Content, Draft, Published, Route chain and JSON content structure.
---

## Model Chain

```
Content <-- Draft <-- Published
  |           |  M2M       |
  |      ContentChannel  Content (snapshot)
  |           |  M2M
  |         Route
  |
  +-- Category (optional, for blog posts)
```

Empty `Draft.channels` M2M = content is public (visible to all channel filters). Assigning channels restricts content to those channels.

### Content

The core record. Stores JSON content, extension data, and SEO meta.

| Field | Type | Description |
|-------|------|-------------|
| `uid` | UUID | Auto-generated, unique identifier |
| `content` | JSONField | Sections/tiles structure (see below) |
| `extension` | JSONField (nullable) | Blog-specific data (title, excerpt, images) |
| `meta` | JSONField (nullable) | SEO metadata (title, description, og_*) |
| `category` | FK to Category (nullable) | Blog category assignment |

### Draft

Links a ContentType to a Content record. The editable entity.

| Field | Type | Description |
|-------|------|-------------|
| `content_type` | FK to ContentType | Document type (static-page, blog-post, etc.) |
| `content` | OneToOne to Content | The editable content body |
| `name` | CharField(128) | Display name in CMS |
| `language` | FK to Language | Content language (default: pk=1) |
| `channels` | M2M to ContentChannel | Channel scoping. Empty = visible to all channels. |
| `access_rights` | M2M to AccessRights | **Deprecated.** Use `channels` instead. |

### Published

A frozen snapshot. Created each time a Draft is published.

| Field | Type | Description |
|-------|------|-------------|
| `draft` | FK to Draft | Source draft (many Published per Draft) |
| `content` | OneToOne to Content | Snapshot copy of content at publish time |

### Route

URL slug mapping. Links slugs to Drafts via M2M.

| Field | Type | Description |
|-------|------|-------------|
| `url` | CharField(256, unique) | URL slug (e.g., `home`, `about`) |
| `label` | CharField(256) | Display label |
| `placement` | TextChoices (top/bottom) | Navigation placement |
| `drafts` | M2M to Draft | Linked drafts |

`Route` records with `url="home"` or `url="header"` cannot be deleted (protected in model — `delete()` raises `ValidationError`, mapped to HTTP 400 by the DRF exception handler). The `bypass=True` kwarg skips the check.

A `Content` whose `Draft` is attached to one of these routes is deletable as long as another draft still covers the same route — e.g. duplicate `home` drafts across channels. Only the last draft for a protected route is blocked. System content (`Draft.is_system=True`) is always blocked regardless of routes.

### AccessRights (Deprecated)

Replaced by ContentChannel. Kept for backward compatibility during transition.

| Field | Type | Description |
|-------|------|-------------|
| `access_level` | IntegerField (primary_key) | Level number. PK=1 = public |

### Language

| Field | Type | Description |
|-------|------|-------------|
| `iso2` | CharField(2, unique) | ISO 639-1 code (e.g., `EN`, `PL`) |
| `iso3` | CharField(3, unique) | ISO 639-2 code (e.g., `ENG`, `POL`) |
| `name_en` | CharField(64) | Language name in English (e.g., `English`) |
| `name_pl` | CharField(64) | Language name in Polish (e.g., `Angielski`) |

Populated via `sync_languages_from_pim()` or fixtures. See [Language & Channel Unification](/architecture/language-channel-unification/).

### ContentChannel

Mirror of PIM `Channel`. Drives content scoping via `Draft.channels` M2M.

| Field | Type | Description |
|-------|------|-------------|
| `idx` | CharField(unique) | Channel identifier used in API `?channel=` param |
| `name` | CharField | Display name |
| `default_language` | FK to Language (nullable) | Default language for this channel |
| `is_default` | BooleanField | Whether this is the default channel |

Populated via admin "Sync from PIM" action, `python manage.py sync_contentdb_channels`, or created manually for standalone deployments.

## JSON Content Structure

The `content` JSONField on Content uses a sections/tiles architecture with four keys:

```json
{
  "document_configs": {},
  "sections": {
    "section-uuid-1": {
      "core_type": "section-hero-slider",
      "width": "full_width",
      "variant": 1
    },
    "section-uuid-2": {
      "core_type": "section-text",
      "dye": 3,
      "grid_desktop": "2",
      "grid_mobile": "1"
    }
  },
  "tiles": {
    "tile-uuid-1": {
      "core_type": "tile-hero",
      "title": "Welcome",
      "description": "<p>HTML content here</p>",
      "dye": 3,
      "tile_align": "left",
      "images_set": {
        "desktop": { "uid": "...", "image": "url", "width": 1920, "height": 800 },
        "mobile": { "uid": "...", "image": "url", "width": 750, "height": 1000 }
      },
      "custom_buttons": [
        { "label": "Shop now", "url": "/c/furniture", "type": "internal" }
      ]
    },
    "tile-uuid-2": {
      "core_type": "tile-txt-btn",
      "title": "Section Title",
      "description": "<p>Body text</p>"
    }
  },
  "tiles_order": {
    "section-uuid-1": ["tile-uuid-1"],
    "section-uuid-2": ["tile-uuid-2"]
  },
  "sections_order": ["section-uuid-1", "section-uuid-2"]
}
```

### Section Types

All 17 section types. Each available for all document types (static-page, blog-post, product-rich-content, category-rich-content).

| core_type | Label | Section Configs | Typical Tiles |
|-----------|-------|-----------------|---------------|
| `section-hero-slider` | Hero slider | width | tile-hero |
| `section-mini-banner` | Mini banner | width, margin | (images on section) |
| `section-content-slider` | Content slider | dye, grid_mobile, grid_desktop | tile-img-btn |
| `section-product-slider-category` | Product slider (category) | grid | (auto from category) |
| `section-product-slider-via-sku` | Product slider (via sku) | grid | tile-product |
| `section-banner` | Banner | width, tile_align, margin, dye, banner_type | (images on section) |
| `section-image-text` | Image & text | width, margin | tile-image, tile-video, tile-txt-btn |
| `section-image-grid` | Image grid | dye, grid_mobile, grid_desktop | tile-img-btn |
| `section-text` | Text | dye, grid_mobile, grid_desktop | tile-txt-btn |
| `section-accordion` | Accordion | dye | tile-accordion |
| `section-table` | Table | — | tile-text |
| `section-icon-grid` | Icon grid | dye | tile-title-desc-img |
| `section-video` | Video | — | tile-img-btn |
| `section-testimonial` | Testimonial | — | tile-testimonial |
| `section-chart` | Chart | — | tile-chart |
| `section-blog` | Blog | — | (uses blog_section group-field) |
| `section-form` | Form | — | tile-form |

**Section config props:** `variant` (1-4, all sections), `dye` (1-5), `width` (container/full_width), `tile_align` (left/right), `margin` (true/false), `banner_type` (video/banner), `grid` (grid/slider), `grid_mobile`, `grid_desktop`.

### Tile Types

All 13 tile types. Each locked to specific parent sections via variant matching.

| core_type | Label | Parent Sections | Key Props |
|-----------|-------|-----------------|-----------|
| `tile-hero` | Hero tile | hero-slider | title, description, images_set, dye, tile_align, custom_buttons, custom_field, video_url, product_sku |
| `tile-img-btn` | Image + button | content-slider, image-grid, video | images_set, custom_buttons |
| `tile-product` | Product (sku) | product-slider-via-sku | sku |
| `tile-image` | Image | image-text | images_set |
| `tile-video` | Video | image-text | video_field |
| `tile-txt-btn` | Text + button | image-text, text | title, description, dye (image-text only), custom_buttons |
| `tile-accordion` | Tile accordion | accordion | accordion_tile (group-fields) |
| `tile-title-desc-img` | Title + desc + img | icon-grid | title, description, images_set |
| `tile-text` | Text | table | description |
| `tile-testimonial` | Testimonial tile | testimonial | title, description, author, images_set |
| `tile-chart` | Chart tile | chart | title, description, chart_tile (group-fields) |
| `tile-blog-extension` | Tile blog | any (blog-post only) | title, description, images_set, custom_buttons, rating, number_of_reviews |
| `tile-form` | Tile form | form | title, form_type, button_text, header_area, footer_area, form_tile, consents |

**Tile props:** `dye` (1-5), `tile_align` (left/right), `images_set` (desktop/mobile), `custom_buttons` (label/url/type array), `custom_field` (url-key), various group-fields.

See [Rich Content Building](https://github.com/entirius/entirius-pwa-cms/blob/develop/docs/rich-content-building.md) for complete config options, dye system, and patterns.

### Blog Extension

Blog posts (`content_type.slug = "blog-post"`) use the `extension` JSONField:

```json
{
  "title": "Article Title",
  "description": "<p>Short excerpt for listing pages</p>",
  "images_set": {
    "desktop": { "uid": "...", "image": "url", ... }
  }
}
```

### Meta (SEO)

The `meta` JSONField stores SEO data:

```json
{
  "title": "Page Title",
  "description": "Meta description for search engines",
  "og_title": "Open Graph title",
  "og_description": "Open Graph description"
}
```
