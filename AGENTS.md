# AGENTS.md

## Quick Reference

Content management module for the Volkanos ecommerce platform. JSON-based page content with draft/publish workflow, routing, access control, media management, and blog authoring. v1 API for content CRUD, v2 API for author management (Pydantic + drf-spectacular).

**Tech:** Python >=3.10, Django >=4.0, DRF, django-filter, Pillow, Pydantic, drf-spectacular, djangorestframework-simplejwt

## Commands

| Command | Meaning |
|---|---|
| `make install` | sync dependencies (uv, incl. extras) |
| `make check` | lint + format-check (ruff) |
| `make fix` | auto-fix lint + format |
| `make test` | test suite (pytest + pytest-django) |

## Conventions

- English only: code, docs, commits, branches, PRs.
- MPL-2.0: every non-trivial source file carries the license header (pre-commit inserts it).
- Toolchain: uv + ruff + hatchling + pytest; all config in `pyproject.toml`; `uv.lock` committed.
- Git flow: `master` (production) + `develop` (integration); changes land via PR; semver tag on `master`.
- Never rename the package / Django app_label / DB table prefix `django_contentdb` — it is a schema contract.
- Migrations are part of the public contract — never edit an already released migration.
- Default: do not commit — git is the user's call.

## Architecture

```
src/django_contentdb/
├── models/                          # 26 ORM models (one file per entity)
│   ├── content.py                   #   Content (UUID pk, JSONField body)
│   ├── content_type.py              #   ContentType (slug↑, is_layout_extender, supports_authors)
│   ├── content_channel.py           #   ContentChannel (idx↑, name, default_language FK, is_default)
│   ├── draft.py                     #   Draft (FK→ContentType, O2O→Content, FK→Language, M2M→ContentChannel, M2M→Author)
│   ├── published.py                 #   Published (FK→Draft, O2O→Content, immutable snapshot)
│   ├── route.py                     #   Route (url↑, placement, M2M→Draft)
│   ├── author.py                    #   Author (UUID, name, slug↑, role/bio/tag _t9n, photo FK→Image)
│   ├── draft_author.py              #   DraftAuthor (through: Draft↔Author, position)
│   ├── draft_co_author.py           #   DraftCoAuthor (through: Draft↔Author, position)
│   ├── attribute.py                 #   Attribute (slug↑, 6 type flags, filter/search flags)
│   ├── attribute_set.py             #   AttributeSet (slug↑, M2M→Attribute)
│   ├── attribute_value.py           #   AttributeValue (typed value fields)
│   ├── attribute_to_set.py          #   AttributeToSet (M2M through)
│   ├── content_attribute.py         #   ContentAttribute (M2M through: Content↔AttributeValue)
│   ├── image.py                     #   Image (UUID, HashedImageField, SHA256 dedup)
│   ├── thumbnail.py                 #   Thumbnail (method, source→Image, unique per dims)
│   ├── image_tag.py                 #   ImageTag (slug↑)
│   ├── image_to_tag.py              #   ImageToTag (M2M through)
│   ├── access_rights.py             #   AccessRights (access_level = PK, pk=1 = public) [DEPRECATED]
│   ├── language.py                  #   Language (iso2↑, iso3↑, name_en, name_pl)
│   ├── category.py                  #   Category (UUID, auto url_key from name)
│   ├── content_type_permission.py   #   ContentTypePermission (action×content_type unique)
│   ├── content_set.py               #   ContentSet (UUID, M2M→Draft)
│   ├── draft_to_content_set.py      #   DraftToContentSet (M2M through)
│   ├── activity_log.py              #   ActivityLog (GenericFK audit trail)
│   └── deleted.py                   #   Deleted (O2O→Content, soft-delete audit)
│
├── services/                        # Business logic
│   ├── sync_service.py              #   sync_channels_from_pim(), sync_languages_from_pim()
│   └── author_service.py            #   CRUD + reassignment + set_draft_authors
│
├── api/                             # v2 API (Pydantic + drf-spectacular)
│   └── v2/
│       ├── views/author_views.py    #   AuthorViewSet (JWT + IsAdminUser)
│       ├── urls.py                  #   /api/contentdb/v2/admin/authors/
│       └── pagination.py            #   AdminPageNumberPagination (20/page, max 100)
│
├── schemas/                         # Pydantic schemas (v2 API)
│   ├── requests/author.py           #   CreateAuthorRequest, UpdateAuthorRequest, DeleteAuthorRequest
│   └── responses/author.py          #   AuthorResponse, AuthorBriefResponse, AuthorListResponse
│
├── views/                           # DRF ViewSets (v1 admin + public mirrors)
│   ├── admin/                       #   17 ViewSets + 2 function views (CRUD + publish)
│   └── public/                      #   16 ViewSets (read-only)
│
├── serializers/                     # DRF serializers (v1 API)
│   ├── content.py                   #   ContentSerializer, DraftContentSerializer
│   ├── content_channel.py           #   ContentChannelSerializer
│   ├── published.py                 #   PublishedContentSerializer
│   ├── attribute.py, attribute_value.py, attribute_set.py
│   ├── content_type.py, route.py, language.py, category.py
│   ├── image.py, image_tag.py, content_set.py
│   └── fields/                      #   Custom fields (AuthorBrief, CreateableSlugRelated, etc.)
│
├── filters/                         # django-filter classes
│   ├── published.py                 #   access_rights, channel, language, routes, author
│   ├── draft.py                     #   access_rights, channel, language, routes, author
│   ├── content_set.py, image.py
│   └── ordering.py                  #   sort by created_at
│
├── viewsets.py                      # Base classes: ContentDBModelViewSet, ROContentDBModelViewSet
├── permissions.py                   # ContentTypePermission (action-based per content_type)
├── enums.py                         # Action: CREATE, UPDATE, DELETE, PUBLISH, VIEW
├── settings.py                      # ADMIN_BASE_URL, PUBLIC_BASE_URL, THUMBNAIL_QUALITY, IMAGE_MAX_WIDTH
├── utils.py                         # StandardPagination, HashedImageField, DjangoAuth, exception_handler
├── image_manager.py                 # PIL utilities: resize, crop, transparency removal
├── management/commands/
│   ├── sync_contentdb_channels.py   #   Sync ContentChannels from PIM
│   ├── sync_contentdb_languages.py  #   Sync Languages from django_regional
│   └── propagate_content_channels.py #  Assign channels to drafts with empty M2M
├── admin.py                         # Django admin (20 registered models, Author + DraftAuthor/DraftCoAuthor inlines)
├── urls.py                          # Admin + public routers (19 routes each)
└── tasks.py                         # Celery: image optimization
```

