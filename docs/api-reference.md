---
title: API Reference
description: Complete endpoint reference for the django-contentdb Admin and Public APIs.
---

## Overview

django-contentdb exposes two API families: an **Admin API** (authenticated, full CRUD) and a
**Public API** (unauthenticated, read-only). Both use the same URL structure; only the base path
and available HTTP methods differ.

Default base paths (configurable via Django settings):

| API family | Base path | Setting |
|------------|-----------|---------|
| Admin | `/api-admin/contentdb/{version}/` | `API_ADMIN_BASE_URL` |
| Public | `/api/contentdb/{version}/` | `API_PUBLIC_BASE_URL` |

`{version}` is a free-form path segment (e.g. `v1`). It is not validated -- any string is
accepted. The canonical version string in production is `v1`.

---

## Response Format

Every response, including errors, is wrapped in the same envelope.

### Success (non-paginated)

```json
{
  "meta": {
    "status": "OK",
    "message": ""
  },
  "data": <object or array>
}
```

### Success (paginated list)

```json
{
  "meta": {
    "status": "OK",
    "message": ""
  },
  "data": [<objects>],
  "pagination": {
    "page": 1,
    "limit": 6,
    "pages": 10,
    "records": 57
  }
}
```

`content_type` is appended to Draft and Published list responses at the top level:

```json
{
  "meta": {...},
  "data": [...],
  "pagination": {...},
  "content_type": "static-page"
}
```

### Write operation status codes

| Action | `meta.status` | HTTP status |
|--------|--------------|-------------|
| List, Retrieve | `OK` | 200 |
| Create | `CREATED` | 201 |
| Update | `UPDATED` | 200 |
| Delete | `DELETED` | 204 |

### Error responses

```json
{
  "meta": {
    "status": "BAD_REQUEST",
    "status_code": 400,
    "message": <error codes from DRF>
  },
  "data": <DRF error detail>
}
```

| HTTP status | `meta.status` |
|-------------|--------------|
| 400 | `BAD_REQUEST` |
| 401 | `UNAUTHORIZED` |
| 403 | `FORBIDDEN` |
| 404 | `NOT_FOUND` |
| 500 | `ERR` (with message `"Server Error"`) |

---

## Authentication and Permissions

### Admin API

**Authentication class:** `DjangoAuth` -- a subclass of DRF `TokenAuthentication` that delegates to
`django.contrib.auth.authenticate`. In the Volkanos stack this resolves JWT tokens via the
`django-utils` package (`JWTException` is translated to `NotAuthenticated`).

**Default permission class:** `IsAuthenticated`

**Draft/Published endpoints additionally require:** `IsAuthenticated & (IsAdminUser | ContentTypePermission)`

The combined requirement means:
- The user must be authenticated, AND
- The user must be a Django staff/superuser (`IsAdminUser`), OR must have an explicit
  `ContentTypePermission` row granting the specific action on the requested `content_type` slug.

### ContentTypePermission -- action mapping

`ContentTypePermission` reads `view.action` and maps it to an `Action` enum value, then checks
whether a `ContentTypePermission` row exists for the current user (or any of their groups) and
the `content_type` slug taken from URL kwargs.

| ViewSet action | Required `Action` |
|---------------|------------------|
| `list` | `VIEW` |
| `retrieve` | `VIEW` |
| `create` | `CREATE` |
| `update` | `UPDATE` |
| `destroy` | `DELETE` |
| `published` (GET) | `PUBLISH` |
| `published_create` (POST) | `PUBLISH` |
| `published_delete` (DELETE) | `DELETE` |

Superusers bypass `ContentTypePermission` and always have access.

### Public API

**Authentication class:** none (empty list)

**Permission class:** `AllowAny`

No credentials are required. All public endpoints are read-only (list + retrieve).

---

## Pagination

**Class:** `StandardPagination` (subclass of DRF `PageNumberPagination`)

| Parameter | Query param | Default | Maximum |
|-----------|-------------|---------|---------|
| Page number | `page` | 1 | -- |
| Page size | `limit` | 6 | 100 |

`RouteViewSet` (admin) has no `pagination_class` set -- returns unpaginated results.
`RORouteViewSet` (public) similarly has no `pagination_class`.

---

## Sorting

Where a ViewSet declares `available_sorting_fields`, the caller passes one or more field names
via the `sort` query parameter (comma-separated or repeated). Prefix with `-` for descending.

Sorting is validated against the declared list; unknown sort values are silently ignored.

The `PublishedSortMixin` translates the user-visible `created_at` / `-created_at` sort tokens to
the ORM path `published__draft__created_at` / `-published__draft__created_at` transparently.

---

## Admin API Endpoints

Base: `/{ADMIN_BASE_URL}/contentdb/{version}/`

Default: `/api-admin/contentdb/v1/`

---

### Attributes

