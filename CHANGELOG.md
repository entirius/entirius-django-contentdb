# Changelog

## Unreleased

- Enrichment adapter (`services/enrichment_adapter.py`, registered by the host as
  `ENRICHMENT_ADAPTERS["contentdb"]`): the enrichment bus reads and writes draft fields by path (`name`, `meta.*`,
  `extension.*`, section and tile texts) and content-type attributes (select, multiselect, text), with merge writes,
  sanitising and an `ActivityLog` row as the reviewer. A `document` proposal creates an unpublished blog-post draft
  from article markdown (a port of the article converter) and returns its uid; undo deletes it while never
  published. New setting `CONTENTDB_ENRICHMENT_DOCUMENT_TYPE` (default `blog-post`). See `docs/enrichment-adapter.md`.

## 5.2.0 — 2026-10-12

- Access: the module declares its own access areas on its AppConfig and its admin views (copied from the
  entirius-django-access defaults; behaviour unchanged).

### Security

- The router roots of the v1 public and admin APIs (an index of route names) declare `authentication_classes = []`
  and `AllowAny`. They inherited the service default, so under DRF's defaults (session and Basic) the root answered
  differently for a right and a wrong password sent as `Authorization: Basic`. The admin root carries the access area
  `content.pages` itself (it was mapped by an access default for the framework's root view), so under the access gate
  it answers as before. The views behind both roots are unchanged.

- Page HTML is sanitised on write. Creating a draft, updating it and publishing it pass `content` and `extension`
  through an allowlist (`services/content_service.py`): every string of the JSON that carries markup keeps only the
  tags, attributes, URL schemes (`http`, `https`, `mailto`; images `http`, `https`) and style properties the CMS
  editor writes; `script` and `style` elements go with their content, event handlers and `javascript:` / `data:`
  URLs are dropped. Before, rich-text props were stored as sent and rendered as HTML by the CMS and the storefront,
  so an account allowed to save content could store a script. Content stored earlier is not rewritten: it is
  sanitised the next time it is saved or published.

## 5.1.0 — 2026-08-11

- v1 Admin API authenticates with `JWTAuthentication` (djangorestframework-simplejwt)
  instead of the `DjangoAuth` class, which delegated to
  `django.contrib.auth.authenticate()` and therefore depended on the deploying
  service listing a JWT-reading backend in `AUTHENTICATION_BACKENDS`. That
  requirement was undocumented and unenforceable — a service adopting contentdb
  without it got HTTP 401 on every admin request. v1 now matches v2, and the
  module no longer has a hidden dependency on `entirius-django-accounts`.
- Removed `DjangoAuth` from `django_contentdb.utils`. Deployments that relied on
  a custom `AUTHENTICATION_BACKENDS` entry to authenticate v1 admin requests must
  issue simplejwt tokens instead.
- Authenticating on the v1 Admin API no longer requires the user to be a
  storefront customer (`UserExtensionProxy.is_customer`), a condition the old
  backend imposed. Authorization is unchanged: `IsAdminUser | ContentTypePermission`.

## 5.0.1 — 2026-08-06

- Restore case-insensitive language filtering.

## 5.0.0 — 2026-07-11

- Initial public release: CMS content storage — draft/published snapshot
  model, routes, layouts, navigation, image library with configurable
  thumbnails, authors, blog categories, and channel-based content filtering
  synced from PIM.
- v2 Admin API (Pydantic schemas, OpenAPI docs, JWT + IsAdminUser) and
  read-only Public API.
- Public blog-post detail returns `prev`/`next` neighbour links for SSR
  navigation without extra round-trips.
- `Content.delete()` / `Route.delete()` validation errors surface as
  HTTP 400 instead of HTTP 500.
- Migrations squashed into a single initial migration for the Entirius epoch.
