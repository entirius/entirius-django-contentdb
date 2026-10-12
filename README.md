# entirius-django-contentdb

A Django module for page content of Entirius, the open-source modular ecommerce platform: structured JSON pages with
a draft/publish workflow. It serves routes, images, channel-scoped content and blog authors over a REST API for the
storefront and the CMS.

[![PyPI](https://img.shields.io/pypi/v/entirius-django-contentdb.svg)](https://pypi.org/project/entirius-django-contentdb/)
[![Python](https://img.shields.io/pypi/pyversions/entirius-django-contentdb.svg)](https://pypi.org/project/entirius-django-contentdb/)
[![License: MPL-2.0](https://img.shields.io/badge/license-MPL--2.0-blue.svg)](https://github.com/entirius/entirius-django-contentdb/blob/develop/LICENSE)

## What it does

- Stores page content as structured JSON (sections and tiles) with a draft/publish lifecycle.
- Maps URL routes to published content and scopes content per sales channel and language.
- Uploads images with content-addressed deduplication, resizing and thumbnails.
- Manages blog authors and co-authors on drafts.
- Exposes a read-only public API for storefronts and an admin API for the CMS.

## Installation

```shell
uv add entirius-django-contentdb
pip install entirius-django-contentdb
```

```python
INSTALLED_APPS = [
    ...
    "django_regional",
    "django_utils",
    "django_pim",
    "django_contentdb",
]

# urls.py
urlpatterns = [
    path("", include("django_contentdb.urls")),
]
```

Optional settings: `CONTENTDB_THUMBNAIL_QUALITY`, `CONTENTDB_IMAGE_MAX_WIDTH`, `API_ADMIN_BASE_URL`,
`API_PUBLIC_BASE_URL`; reference with defaults in
https://github.com/entirius/entirius-django-contentdb/blob/develop/AGENTS.md (section Settings).

## Quick start

```python
from django_contentdb.services.navigation_service import get_published_navigation

navigation = get_published_navigation(
    content_type_slug="header",
    language_iso2="en",
    channel_idx="default",
)
```

## Requirements

- Python 3.11 or newer, Django 4.0 or newer.
- PostgreSQL (published-content queries use `DISTINCT ON`).
- Entirius packages pulled in: `entirius-django-pim`, `entirius-django-regional`, `entirius-django-utils`,
  `entirius-py-idx-normalizator`, `entirius-py-image-transformations`.

## Documentation

- Module docs: https://github.com/entirius/entirius-django-contentdb/tree/develop/docs
- Entirius documentation: https://docs.entirius.com/
- Changelog: https://github.com/entirius/entirius-django-contentdb/blob/develop/CHANGELOG.md

## Part of Entirius

This module runs inside the Entirius backend service (Volkanos), next to the product and regional modules.

- Backend service: https://github.com/entirius/entirius-service-volkanos
- Docker harness: https://github.com/entirius/entirius-zeno
- Sibling modules: https://github.com/entirius/entirius-django-pim, https://github.com/entirius/entirius-django-regional,
  https://github.com/entirius/entirius-django-contentdb-translator

## Development

```shell
make install     # sync dependencies (uv)
make check       # lint + format check (ruff)
make test        # test suite (pytest + pytest-django, needs PostgreSQL via DATABASE_URL)
```

Development and agent instructions: https://github.com/entirius/entirius-django-contentdb/blob/develop/AGENTS.md

## License

Mozilla Public License 2.0 (MPL-2.0) — see https://github.com/entirius/entirius-django-contentdb/blob/develop/LICENSE.