**URL:** `attributes/`
**Lookup:** `slug` (string)
**Lookup URL:** `attributes/{slug}/`
**Methods:** GET (list), GET (retrieve), POST (create), PUT (update), PATCH (partial update), DELETE
**Auth:** DjangoAuth + IsAuthenticated
**Filter class:** `AttributeFilter`
**Pagination:** StandardPagination (default 6, max 100)
**Default order:** `-created_at`

#### Serializer fields -- AttributeSerializer

| Field | Type | R/W | Description |
|-------|------|-----|-------------|
| `slug` | string | R+W | URL-safe unique identifier |
| `label` | string | R+W | Human-readable display name |
| `attribute_set` | string (slug) | R+W | Slug of the owning AttributeSet |
| `filter_values` | array of values | R | Non-text filterable values from AttributeValue set |
| `is_filterable` | boolean | R+W | Whether this attribute appears in filter panels |
| `is_searchable` | boolean | R+W | Whether this attribute is included in full-text search |
| `is_comparable` | boolean | R+W | Whether sorting by this attribute is supported |
| `allow_new_values` | boolean | R+W | Whether new AttributeValues can be created on assignment |
| `allow_many_values` | boolean | R+W | Whether multiple values can be assigned per content item |
| `is_bool` | boolean | R+W | Value type flag: boolean |
| `is_int` | boolean | R+W | Value type flag: integer |
| `is_txt` | boolean | R+W | Value type flag: short text |
| `is_txt_long` | boolean | R+W | Value type flag: long text |
| `is_datetime` | boolean | R+W | Value type flag: datetime |
| `type` | string | R | Derived type name (`type_as_str`): `bool`, `int`, `txt`, `txt_long`, `datetime` |
| `created_at` | datetime | R | ISO 8601 creation timestamp |
| `updated_at` | datetime | R | ISO 8601 last-updated timestamp |

#### Filters -- AttributeFilter

| Parameter | Type | Description |
|-----------|------|-------------|
| `attribute_set` | string (slug) | Filter by AttributeSet slug. Accepts multiple values. |
| `attribute_set[]` | string (slug) | Alternate bracket notation for multi-value |

---

### Attribute Values (nested)

**URL:** `attributes/{attribute_slug}/values/`
**Lookup:** `pk` (integer)
**Lookup URL:** `attributes/{attribute_slug}/values/{pk}/`
**Methods:** GET (list), GET (retrieve), POST (create), PUT (update), PATCH (partial update), DELETE
**Auth:** DjangoAuth + IsAuthenticated
**Pagination:** StandardPagination
**Default order:** `-created_at`

The queryset is filtered to values belonging to the attribute identified by `{attribute_slug}`.
Returns 404 if the attribute slug does not exist.

#### Serializer fields -- AttributeValueSerializer

| Field | Type | R/W | Description |
|-------|------|-----|-------------|
| `id` | integer | R | Primary key |
| `value` | any | R+W | Typed value; type determined by the parent Attribute's type flags |

On write, the incoming `value` is parsed according to the parent attribute's type
(`parse_value`), then stored in the appropriate typed column (`value_bool`, `value_int`,
`value_txt`, `value_txt_long`, `value_datetime`). Create uses `get_or_create` -- creating a
duplicate value returns the existing record without error.

---

### Attribute Sets

**URL:** `attribute-sets/`
**Lookup:** `slug` (string)
**Lookup URL:** `attribute-sets/{slug}/`
**Methods:** GET (list), GET (retrieve), POST (create), PUT (update), PATCH (partial update), DELETE
**Auth:** DjangoAuth + IsAuthenticated
**Pagination:** StandardPagination
**Default order:** `-created_at`

#### Serializer fields -- AttributeSetSerializer

| Field | Type | R/W | Description |
|-------|------|-----|-------------|
| `slug` | string | R+W | URL-safe unique identifier |
| `label` | string | R+W | Human-readable display name |
| `attributes` | array of strings (slugs) | R+W | Attribute slugs belonging to this set |

---

### Content Types

**URL:** `content-types/`
**Lookup:** `slug` (string)
**Lookup URL:** `content-types/{slug}/`
**Methods:** GET (list), GET (retrieve), POST (create), PUT (update), PATCH (partial update), DELETE
**Auth:** DjangoAuth + IsAuthenticated
**Pagination:** StandardPagination
**Default order:** `-created_at`

Queryset is filtered to `is_layout_extender=False` (standard content types only).
Layout extender types use the `layout-extender-types/` endpoints.

#### Serializer fields -- ContentTypeSerializer

| Field | Type | R/W | Description |
|-------|------|-----|-------------|
| `slug` | string | R+W | URL-safe unique identifier |
| `label` | string | R+W | Human-readable display name |
| `attribute_set` | string (slug) | R+W | Slug of the associated AttributeSet |
| `attributes` | array of objects | R | Attributes from the linked AttributeSet (expanded inline) |
| `is_layout_extender` | boolean | R+W | True for header/layout types; False for standard content types |

