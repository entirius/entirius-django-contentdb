# Changelog

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
