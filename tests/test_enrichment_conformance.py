# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The enrichment adapter conformance kit run against the ContentDB adapter.

django-enrichment is not a dependency of this module yet (the kit ships after entirius-django-enrichment 2.2.0): the
kit runs where it is importable (the zeno dev venv) and the file is skipped elsewhere. Set
`CONTENTDB_REQUIRE_CONFORMANCE=1` to turn a missing kit into a failure instead of a skip.
"""

import hashlib
import importlib
import os

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from tests.conftest import png


def _load_kit():
    try:
        return importlib.import_module("django_enrichment.testing.adapter_conformance")
    except ImportError:
        if os.environ.get("CONTENTDB_REQUIRE_CONFORMANCE") == "1":
            raise
        pytest.skip("enrichment conformance kit not installed", allow_module_level=True)


kit = _load_kit()

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


# --- gallery images: a processed copy replaces the image's file; the bus stages the binary, a stand-in does it here --


class _ReplaceBus:
    """The ContentDB adapter plus what `apply_service` does around a picture apply in `replace` mode: stage the next
    payload as the proposal's binary. `read_current` is compared by the file's content (the stored name is a hash plus
    a storage suffix), and each content maps back to the real snapshot the adapter's undo reads."""

    def __init__(self, payloads: list[bytes]):
        self._payloads = payloads
        self._snapshots: dict[str, dict] = {}

    def __getattr__(self, name: str):
        return getattr(enrichment_adapter, name)

    def read_current(self, **kwargs) -> dict:
        real = enrichment_adapter.read_current(**kwargs)
        digest = _digest_of(real["file"])
        self._snapshots[digest] = real
        return {"ref": real["ref"], "sha256": digest}

    def apply(self, proposal) -> None:
        staged = ContentFile(self._payloads.pop(0), name="image-1.png")
        proposal.open_staged_file = lambda: staged
        proposal.apply_mode = "replace"
        proposal.current_snapshot = self._real(proposal.current_snapshot)
        enrichment_adapter.apply(proposal)

    def revert(self, proposal) -> None:
        proposal.current_snapshot = self._real(proposal.current_snapshot)
        enrichment_adapter.revert(proposal)

    def _real(self, snapshot: dict) -> dict:
        return self._snapshots.get((snapshot or {}).get("sha256"), snapshot)


def _digest_of(name: str) -> str:
    with default_storage.open(name, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


_PICTURE_PAYLOADS = [png("white"), png("blue")]


class TestContentdbPictureConformance(kit.AdapterConformance):
    @pytest.fixture
    def adapter(self):
        return _ReplaceBus(list(_PICTURE_PAYLOADS))

    @pytest.fixture
    def conformance_case(self, gallery_image):
        uid = str(gallery_image.uid)
        white, blue = (hashlib.sha256(payload).hexdigest() for payload in _PICTURE_PAYLOADS)
        return kit.ConformanceCase(
            subject_ref=f"image:{uid}",
            target_kind="picture",
            target_locator={"channel": "media", "source_picture_ref": uid, "operation": "packshot", "variant": 1},
            value={"ref": uid, "sha256": white},
            other_value={"ref": uid, "sha256": blue},
        )