Each element of `attributes`:

| Subfield | Type | Description |
|----------|------|-------------|
| `slug` | string | Attribute slug |
| `lable` | string | Attribute label (note: typo in source -- field name is `lable`) |
| `type` | string | Type string (`bool`, `int`, `txt`, `txt_long`, `datetime`) |
| `is_filterable` | boolean | Filterable flag |
| `is_searchable` | boolean | Searchable flag |
| `is_comparable` | boolean | Comparable (sortable) flag |
| `allow_new_values` | boolean | New value creation allowed |
| `allow_many_values` | boolean | Multiple values allowed |

---

### Layout Extender Types

**URL:** `layout-extender-types/`
**Lookup:** `slug` (string)
**Lookup URL:** `layout-extender-types/{slug}/`
**Methods:** GET (list), GET (retrieve), POST (create), PUT (update), PATCH (partial update), DELETE
**Auth:** DjangoAuth + IsAuthenticated
**Pagination:** StandardPagination
**Default order:** `-created_at`

Identical to Content Types but queryset is filtered to `is_layout_extender=True`. Uses
`ContentTypeSerializer` (same fields).

---

### Routes

**URL:** `routes/`
**Lookup:** `url` (string)
**Lookup URL:** `routes/{url}/`
**Methods:** GET (list), GET (retrieve), POST (create), PUT (update), PATCH (partial update), DELETE
**Auth:** DjangoAuth + IsAuthenticated
**No pagination** (no `pagination_class` -- returns full list)
**Default order:** `url` (ascending)
**Queryset:** Excludes routes with empty `label`
**Filter class:** `RouteFilter`

#### Serializer fields -- RouteSerializer

| Field | Type | R/W | Description |
|-------|------|-----|-------------|
| `url` | string | R+W | URL path (unique identifier, e.g. `home`, `about-us`) |
| `label` | string | R+W | Display label |
| `placement` | string | R+W | `top` or `bottom` -- controls navigation placement |
| `draft` | string | R | String representation of the linked Draft (read-only, nullable) |

#### Filters -- RouteFilter

| Parameter | Type | Description |
|-----------|------|-------------|
| `placement` | string | Exact match: `top` or `bottom` |

---

### Content Sets

**URL:** `content-sets/`
**Lookup:** `uid` (UUID)
**Lookup URL:** `content-sets/{uid}/`
**Methods:** GET (list), GET (retrieve), POST (create), PUT (update), PATCH (partial update), DELETE
**Auth:** DjangoAuth + IsAuthenticated
**Pagination:** StandardPagination
**Default order:** `-created_at`
**Queryset:** Only ContentSets whose members have `is_layout_extender=False`
**Filter class:** `ContentSetFilter`

#### Serializer fields -- ContentSetSerializer

| Field | Type | R/W | Description |
|-------|------|-----|-------------|
| `uid` | UUID string | R | Unique identifier |
| `members` | array of objects | R+W | Draft members in this set |

Each member object:

| Subfield | Type | R/W | Description |
|----------|------|-----|-------------|
| `name` | string | R | Draft name |
| `draft` | UUID string | R+W | Content UUID of the linked Draft |
| `language` | string | R | ISO 2-letter language code |

On write, `members` is a list of `{"draft": "<content-uid>"}` objects. The serializer resolves
each UUID to a Draft and associates it with the ContentSet. Updating replaces all members.

#### Filters -- ContentSetFilter

| Parameter | Type | Description |
|-----------|------|-------------|
| `content_type` | string (slug) | Filter sets by member content type slug |

---

### Layout Extender Sets

**URL:** `layout-extender-sets/`
**Lookup:** `uid` (UUID)
**Lookup URL:** `layout-extender-sets/{uid}/`
**Methods:** GET (list), GET (retrieve), POST (create), PUT (update), PATCH (partial update), DELETE
**Auth:** DjangoAuth + IsAuthenticated
**Pagination:** StandardPagination
**Default order:** `-created_at`
**Queryset:** Only ContentSets whose members have `is_layout_extender=True`

Same serializer and filters as Content Sets.

---

### Content (Drafts)

**URL:** `content/{content_type}/`
**Lookup:** `uid` (UUID)
**Lookup URL:** `content/{content_type}/{uid}/`
**Methods:** GET (list), GET (retrieve), POST (create), PUT (update), PATCH (partial update), DELETE
**Auth:** DjangoAuth + IsAuthenticated & (IsAdminUser | ContentTypePermission)
**Pagination:** StandardPagination
**Default order:** (model default)
**Filter class:** `DraftFilter`

`{content_type}` is the slug of a ContentType with `is_layout_extender=False`. Returns 404 if
the slug does not match an existing ContentType.

