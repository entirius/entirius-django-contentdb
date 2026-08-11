# Changelog

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
