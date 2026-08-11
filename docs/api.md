---
title: API Reference
description: ContentDB REST API — public and admin endpoints for content, routes, images, and categories.
---

## Base URLs

- **Public**: `/api/contentdb/v1/`
- **Admin**: `/api-admin/contentdb/v1/` (requires Bearer token)

Response format: `{"meta": {"status": "OK", "message": ""}, "data": [...], "pagination": {...}}`

## Public Endpoints

### Published Content

```
GET /api/contentdb/v1/published/{content_type}/
```

The primary endpoint for storefronts. Returns Content records that have been published, filtered by content type slug.

**URL parameter**: `content_type` — slug of the ContentType (e.g., `static-page`, `blog-post`)

**Query parameters**:

| Param | Type | Description |
|-------|------|-------------|
| `routes` / `routes[]` | string | Filter by route URL slug |
| `language` | string | Filter by language ISO2 (e.g., `EN`, `PL`) |
| `channel` | string | Filter by channel `idx` (e.g., `default`, `de-market`). Returns content scoped to that channel plus unscoped content. |
| `access_rights` / `access_rights[]` | integer | **Deprecated.** Filter by access level (1 = public). Use channel scoping instead. |
| `sort` | string | Sort field (e.g., `-created_at`) |
| `limit` | integer | Page size |
| `page` | integer | Page number |

**Example — fetch homepage**:

```bash
curl "http://localhost:8000/api/contentdb/v1/published/static-page/?routes=home&language=EN&channel=default-europe"
```

**Response**:

```json
{
  "meta": {"status": "OK", "message": ""},
  "data": [
    {
      "uid": "c0000001-0002-4000-8000-000000000002",
      "content": {
        "tiles": { ... },
        "sections": { ... },
        "tiles_order": { ... },
        "sections_order": [ ... ]
      },
      "extension": null,
      "meta": {
        "title": "Home",
        "description": "Welcome to the Entirius demo store"
      }
    }
  ],
  "pagination": {"page": 1, "limit": 6, "pages": 1, "records": 1}
}
```

### Routes

```
GET /api/contentdb/v1/routes/
```

Returns all URL route slugs with their linked drafts.

### Content Types

```
GET /api/contentdb/v1/content-types/
```

Returns available content type definitions (slug, label, is_layout_extender).

### Languages

```
GET /api/contentdb/v1/languages/
```

Returns configured languages (iso2, iso3, name_en, name_pl). Enriched via `sync_languages_from_pim()` or fixtures.

### Channels

```
GET /api/contentdb/v1/channels/
```

Returns configured channels (idx, name, default_language, is_default). Use channel `idx` values as the `channel` query param on the published endpoint.

### Categories

```
GET /api/contentdb/v1/category/
```

Returns blog categories. Filter by `language` query param.

### Images

```
GET /api/contentdb/v1/images/
```

Returns uploaded images with metadata (uid, url, dimensions, tags).

## Admin Endpoints

All public endpoints are available under `/api-admin/contentdb/v1/` with full CRUD. Requires Bearer token from `/api/token/`.

### Image Upload

```
POST /api-admin/contentdb/v1/images/
Content-Type: multipart/form-data
Authorization: Bearer <token>

image: <file>
alt: "Image description"
```

### Draft CRUD

```
GET    /api-admin/contentdb/v1/content/{content_type}/
POST   /api-admin/contentdb/v1/content/{content_type}/
PUT    /api-admin/contentdb/v1/content/{content_type}/{id}/
DELETE /api-admin/contentdb/v1/content/{content_type}/{id}/
```

#### DELETE responses

| Status | When | Body |
|--------|------|------|
| 204 | Draft deleted | empty |
| 400 | Last draft attached to a `home` or `header` route | `{"meta": {"status": "BAD_REQUEST", "status_code": 400, "message": ["invalid"]}, "data": ["Cannot delete the last home page"]}` |
| 400 | Draft has `is_system=true` | `{..., "data": ["Cannot delete system content"]}` |
| 404 | Content or Draft not found | DRF default |

Duplicate `home`/`header` drafts (e.g. one per channel) are deletable as long as at least one other draft shares the route. The protection blocks only the last instance.

### Publish

```
POST /api-admin/contentdb/v1/published/{content_type}/
```

Creates a Published snapshot from the current Draft content.

### Channels

```
GET /api-admin/contentdb/v1/channels/
GET /api-admin/contentdb/v1/channels/{idx}/
```

Read-only list/retrieve for `ContentChannel` records. Channels are managed via the Django admin "Sync from PIM" action or `python manage.py sync_contentdb_channels`. For standalone deployments without PIM, create channels manually in Django admin.

## Storefront Integration

The storefront builder store calls:

```javascript
const { $bma } = useNuxtApp()
const { data } = await $bma.GET._PublishedDocs({
  routes: slug,       // URL slug (default: 'home')
  type: 'static-page', // content type slug
  language: 'EN',      // ISO2 language code
})
const [content] = data
```

The `channel` query param is added automatically from the `DEFAULT_CHANEL` env var via the storefront's `_methods` wrapper. No slug defaults to `home`. The builder caches content by slug.