List response includes a top-level `content_type` key with the ContentType slug.

#### Serializer fields -- DraftContentSerializer

Extends `ContentSerializer` with draft-specific fields.

| Field | Type | R/W | Description |
|-------|------|-----|-------------|
| `uid` | UUID string | R | Content unique identifier |
| `content` | JSON object | R+W | Page builder payload: `{tiles, sections, tiles_order, sections_order}` |
| `category` | object or null | R+W | Category reference (`{uid, name, url_key, language}` on read; `uid` string or object with `uid` on write) |
| `meta` | JSON object | R+W | Arbitrary metadata dictionary |
| `attributes` | JSON object | R+W | Attribute values as `{slug: value}` or `{slug: [values]}` map |
| `has_extension` | boolean | R | True if `extension` is a non-empty object |
| `extension` | JSON object or null | R+W | Extra content blob (optional) |
| `created_at` | datetime | R | ISO 8601 creation timestamp |
| `updated_at` | datetime | R | ISO 8601 last-updated timestamp |
| `content_set` | UUID string or null | R | UID of the ContentSet this draft belongs to (if any) |
| `content_set_members` | object | R | Map of language → `{uid, routes}` for all members in the same ContentSet |
| `content_type` | string (slug) | R | ContentType slug |
| `language` | string (ISO2) or null | R+W | Language code (e.g. `en`, `pl`); nullable |
| `name` | string | R+W | Human-readable draft name |
| `routes` | array of strings | R+W | Route URLs assigned to this draft |
| `access_rights` | array of integers | R+W | `access_level` values (integers, e.g. `[1]` for public) |
| `is_published` | boolean | R | True if at least one Published version exists for this draft |
| `is_up_to_date` | boolean | R | True if the latest Published content matches the current Draft content |

**Attribute validation:** On write, each attribute slug in the `attributes` map must belong to
the ContentType's AttributeSet. Values must parse to the correct type. If `allow_new_values` is
false, the value must already exist in `AttributeValue`. If `allow_many_values` is false, only a
scalar (not an array) is accepted.

**Route write behavior:** Routes are resolved by URL string. If a Route with the given URL does
not exist, `CreateableSlugRelatedField` creates it on-the-fly.

#### Filters -- DraftFilter (extends ContentFilter)