Layer rule: v1 views use DRF serializers directly (no service layer for CRUD). v2 Author API uses Pydantic schemas + service layer. `viewsets.py` base classes auto-log to ActivityLog. Sync logic lives in `services/sync_service.py`, author CRUD in `services/author_service.py`.

---

## Content Pipeline

```
Content (UUID pk, JSON blob: {tiles, sections, tiles_order, sections_order})
  → Draft (links ContentType + Content + Language + ContentChannel M2M)
    → Published (immutable snapshot of Draft + Content)
      → Route (URL path, M2M→Draft, placement: top|bottom)
```

- **ContentType** defines the template: `static-page`, `header`, `blog-post`, `product-rich-content`, `category-rich-content`
- **ContentType.is_layout_extender** = true → header type (separate API routes)
- **ContentType.supports_authors** = true → enables author picker in CMS (only `blog-post` by default)
- **Author** — author profiles with name, slug, role/bio/tag translations, photo, contacts, social links
- **DraftAuthor / DraftCoAuthor** — through-tables linking Draft ↔ Author with position ordering
- **ContentChannel** — local mirror of PIM Channel (idx↑, name, default_language FK, is_default). Syncs from PIM via admin action or management command. Empty `Draft.channels` M2M = content is public (all channels).
- **AccessRights** — DEPRECATED. Replaced by ContentChannel. Kept for backward compatibility during transition.
- Content/Route `delete()` prevents deletion of `home` and `header` records

---

## API

**Response wrapper** (all endpoints): `{"meta": {"status": "OK|CREATED|UPDATED|DELETED|ERROR"}, "data": ...}`

**Pagination:** `StandardPagination` — page_size=6, max=100, query param: `limit`

### Admin API — `/{ADMIN_BASE_URL}/contentdb/{version}/`

Default: `/api-admin/contentdb/v1/`. Auth: DjangoAuth + IsAdminUser | ContentTypePermission.

```
contentdb/v1/
├── attributes/                         CRUD
│   └── {attribute_slug}/values/        CRUD (nested)
├── attribute-sets/                     CRUD
├── content-types/                      CRUD
├── routes/                             CRUD
├── content-sets/                       CRUD
├── content/{content_type}/             CRUD drafts
│   └── {uid}/published/               POST (publish), DELETE (unpublish)
├── published/{content_type}/           RO
├── layout-extender-types/              CRUD (is_layout_extender=True only)
├── layout-extender-sets/               CRUD
├── layout-extender/{content_type}/     CRUD layout drafts
├── layout-extender-published/...       RO
├── images/                             CRUD
├── image-tags/                         CRUD
├── languages/                          CRUD
├── channels/                           RO (ContentChannel list/retrieve)
├── category/                           CRUD
├── content-permissions/                FBV (manage per-type permissions)
└── layout-extender-permissions/        FBV
```

### Public API — `/{PUBLIC_BASE_URL}/contentdb/{version}/`

Default: `/api/contentdb/v1/`. Auth: AllowAny.

Same routes as admin but **read-only** (list + retrieve only). Key query:

```
GET /api/contentdb/v1/published/{content_type_slug}/?routes=home&language=EN&channel=default
```

