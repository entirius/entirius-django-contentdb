# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The bus's `write` kind over every channel language on a ContentDB draft: only the draft's language is written.

Runs where django-enrichment and its runtime are installed (`make module-test MODULE=entirius-django-contentdb` in
zeno), skipped elsewhere.
"""

import pytest
from django.conf import settings as django_settings

if not django_settings.ENRICHMENT_RUNNABLE:
    pytest.skip("django-enrichment runtime not installed", allow_module_level=True)

import httpx  # noqa: E402
from django.test import override_settings  # noqa: E402
from django_utils.toolbox.testing import CANNED_COMPLETION, mock_toolbox  # noqa: E402

from django_contentdb.models import Content, Draft, Language  # noqa: E402

pytestmark = pytest.mark.django_db
ADAPTERS = {"contentdb": "django_contentdb.services.enrichment_adapter"}


@pytest.fixture
def enrichment(settings):
    from celery import current_app
    from django_enrichment.adapters import clear_cache
    from django_enrichment.kinds import extras

    current_app.conf.task_always_eager = True
    settings.AI_TOOLBOX_BASE_URL = "http://toolbox.test"
    settings.AI_TOOLBOX_API_KEY = "test-key"
    settings.AI_TOOLBOX_CHANNEL = "shop"
    clear_cache()
    extras.clear_cache()
    with override_settings(ENRICHMENT_ADAPTERS=ADAPTERS):
        yield
    clear_cache()
    extras.clear_cache()


@pytest.fixture
def polish_draft(blog_setup):
    """A second draft on the channel, so `["*"]` resolves to `en` and `pl`."""
    draft = Draft.objects.create(
        content_type=blog_setup.content_type,
        content=Content.objects.create(content={}, meta={}),
        name="Pierwszy wpis",
        language=Language.objects.create(iso2="PL", iso3="POL"),
    )
    draft.channels.add(blog_setup.channel)
    return draft


def _write_all_languages(draft, capture):
    from django_enrichment.models import Worker
    from django_enrichment.services import task_service, worker_service

    worker_service.save_worker(Worker(key="contentdb.write", label="Write", kind="write", target_module="contentdb"))
    answer = httpx.Response(200, json={**CANNED_COMPLETION, "parsed": {"meta.title": "A title"}})
    with mock_toolbox() as router, capture(execute=True):
        route = router["complete"].mock(return_value=answer)
        task = task_service.spawn(
            type="contentdb.write",
            scope_spec={"mode": "list", "module": "contentdb", "refs": [str(draft.content.uid)]},
            params={"channel": "web", "fields": ["meta.title"], "languages": ["*"]},
        )
    task.refresh_from_db()
    return task, route


def test_star_languages_write_only_the_draft_language(
    enrichment, blog_draft, polish_draft, django_capture_on_commit_callbacks
):
    from django_enrichment.models import ContentProposal

    task, route = _write_all_languages(blog_draft, django_capture_on_commit_callbacks)
    locators = list(ContentProposal.objects.filter(task=task).values_list("target_locator", flat=True))
    assert route.call_count == 1
    assert locators == [{"path": "meta.title", "language": "en"}]
    assert (task.status, task.counts.get("failed", 0), task.errors) == ("done", 0, [])