**Inherited from ContentFilter:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `created_at` | datetime | Exact match |
| `created_at__gt` | datetime | Greater than |
| `created_at__lt` | datetime | Less than |
| `updated_at` | datetime | Exact match |
| `updated_at__gt` | datetime | Greater than |
| `updated_at__lt` | datetime | Less than |
| `category` | UUID | Filter by Category UID |
| `category_url_key` | string | Filter by Category URL key |
| `{attribute_slug}` | string | Per-attribute value filter (dynamic, generated from ContentType's AttributeSet) |
| `order-by` | string | Order by comparable attribute value (prefix with `-` for descending) |
| `search` | string | Full-text search across searchable text attributes (case-insensitive contains) |

**Added by DraftFilter:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `access_rights` | integer | Filter by access level. Accepts multiple values. |
| `access_rights[]` | integer | Bracket notation alias |
| `routes` | string (URL) | Filter by assigned Route URL. Accepts multiple values. |
| `routes[]` | string (URL) | Bracket notation alias |
| `language` | string (ISO2) | Filter by language code (single value) |

#### Custom action: Publish (POST)

**URL:** `content/{content_type}/{uid}/published/`
**Method:** POST
**Permission required:** ContentTypePermission action `PUBLISH` (or IsAdminUser)

Creates a new immutable Published snapshot from the specified Draft. The Published record links
the newly created Content snapshot to the Draft.

Request body: same shape as `ContentSerializer` (the snapshot content). The `draft_uid` is taken
from the URL path (`{uid}`), not the request body.

Response (201):

```json
{
  "meta": {"status": "CREATED", "message": ""},
  "data": <PublishedContentSerializer>
}
```

An `ActivityLog` entry with `action=PUBLISH` is created on success.

#### Custom action: Unpublish (DELETE)

**URL:** `content/{content_type}/{uid}/published/`
**Method:** DELETE
**Permission required:** ContentTypePermission action `DELETE` (or IsAdminUser)

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `all` | `true` / `True` | false | If true, deletes all Published versions; otherwise deletes only the latest |

Response (204):

```json
{
  "meta": {
    "status": "DELETED",
    "message": ""
  },
  "data": {
    "deleted_uid": ["<uuid>", ...],
    "error_uid": []
  }
}
```

If some deletes fail, `meta.status` is `"ERROR"` and `error_uid` lists the failed UIDs.

A `Deleted` record and `ActivityLog` entry with `action=DELETE` are created for each deleted
Published.

#### Custom action: List Published versions (GET)

**URL:** `content/{content_type}/{uid}/published/`
**Method:** GET
**Permission required:** ContentTypePermission action `PUBLISH` (or IsAdminUser)

Returns all Published snapshots for the given Draft, ordered by `-published__created_at` (newest
first). Paginated with `StandardPagination`. Each item uses `PublishedContentSerializer`.

---

### Layout Extender (Drafts)

**URL:** `layout-extender/{content_type}/`
**Lookup URL:** `layout-extender/{content_type}/{uid}/`
**Methods:** GET (list), GET (retrieve), POST (create), PUT (update), PATCH (partial update), DELETE
**Auth:** DjangoAuth + IsAuthenticated & (IsAdminUser | ContentTypePermission)

Identical to Content (Drafts) but `get_content_type()` resolves ContentTypes with
`is_layout_extender=True`. Same serializer, same filters, same publish/unpublish actions.

---

### Published Content (Admin read-only)

**URL:** `published/{content_type}/`
**Lookup:** `uid` (UUID)
**Lookup URL:** `published/{content_type}/{uid}/`
**Methods:** GET (list), GET (retrieve)
**Auth:** DjangoAuth + IsAuthenticated
**Pagination:** StandardPagination
**Filter class:** `PublishedFilter`
**Sorting fields:** `published__draft__created_at`, `updated_at`
**Default sort:** `-published__draft__created_at` (newest Draft first)

The queryset returns only the **latest** Published snapshot per Draft (deduplication via
`MAX(id)` subquery grouped by `published__draft`).

List response includes a top-level `content_type` key.

#### Custom action: Get Draft for Published (GET)

**URL:** `published/{content_type}/{uid}/draft/`
**Method:** GET

Returns the Draft content (using `PublishedContentSerializer`) that owns the specified Published
record.

Response:

```json
{
  "meta": {"status": "OK", "message": ""},
  "data": <PublishedContentSerializer>
}
```

#### Serializer fields -- PublishedContentSerializer

Extends `ContentSerializer` with publication-context fields.

| Field | Type | R/W | Description |
|-------|------|-----|-------------|
| `uid` | UUID string | R | Content unique identifier |
| `content` | JSON object | R+W | Page builder payload |
| `category` | object or null | R+W | Category reference |
| `meta` | JSON object | R+W | Arbitrary metadata dictionary |
| `attributes` | JSON object | R+W | Attribute values map |
| `has_extension` | boolean | R | True if extension is non-empty |
| `extension` | JSON object or null | R+W | Extra content blob |
| `created_at` | datetime | R | Derived from `published.draft.created_at` (Draft creation time, not Published) |
| `updated_at` | datetime | R | ISO 8601 last-updated timestamp |
| `content_set` | UUID string or null | R | UID of the ContentSet (if any) |
| `content_set_members` | object | R | Map of language → `{uid, routes}` for co-members in the same ContentSet (published versions only) |
| `content_type` | string (slug) | R | ContentType slug |
| `language` | string (ISO2) | R | Language code from the Draft |
| `name` | string | R | Draft name |
| `routes` | array of strings | R | Route URLs from the Draft |
| `access_rights` | array of integers | R | `access_level` values from the Draft |

#### Filters -- PublishedFilter (extends ContentFilter)

**Inherited from ContentFilter:** (same as DraftFilter, minus draft-specific ORM paths)

| Parameter | Type | Description |
|-----------|------|-------------|
| `created_at` | datetime | Exact match |
| `created_at__gt` | datetime | Greater than |
| `created_at__lt` | datetime | Less than |
| `updated_at` | datetime | Exact match |
| `updated_at__gt` | datetime | Greater than |
| `updated_at__lt` | datetime | Less than |
| `category` | UUID | Filter by Category UID |
| `category_url_key` | string | Filter by Category URL key |
| `{attribute_slug}` | string | Per-attribute value filter (dynamic) |
| `order-by` | string | Order by comparable attribute value |
| `search` | string | Full-text search across searchable text attributes |

**Added by PublishedFilter:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `access_rights` | integer | Filter by access level. Accepts multiple values. |
| `access_rights[]` | integer | Bracket notation alias |
| `routes` | string (URL) | Filter by Route URL. Accepts multiple values. |
| `routes[]` | string (URL) | Bracket notation alias |
| `language` | string (ISO2) | Filter by language code (single value) |

#### Sorting -- Published (Admin)

| Sort value | Description |
|------------|-------------|
| `published__draft__created_at` | Sort by Draft creation time (ascending) |
| `-published__draft__created_at` | Sort by Draft creation time (descending, default) |
| `updated_at` | Sort by Content last-updated (ascending) |
| `-updated_at` | Sort by Content last-updated (descending) |

---

### Layout Extender Published (Admin read-only)

**URL:** `layout-extender-published/{content_type}/`
**Lookup URL:** `layout-extender-published/{content_type}/{uid}/`
**Methods:** GET (list), GET (retrieve)
**Auth:** DjangoAuth + IsAuthenticated

Identical to Published Content but queryset additionally filters for
`published__draft__content_type__is_layout_extender=True`. Same serializer, same filters, same
sorting.

---

### Images

**URL:** `images/`
**Lookup:** `uid` (UUID)
**Lookup URL:** `images/{uid}/`
**Methods:** GET (list), GET (retrieve), POST (create), PUT (update), PATCH (partial update), DELETE
**Auth:** DjangoAuth + IsAuthenticated
**Pagination:** StandardPagination
**Filter class:** `ImageFilter`

On create, a `tags` list is accepted; `ImageTag` records are created with `get_or_create`.
After creation, `optimize_image` is called asynchronously (Celery task) to generate thumbnails.

On update, `tags` is optional -- omitting it leaves existing tags unchanged. Providing `tags`
replaces all existing tags. Providing `image` updates the image file; omitting it keeps the
current image.

The image file is stored via `HashedImageField`: the file is optionally resized to
`CONTENTDB_IMAGE_MAX_WIDTH` (default 2560px, width-preserving aspect ratio), then stored at a
path derived from the SHA256 hash of the processed content
(`{hash[0:2]}/{hash[2:4]}/{hash[4:]}{ext}`). Uploading the same image twice results in one file
on disk.

#### Serializer fields -- ImageSerializer

| Field | Type | R/W | Description |
|-------|------|-----|-------------|
| `uid` | UUID string | R | Unique identifier |
| `image` | file (Base64 or multipart) | W | Image file; accepts Base64-encoded data URI or multipart file upload |
| `width` | integer | R | Image width in pixels (populated after save) |
| `height` | integer | R | Image height in pixels (populated after save) |
| `set` | array of objects | R | Thumbnail source set for this image |
| `tags` | array of objects | R+W | Tags associated with the image |
| `meta` | JSON object | R+W | Arbitrary metadata dictionary |
| `created_at` | datetime | R | ISO 8601 creation timestamp |
| `updated_at` | datetime | R | ISO 8601 last-updated timestamp |

`set` elements:

| Subfield | Type | Description |
|----------|------|-------------|
| `source` | string (URL) | Absolute URL to the thumbnail file |
| `width` | integer | Thumbnail width in pixels |
| `height` | integer | Thumbnail height in pixels |

`tags` elements use `ImageTagSerializer`:

| Subfield | Type | R/W | Description |
|----------|------|-----|-------------|
| `slug` | string | R+W | Tag slug (uniqueness validation is disabled -- `get_or_create` is used) |
| `label` | string | R+W | Tag display name |

#### Filters -- ImageFilter

| Parameter | Type | Description |
|-----------|------|-------------|
| `created_at` | datetime | Exact match |
| `created_at__gt` | datetime | Greater than |
| `created_at__lt` | datetime | Less than |
| `updated_at` | datetime | Exact match |
| `updated_at__gt` | datetime | Greater than |
| `updated_at__lt` | datetime | Less than |
| `tags` | string (slug) | Filter by image tag slug. Accepts multiple values. |
| `tags[]` | string (slug) | Bracket notation alias |

---

### Image Tags

**URL:** `image-tags/`
**Lookup:** `slug` (string)
**Lookup URL:** `image-tags/{slug}/`
**Methods:** GET (list), GET (retrieve), POST (create), PUT (update), PATCH (partial update), DELETE
**Auth:** DjangoAuth + IsAuthenticated
**Pagination:** StandardPagination
**Default order:** `slug` (ascending)

#### Serializer fields -- ImageTagSerializer

| Field | Type | R/W | Description |
|-------|------|-----|-------------|
| `slug` | string | R+W | URL-safe unique identifier |
| `label` | string | R+W | Human-readable display name |

---

### Languages

**URL:** `languages/`
**Lookup:** `iso2` (string)
**Lookup URL:** `languages/{iso2}/`
**Methods:** GET (list), GET (retrieve)
**Auth:** DjangoAuth + IsAuthenticated
**Pagination:** StandardPagination
**Default order:** `-iso2`

Admin Language endpoint is read-only (`ROContentDBModelViewSet`) despite being in the admin
router. No create/update/delete is exposed.

#### Serializer fields -- LanguageSerializer

| Field | Type | R/W | Description |
|-------|------|-----|-------------|
| `iso2` | string | R | ISO 639-1 two-letter code (e.g. `en`, `pl`) |
| `iso3` | string | R | ISO 639-2 three-letter code (e.g. `eng`, `pol`) |

---

### Categories

**URL:** `category/`
**Lookup:** `uid` (UUID)
**Lookup URL:** `category/{uid}/`
**Methods:** GET (list), GET (retrieve), POST (create), PUT (update), PATCH (partial update), DELETE
**Auth:** DjangoAuth + IsAuthenticated
**Pagination:** StandardPagination
**Default order:** `-created_at`

**Query parameters (not filter class -- inline `get_queryset`):**

| Parameter | Type | Description |
|-----------|------|-------------|
| `language` | string (ISO2) | Filter by language. Returns all if omitted. |

#### Serializer fields -- CategorySerializer

| Field | Type | R/W | Description |
|-------|------|-----|-------------|
| `uid` | UUID string | R | Unique identifier (auto-generated) |
| `name` | string | R+W | Category display name |
| `url_key` | string | R+W | URL-safe key (auto-generated from `name` if not provided) |
| `language` | string (ISO2) | R+W | Language code; resolved to a Language instance on write |
| `published_posts_count` | integer | R | Count of published content items in this category (filtered by `access_rights` if provided) |

---

### Content Permissions (Function View)

**URL:** `content-permissions/`
**Method:** GET
**Auth:** DjangoAuth + IsAuthenticated
**No pagination**

Returns the set of content type permissions for the current user. Superusers receive all
permissions for all ContentTypes. Regular users receive only their explicitly granted permissions
(from `ContentTypePermission` rows for their user or any of their groups).

Response:

```json
{
  "meta": {"status": "OK", "message": ""},
  "data": [
    {
      "slug": "static-page",
      "label": "Static Page",
      "actions": ["create", "update", "delete", "publish", "view"]
    }
  ]
}
```

`actions` values correspond to `Action` enum: `create`, `update`, `delete`, `publish`, `view`.

---

### Layout Extender Permissions (Function View)

**URL:** `layout-extender-permissions/`
**Method:** GET
**Auth:** DjangoAuth + IsAuthenticated
**No pagination**

Same as Content Permissions but filtered to ContentTypes with `is_layout_extender=True`. For
non-superusers, the `ContentTypePermission` queryset is additionally filtered by
`content_type__is_layout_extender=True`.

Response shape is identical to Content Permissions.

---

## Public API Endpoints

Base: `/{PUBLIC_BASE_URL}/contentdb/{version}/`

Default: `/api/contentdb/v1/`

All public endpoints are **read-only** (GET list, GET retrieve). No authentication is required.
Serializers are identical to their admin counterparts unless noted.

---

### Attributes (Public)

**URL:** `attributes/`
**Lookup URL:** `attributes/{slug}/`
**Methods:** GET (list), GET (retrieve)
**Auth:** AllowAny
**Filter class:** `AttributeFilter` (same as admin)
**Pagination:** StandardPagination

Same filters as admin: `attribute_set`, `attribute_set[]`.

---

### Attribute Values (Public)

**URL:** `attributes/{attribute_slug}/values/`
**Lookup URL:** `attributes/{attribute_slug}/values/{pk}/`
**Methods:** GET (list), GET (retrieve)
**Auth:** AllowAny
**Pagination:** StandardPagination

---

### Attribute Sets (Public)

**URL:** `attribute-sets/`
**Lookup URL:** `attribute-sets/{slug}/`
**Methods:** GET (list), GET (retrieve)
**Auth:** AllowAny
**Pagination:** StandardPagination

---

### Content Types (Public)

**URL:** `content-types/`
**Lookup URL:** `content-types/{slug}/`
**Methods:** GET (list), GET (retrieve)
**Auth:** AllowAny
**Pagination:** StandardPagination
**Queryset:** `is_layout_extender=False` only

---

### Layout Extender Types (Public)

**URL:** `layout-extender-types/`
**Lookup URL:** `layout-extender-types/{slug}/`
**Methods:** GET (list), GET (retrieve)
**Auth:** AllowAny
**Queryset:** `is_layout_extender=True` only

---

### Routes (Public)

**URL:** `routes/`
**Lookup URL:** `routes/{url}/`
**Methods:** GET (list), GET (retrieve)
**Auth:** AllowAny
**No pagination**
**Filter class:** `RouteFilter` (same as admin -- `placement` filter)

---

### Content Sets (Public)

**URL:** `content-sets/`
**Lookup URL:** `content-sets/{uid}/`
**Methods:** GET (list), GET (retrieve)
**Auth:** AllowAny
**Pagination:** StandardPagination
**Filter class:** `ContentSetFilter` (same as admin)
**Queryset:** Members with `is_layout_extender=False`

---

### Layout Extender Sets (Public)

**URL:** `layout-extender-sets/`
**Lookup URL:** `layout-extender-sets/{uid}/`
**Methods:** GET (list), GET (retrieve)
**Auth:** AllowAny
**Queryset:** Members with `is_layout_extender=True`

---

### Content / Drafts (Public)

**URL:** `content/{content_type}/`
**Lookup URL:** `content/{content_type}/{uid}/`
**Methods:** GET (list), GET (retrieve)
**Auth:** AllowAny
**Pagination:** StandardPagination
**Filter class:** `DraftFilter` (same as admin)
**Queryset:** Content with `is_layout_extender=False` content types

Uses `DraftContentSerializer`. Same filters as admin. No publish/unpublish actions.

---

### Layout Extender / Drafts (Public)

**URL:** `layout-extender/{content_type}/`
**Lookup URL:** `layout-extender/{content_type}/{uid}/`
**Methods:** GET (list), GET (retrieve)
**Auth:** AllowAny
**Queryset:** `is_layout_extender=True` content types

---

### Published Content (Public)

**URL:** `published/{content_type}/`
**Lookup URL:** `published/{content_type}/{uid}/`
**Methods:** GET (list), GET (retrieve)
**Auth:** AllowAny
**Pagination:** StandardPagination
**Filter class:** `PublishedFilter` (same as admin)
**Sorting fields:** `created_at`, `updated_at` (note: mapped to Draft's created_at internally)
**Default sort:** `-created_at` (newest Draft first)

This is the primary endpoint for storefronts. The canonical query:

```
GET /api/contentdb/v1/published/{content_type}/?routes=home&language=EN&access_rights=1
```

Returns the latest Published snapshot for each Draft of the given ContentType, filtered by route
URL, language, and access level.

**No `draft` action** -- the public Published ViewSet does not expose the `GET .../draft/`
custom action. That action is admin-only.

Uses `PublishedContentSerializer`. Sorting in the public ViewSet uses the field names `created_at`
and `updated_at` in query params (the `PublishedSortMixin` maps them to ORM paths internally).

#### Sorting -- Published (Public)

| Sort value | Description |
|------------|-------------|
| `created_at` | Sort by Draft creation time (ascending) |
| `-created_at` | Sort by Draft creation time (descending, default) |
| `updated_at` | Sort by Content last-updated (ascending) |
| `-updated_at` | Sort by Content last-updated (descending) |

---

### Layout Extender Published (Public)

**URL:** `layout-extender-published/{content_type}/`
**Lookup URL:** `layout-extender-published/{content_type}/{uid}/`
**Methods:** GET (list), GET (retrieve)
**Auth:** AllowAny
**Filter class:** `PublishedFilter`

Queryset restricted to `is_layout_extender=True` content types.

---

### Images (Public)

**URL:** `images/`
**Lookup URL:** `images/{uid}/`
**Methods:** GET (list), GET (retrieve)
**Auth:** AllowAny
**Pagination:** StandardPagination
**Filter class:** `ImageFilter` (same as admin)

---

### Image Tags (Public)

**URL:** `image-tags/`
**Lookup URL:** `image-tags/{slug}/`
**Methods:** GET (list), GET (retrieve)
**Auth:** AllowAny
**Pagination:** StandardPagination
**Default order:** `slug` (ascending)

---

### Languages (Public)

**URL:** `languages/`
**Lookup URL:** `languages/{iso2}/`
**Methods:** GET (list), GET (retrieve)
**Auth:** AllowAny
**Pagination:** StandardPagination
**Default order:** `-iso2`

---

### Categories (Public)

**URL:** `category/`
**Lookup URL:** `category/{uid}/`
**Methods:** GET (list), GET (retrieve)
**Auth:** AllowAny
**Pagination:** StandardPagination
**Default order:** `-created_at`

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `language` | string (ISO2) | Filter by language |
| `access_rights` | string | Comma-separated list of access levels (e.g. `1,2`). Filters to categories that have at least one published content item at those access levels. |

**List behavior:** After queryset filtering, the list action additionally removes any item where
`published_posts_count` is 0 and updates `pagination.records` to reflect the filtered count.

---

## Status Code Summary

| Status code | When |
|-------------|------|
| 200 | Successful list, retrieve, or update |
| 201 | Successful create |
| 204 | Successful delete |
| 400 | Validation failure (field errors or malformed request) |
| 401 | Authentication failed or not provided (admin endpoints) |
| 403 | Authenticated but not permitted |
| 404 | Resource not found, or content_type slug does not exist |
| 500 | Unhandled server error |

---

## Activity Logging

All write operations on admin ViewSets (`ContentDBModelViewSet`) automatically create an
`ActivityLog` entry recording the user, the target object (via `GenericForeignKey`), and the
`Action` enum value (`CREATE`, `UPDATE`, `DELETE`, `PUBLISH`). Publish and Unpublish actions on
the Draft ViewSet create additional log entries with `PUBLISH` or `DELETE` respectively.

---

## Deletion Constraints

`Content.delete()` and `Route.delete()` block deletion if the target is identified as a protected
system record (e.g. slug/url `home`, label `header`). This raises an exception rather than
silently skipping. Check the model `delete()` implementations before attempting to delete
core fixtures.
