# django-contentdb

Content management module for the Volkanos ecommerce platform — JSON-based page content with
draft/publish workflow, routing, access control, media management (images + thumbnails, SHA256
dedup) and blog authoring. v1 API for content CRUD, v2 API for author management
(Pydantic + drf-spectacular).

## Installation

```shell
pip install entirius-django-contentdb
```

Add the app to your project:

```python
INSTALLED_APPS = [
    ...
    "django_contentdb",
]
```

Optional integrations: content channels sync from `django_pim`, languages from `django_regional`
(both degrade gracefully when the module is absent from `INSTALLED_APPS`).

## Development

```shell
make install     # sync dependencies (uv)
make check       # lint + format check (ruff)
make test        # test suite (pytest + pytest-django)
```

Architecture, API and model reference: [AGENTS.md](AGENTS.md), [docs/](docs/).

## License

Mozilla Public License 2.0 — see [LICENSE](LICENSE).
