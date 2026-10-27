# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Gallery images (`image:<uid>`) as subjects of the enrichment `image` kind: source picture, add / replace, undo."""

from types import SimpleNamespace

import pytest
from django.core.files.base import ContentFile

from django_contentdb.models import Image, Thumbnail
from django_contentdb.services import enrichment_adapter as adapter
from tests.conftest import png

pytestmark = pytest.mark.django_db


def ref(image: Image) -> str:
    return f"image:{image.uid}"


def locator(image: Image) -> dict:
    return {"channel": "media", "source_picture_ref": str(image.uid), "operation": "packshot", "variant": 1}


def derived(image: Image, *, mode: str = "add", color: str = "white", value: dict | None = None):
    proposal = SimpleNamespace(
        subject_ref=ref(image),
        target_kind="picture",
        target_locator=locator(image),
        proposed_value=value or {"op": "derived", "operation": "packshot", "variant": 1, "of": 1},
        current_snapshot=adapter.read_current(
            subject_ref=ref(image), target_kind="picture", target_locator=locator(image)
        ),
        apply_mode=mode,
        result_ref="",
    )
    proposal.open_staged_file = lambda: ContentFile(png(color), name="image-1.png")
    return proposal


def file_bytes(image: Image) -> bytes:
    image.refresh_from_db()
    with image.image.open("rb") as handle:
        return handle.read()


class TestSourcePicture:
    def test_lists_the_image_as_its_own_main_picture(self, gallery_image):
        pictures = adapter.list_pictures(subject_ref=ref(gallery_image), channel="media")
        assert pictures == [
            {"ref": str(gallery_image.uid), "label": "mug.png", "url": gallery_image.image.url, "is_main": True}
        ]

    def test_picture_reads_bytes_and_mime(self, gallery_image):
        data, mime = adapter.picture(subject_ref=ref(gallery_image), channel="", picture_ref=str(gallery_image.uid))
        assert (data, mime) == (png("red"), "image/png")

    def test_picture_of_another_image_is_refused(self, gallery_image):
        with pytest.raises(LookupError):
            adapter.picture(subject_ref=ref(gallery_image), channel="", picture_ref="other")

    @pytest.mark.parametrize("subject", ["image:not-a-uuid", "image:00000000-0000-0000-0000-000000000000"])
    def test_unknown_image_is_a_lookup_miss(self, media_root, subject):
        with pytest.raises(Image.DoesNotExist):
            adapter.list_pictures(subject_ref=subject, channel="media")

    def test_subject_labels_keep_only_existing_images(self, gallery_image):
        refs = [ref(gallery_image), "image:00000000-0000-0000-0000-000000000000", "image:x", "SKU-1"]
        assert adapter.subject_labels(refs=refs, channel="media") == {ref(gallery_image): "mug.png"}

    def test_context_names_the_image(self, gallery_image):
        context = adapter.build_context(subject_ref=ref(gallery_image), channel="media", language="")
        assert context == {"uid": str(gallery_image.uid), "name": "mug.png", "alt": "A red mug", "tags": []}


class TestApplyModes:
    def test_a_processed_image_can_be_added_or_replace(self, gallery_image):
        assert adapter.apply_modes(target_kind="picture", target_locator=locator(gallery_image)) == ["add", "replace"]

    def test_other_targets_have_one_way(self):
        assert adapter.apply_modes(target_kind="attribute_value", target_locator={"path": "meta.title"}) == []


class TestAdd:
    def test_add_makes_a_tagged_gallery_image_linked_to_the_source(self, gallery_image):
        result = adapter.apply(derived(gallery_image))
        added = Image.objects.get(uid=result["ref"])
        assert added.meta == {
            "fileName": "mug · packshot",
            "alt": "A red mug",
            "source_image": str(gallery_image.uid),
            "ai_operation": "packshot",
        }
        assert list(added.tags.values_list("slug", flat=True)) == ["ai"]
        assert file_bytes(added) == png("white")
        assert Thumbnail.objects.filter(source=added).exists()
        assert file_bytes(gallery_image) == png("red")

    def test_variants_are_numbered(self, gallery_image):
        value = {"op": "derived", "operation": "enhance", "variant": 2, "of": 3}
        added = Image.objects.get(uid=adapter.apply(derived(gallery_image, value=value))["ref"])
        assert added.meta["fileName"] == "mug · enhanced 2"

    def test_undo_deletes_the_added_image(self, gallery_image):
        proposal = derived(gallery_image)
        proposal.result_ref = adapter.apply(proposal)["ref"]
        adapter.revert(proposal)
        assert list(Image.objects.all()) == [gallery_image]

    def test_add_does_not_change_the_source_snapshot(self, gallery_image):
        proposal = derived(gallery_image)
        adapter.apply(proposal)
        live = adapter.read_current(
            subject_ref=ref(gallery_image), target_kind="picture", target_locator=locator(gallery_image)
        )
        assert live == proposal.current_snapshot


class TestReplace:
    def test_replace_puts_the_new_file_on_the_same_image(self, gallery_image):
        assert adapter.apply(derived(gallery_image, mode="replace")) is None
        assert file_bytes(gallery_image) == png("white")
        assert Image.objects.count() == 1

    def test_undo_restores_the_old_file(self, gallery_image):
        proposal = derived(gallery_image, mode="replace")
        adapter.apply(proposal)
        adapter.revert(proposal)
        assert file_bytes(gallery_image) == png("red")
        assert Thumbnail.objects.filter(source=gallery_image).count() == 1

    def test_undo_without_the_old_file_refuses(self, gallery_image):
        proposal = derived(gallery_image, mode="replace")
        adapter.apply(proposal)
        proposal.current_snapshot = {**proposal.current_snapshot, "file": "image/gone.png"}
        with pytest.raises(ValueError, match="no longer available"):
            adapter.revert(proposal)

    def test_a_replaced_file_is_drift(self, gallery_image):
        before = adapter.read_current(
            subject_ref=ref(gallery_image), target_kind="picture", target_locator=locator(gallery_image)
        )
        adapter.apply(derived(gallery_image, mode="replace"))
        after = adapter.read_current(
            subject_ref=ref(gallery_image), target_kind="picture", target_locator=locator(gallery_image)
        )
        assert after != before
