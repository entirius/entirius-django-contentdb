# AGENTS.md

`entirius-django-contentdb` (Django app `django_contentdb`) — content management module of Entirius: JSON page
content with a draft/publish workflow, routing, channel scoping, media management and blog authoring; v1 API for
content CRUD, v2 API for author management (Pydantic + drf-spectacular).

## Commands

| Command | Meaning |
|---|---|
| `make install` | sync dependencies (uv, incl. extras) |
| `make check` | lint + format-check (ruff) |
| `make fix` | auto-fix lint + format |
| `make test` | test suite (pytest + pytest-django) |

Tests need PostgreSQL: set `DATABASE_URL` (the default in `tests/settings.py` points at a local postgres).

## Conventions

- English only: code, docs, commits, branches, PRs.
- MPL-2.0: every non-trivial source file carries the license header (pre-commit inserts it).
- Toolchain: uv + ruff + hatchling + pytest; all config in `pyproject.toml`; `uv.lock` committed.
- Git flow: `master` (production) + `develop` (integration); changes land via PR; semver tag on `master`.
- Never rename the package / Django app_label / DB table prefix `django_contentdb` — it is a schema contract.
- Migrations are part of the public contract — never edit an already released migration.
- Access: areas live on the AppConfig (`access_areas`, `access_route_rules`), every admin view carries
  `access_area`; a new admin route without one fails `tests/test_access_ownership.py`.
- Default: do not commit — git is the user's call.
- No AI attribution in commits or PR descriptions.

## Architecture

```
src/django_contentdb/
├── models/                          # ORM models (one file per entity)
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
│   ├── author_service.py            #   CRUD + reassignment + set_draft_authors
│   ├── content_service.py           #   sanitize_content(), sanitize_html() — stored page HTML allowlist
│   ├── enrichment_adapter.py        #   enrichment bus adapter (fields by path, attributes, document create)
│   ├── media_enrichment_service.py  #   gallery images as enrichment subjects (source picture, add / replace)
│   ├── content_path_service.py      #   draft text fields by dotted path (read, merge-write, section/tile list)
│   ├── content_attribute_service.py #   content-type attributes as select/multiselect/text fields
│   ├── document_service.py          #   unpublished blog-post draft from an article document
│   ├── article_converter.py         #   article markdown → blog-post payload (pure)
│   └── navigation_service.py        #   get_published_navigation() (cached)
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
│   ├── admin/                       #   ViewSets + function views (CRUD + publish)
│   └── public/                      #   read-only ViewSets
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
├── utils.py                         # StandardPagination, HashedImageField, exception_handler
├── image_manager.py                 # PIL utilities: resize, crop, transparency removal
├── management/commands/
│   ├── sync_contentdb_channels.py   #   Sync ContentChannels from PIM
│   ├── sync_contentdb_languages.py  #   Sync Languages from django_regional
│   ├── propagate_content_channels.py #  Assign channels to drafts with empty M2M
│   └── images-optimize.py           #   Re-optimize all images
├── admin.py                         # Django admin (Author + DraftAuthor/DraftCoAuthor inlines)
├── urls.py                          # Admin + public routers
└── tasks.py                         # Celery: image optimization
```

Layer rule: v1 views use DRF serializers directly (no service layer for CRUD). v2 Author API uses Pydantic schemas + service layer. `viewsets.py` base classes auto-log to ActivityLog. Sync logic lives in `services/sync_service.py`, author CRUD in `services/author_service.py`.

**Does:** Store/serve JSON page content, draft/publish lifecycle, image uploads + thumbnails, attribute metadata, access control, activity audit logging, blog author management

**Does NOT:** Render content (storefront's job), define page layouts (the CMS's job). Optional sync from PIM/django_regional (graceful fallback when not installed)

| Topic | Where |
|---|---|
| Content pipeline, image handling | `docs/content-pipeline.md` |
| API overview (v1 admin/public, v2 authors) | `docs/api.md` |
| Full API surface: endpoints, serializer fields, filters, permissions | `docs/api-reference.md` |
| Data model, authoring entities, key enums | `docs/data-model.md` |
| Complete model inventory | `docs/models-reference.md` |
| ERD config for the docs ERD generator | `docs/erd-config.yaml`, `docs/erd.md` |
| CMS builder config | `docs/cms-config.md` |
| Management commands | `docs/commands.md` |
| Testing, factories | `docs/testing.md` |
| Enrichment adapter: field keys, writes, documents, gallery images | `docs/enrichment-adapter.md` |

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `API_ADMIN_BASE_URL` | `/api-admin/` | Admin API prefix |
| `API_PUBLIC_BASE_URL` | `/api/` | Public API prefix |
| `CONTENTDB_THUMBNAIL_QUALITY` | 60 | JPEG thumbnail quality |
| `CONTENTDB_IMAGE_MAX_WIDTH` | 2560 | Max upload width (0 = no resize) |
| `CONTENTDB_ENRICHMENT_DOCUMENT_TYPE` | `"blog-post"` | Content type of drafts the enrichment adapter creates |

## Gotchas

- Content/Route `delete()` protects `home` and `header` from full removal — raises `ValidationError` (HTTP 400 via `standard_exception_handler`). Duplicates (multiple drafts sharing the same `home` route across channels) are deletable; only the last instance is blocked. `bypass=True` skips validation. System content (`Draft.is_system=True`) is always blocked regardless of routes.
- `AccessRights` is DEPRECATED — replaced by `ContentChannel`. Both `access_rights` and `channel` query params work during transition
- `ContentChannel` syncs from PIM via `services/sync_service.py`. When PIM not installed, sync returns 0 gracefully
- Empty `Draft.channels` M2M = public content (visible to all channel filters)
- Page HTML is sanitised on write: `ContentSerializer.validate_content` / `validate_extension` (draft create, update, publish) call `content_service.sanitize_content`, which runs every markup-bearing string of the JSON through the allowlist of the CMS editor (keep it in step with the CMS `sanitizeHtml` allowlist). A string without a tag is stored as sent. Writes that bypass the serializers (Django admin, fixtures, `Content.objects.create`) are not sanitised; rows stored before this are cleaned on their next save
- Published is immutable — creating a new Published from a Draft creates a new snapshot, doesn't update existing
- Admin API prefix is `/api-admin/` (not `/api/v2/`) — this is v1 architecture, pre-Pydantic
- DRF serializers (not Pydantic) — no drf-spectacular, no OpenAPI auto-generation
- `HashedImageField` uses SHA256 of content for path — same image uploaded twice = same file on disk
- `ContentTypePermission` checks `content_type` slug from URL kwargs — requires content_type in URL path
- `standard_exception_handler` wraps ALL errors in `{"meta": {...}, "data": ...}` format
- Layout extender routes are separate from content routes — `is_layout_extender=True` ContentTypes use `layout-extender/*` paths
- Author cannot appear in both `authors` and `co_authors` M2M on the same Draft — validated in service layer and API
- Both API versions authenticate with simplejwt `JWTAuthentication` — the module reads the Bearer token itself and never relies on the service's `AUTHENTICATION_BACKENDS` (v1 did until 5.1.0, which made admin auth silently deployment-dependent)
- ContentType.supports_authors controls which types show author picker in CMS — only blog-post by default
- Published author data is a live reference through draft — changing authors on draft changes what published shows without re-publishing
- `?author=` filter on v1 endpoints searches both authors and co-authors by slug or UUID