Filters: `routes` (url), `language` (iso2), `channel` (ContentChannel idx), `author` (slug or UUID), `access_rights` (deprecated). Sort: `created_at` (maps to draft's created_at). Channel filter: returns content assigned to that channel + public content (empty channels M2M). Author filter: searches both authors and co-authors on drafts.

Full endpoint details: `docs/api-reference.md`

### v2 Admin API — /api/contentdb/v2/admin/

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /authors/ | List authors (search, is_active, channel post count) |
| POST | /authors/ | Create author (auto-slug) |
| GET | /authors/{uid}/ | Author detail |
| PATCH | /authors/{uid}/ | Update author |
| DELETE | /authors/{uid}/ | Delete with reassignment |

Auth: JWT + IsAdminUser. Pagination: 20/page, max 100. Pydantic schemas for request/response validation.

---

## Data Model — Authoring

| Entity | Key Fields |
|--------|------------|
| Author | uid (UUID), slug↑, name, role_t9n, description_t9n, tag_t9n, photo→Image, contacts, social_profiles, is_active |
| DraftAuthor | draft→Draft, author→Author, position (unique together: draft+author) |
| DraftCoAuthor | draft→Draft, author→Author, position (unique together: draft+author) |

---

## Image Handling

- **HashedImageField** — SHA256 content-addressed storage: `aa/bb/cccccccc...{ext}`
- **Auto-resize** on upload: max width = `CONTENTDB_IMAGE_MAX_WIDTH` (default 2560)
- **Thumbnail** model: unique per (method, source, width, height)
- **Deduplication**: same file content → same hash → same path (no duplicates)
- Uses `image_transformations` library with PIL fallback

---

## Key Enums

| Enum | Values |
|------|--------|
| **Action** | CREATE, UPDATE, DELETE, PUBLISH, VIEW |
| **Thumbnail.method** | "optimize" |
| **Route.placement** | "top", "bottom" |

---

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `API_ADMIN_BASE_URL` | `/api-admin/` | Admin API prefix |
| `API_PUBLIC_BASE_URL` | `/api/` | Public API prefix |
| `CONTENTDB_THUMBNAIL_QUALITY` | 60 | JPEG thumbnail quality |
| `CONTENTDB_IMAGE_MAX_WIDTH` | 2560 | Max upload width (0 = no resize) |

---

## Testing

Factory classes available:

```
tests/__init__.py: AttributeSetFactory, ContentTypeFactory, ContentFactory, DraftFactory, PublishedFactory, ContentChannelFactory
```

```bash
make test                 # pytest (requires Postgres — set DATABASE_URL or use the CI default)
```

---

## Management Commands

```bash
# Sync commands (run inside Django service context)
python manage.py sync_contentdb_channels    # Sync from PIM
python manage.py sync_contentdb_languages   # Sync from django_regional
python manage.py propagate_content_channels --channel=default  # Assign channel to public content
```

---

## Gotchas

- Content/Route `delete()` protects `home` and `header` from full removal — raises `ValidationError` (HTTP 400 via `standard_exception_handler`). Duplicates (multiple drafts sharing the same `home` route across channels) are deletable; only the last instance is blocked. `bypass=True` skips validation. System content (`Draft.is_system=True`) is always blocked regardless of routes.
- `AccessRights` is DEPRECATED — replaced by `ContentChannel`. Both `access_rights` and `channel` query params work during transition
- `ContentChannel` syncs from PIM via `services/sync_service.py`. When PIM not installed, sync returns 0 gracefully
- Empty `Draft.channels` M2M = public content (visible to all channel filters)
- Published is immutable — creating a new Published from a Draft creates a new snapshot, doesn't update existing
- Admin API prefix is `/api-admin/` (not `/api/v2/`) — this is v1 architecture, pre-Pydantic
- DRF serializers (not Pydantic) — no drf-spectacular, no OpenAPI auto-generation
- `HashedImageField` uses SHA256 of content for path — same image uploaded twice = same file on disk
- `ContentTypePermission` checks `content_type` slug from URL kwargs — requires content_type in URL path
- `standard_exception_handler` wraps ALL errors in `{"meta": {...}, "data": ...}` format
- Layout extender routes are separate from content routes — `is_layout_extender=True` ContentTypes use `layout-extender/*` paths
- Author cannot appear in both `authors` and `co_authors` M2M on the same Draft — validated in service layer and API
- v2 Author endpoints use JWT + IsAdminUser (not DjangoAuth like v1)
- ContentType.supports_authors controls which types show author picker in CMS — only blog-post by default
- Published author data is a live reference through draft — changing authors on draft changes what published shows without re-publishing
- `?author=` filter on v1 endpoints searches both authors and co-authors by slug or UUID

---

## Module Boundaries

**Does:** Store/serve JSON page content, draft/publish lifecycle, image uploads + thumbnails, attribute metadata, access control, activity audit logging, blog author management

**Does NOT:** Render content (storefront's job), define page layouts (CMS Blueprint's job). Optional sync from PIM/django_regional (graceful fallback when not installed)

---

## Reference Docs

| File | Content |
|------|---------|
| `docs/api-reference.md` | Full API surface: all endpoints, serializer fields, filters, permissions |
| `docs/models-reference.md` | Complete model inventory: fields, relationships, constraints, enums |
| `docs/erd-config.yaml` | ERD diagram config for `make erd` |
