# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The enrichment adapter conformance kit run against the ContentDB adapter.

django-enrichment is not a dependency of this module: the kit runs where it is importable (the zeno dev venv) and
the file is skipped elsewhere.
"""

import pytest

kit = pytest.importorskip("django_enrichment.testing.adapter_conformance")

from django_contentdb.services import enrichment_adapter  # noqa: E402

CASES = {
    "meta": ("meta.title", {"text": "New title"}, {"text": "Edited title"}),
    "section": ("content.sections.s-1.description", {"text": "Plain lead"}, {"text": "Other lead"}),
    "select": ("attributes.topic", {"option": "news"}, {"option": "guides"}),
    "multiselect": ("attributes.tags", {"options": ["a", "c"]}, {"options": ["b"]}),
    "text_attribute": ("attributes.subtitle", {"text": "A subtitle"}, {"text": "Another subtitle"}),
}


@pytest.fixture
def adapter():
    return enrichment_adapter


@pytest.fixture(params=sorted(CASES))
def conformance_case(request, blog_draft):
    path, value, other_value = CASES[request.param]
    return kit.ConformanceCase(
        subject_ref=str(blog_draft.content.uid),
        target_kind="attribute_value",
        target_locator={"path": path},
        value=value,
        other_value=other_value,
    )


@pytest.fixture
def catalog_channel(blog_setup):
    return blog_setup.channel.idx


@pytest.fixture
def document_case(blog_setup):
    value = {
        "language": "en",
        "title": "Orbital Foundry field notes",
        "slug": "field-notes",
        "body_markdown": "## First\n\nSome text.",
        "meta": {"title": "Field notes", "description": "Notes from the workshop."},
        "faq": [{"question": "Why?", "answer": "Because."}],
    }
    return kit.ConformanceCase(
        subject_ref="run:test",
        target_kind="document",
        target_locator={"channel": blog_setup.channel.idx},
        value=value,
        other_value=value,
    )


class TestContentdbConformance(kit.AdapterConformance, kit.FieldCatalogConformance, kit.DocumentCreateConformance):
    pass
