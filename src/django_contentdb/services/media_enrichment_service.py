# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Gallery images as enrichment subjects (`image:<uid>`): the source of the image kind, and where its results land.

An image is its own one picture (`list_pictures` → itself, marked main). A processed copy (`target_kind="picture"`,
locator `source_picture_ref` = the image's uid) is applied either as a new gallery image (`add`: tag `ai`, name
"<original> · <operation>", `meta.source_image` = the original's uid) or as the new file of the original (`replace`:
the old file stays on disk as the undo anchor). Images belong to no channel: the channel argument is ignored.

A document proposal's staged picture is its cover: `add_cover` makes it a gallery image (tag `ai`), `images_set`
gives the shape a page's tile stores.
"""

import io
import os
import uuid

from PIL import Image as PilImage

from django_contentdb.models import Image, ImageTag, Thumbnail
from django_contentdb.tasks import optimize_image

SUBJECT_PREFIX = "image:"
MODE_ADD = "add"
MODE_REPLACE = "replace"
AI_TAG = {"slug": "ai", "label": "AI"}
_OPERATION_NAMES = {"packshot": "packshot", "lifestyle": "lifestyle", "enhance": "enhanced", "instruct": "edited"}


def is_image_subject(subject_ref: str) -> bool:
    return str(subject_ref).startswith(SUBJECT_PREFIX)


def get_image(subject_ref: str) -> Image:
    """The gallery image of `image:<uid>`; `Image.DoesNotExist` for an unknown or malformed ref."""
    uid = str(subject_ref).removeprefix(SUBJECT_PREFIX)
    if not _is_uuid(uid):
        raise Image.DoesNotExist(f"image {subject_ref!r} not found")
    return Image.objects.get(uid=uid)


def label(image: Image) -> str:
    meta = image.meta or {}
    return str(meta.get("fileName") or meta.get("alt") or image.uid)


def labels(refs: list[str]) -> dict[str, str]:
    """`{ref: label}` of the `image:<uid>` refs that exist; other refs are left out."""
    uids = {ref.removeprefix(SUBJECT_PREFIX): ref for ref in refs if is_image_subject(ref)}
    images = Image.objects.filter(uid__in=_valid_uids(uids))
    return {uids[str(image.uid)]: label(image) for image in images}


def _valid_uids(uids) -> list[str]:
    return [uid for uid in uids if _is_uuid(uid)]


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
    except ValueError:
        return False
    return True


def pictures(subject_ref: str) -> list[dict]:
    """The image as its own one picture: `[{ref, label, url, is_main: True}]`."""
    image = get_image(subject_ref)
    return [{"ref": str(image.uid), "label": label(image), "url": image.image.url, "is_main": True}]


def picture_bytes(subject_ref: str, picture_ref: str) -> tuple[bytes, str]:
    """Bytes + mime of the image; `LookupError` when `picture_ref` names another image."""
    image = get_image(subject_ref)
    if picture_ref != str(image.uid):
        raise LookupError(f"picture {picture_ref!r} is not {subject_ref!r}")
    with image.image.open("rb") as handle:
        data = handle.read()
    with PilImage.open(io.BytesIO(data)) as pil:
        return data, PilImage.MIME.get(pil.format, "application/octet-stream")


def context(subject_ref: str) -> dict:
    """Facts for a prompt and the review label (`name`)."""
    image = get_image(subject_ref)
    meta = image.meta or {}
    tags = list(image.tags.values_list("label", flat=True))
    return {"uid": str(image.uid), "name": label(image), "alt": str(meta.get("alt") or ""), "tags": tags}


def snapshot(subject_ref: str) -> dict:
    """The source image's current file — what drift and undo compare."""
    image = get_image(subject_ref)
    return {"ref": str(image.uid), "file": image.image.name, "url": image.image.url}


def apply_derived(proposal) -> dict | None:
    """`replace` puts the staged file on the source image; `add` (default) makes a new gallery image → `{"ref"}`."""
    source = get_image(proposal.subject_ref)
    if getattr(proposal, "apply_mode", "") == MODE_REPLACE:
        _set_file(source, proposal)
        return None
    added = Image.objects.create(meta=_derived_meta(source, proposal.proposed_value or {}))
    _set_file(added, proposal)
    _tag_ai(added)
    return {"ref": str(added.uid)}


def add_cover(proposal, cover: dict) -> Image:
    """A new gallery image from the staged cover of a document proposal; alt and file name from `cover`."""
    image = Image.objects.create(
        meta={"alt": str(cover.get("alt") or ""), "fileName": cover.get("file_name") or "cover"}
    )
    _set_file(image, proposal)
    _tag_ai(image)
    return image


def images_set(image: Image) -> dict:
    """`{desktop, mobile}` of a page or tile, both the one image (the shape the CMS stores)."""
    entry = {
        "set": [{"source": t.image.url, "width": t.width, "height": t.height} for t in image.thumbnails.all()],
        "uid": str(image.uid),
        "meta": image.meta or {},
        "image": image.image.url,
        "width": image.width,
        "height": image.height,
    }
    return {"desktop": entry, "mobile": dict(entry)}


def delete_cover(images: dict) -> None:
    """Delete the gallery image an `images_set` names (a document's cover, on undo)."""
    if uid := _uid_or_none(str(((images or {}).get("desktop") or {}).get("uid") or "")):
        Image.objects.filter(uid=uid).delete()


def _tag_ai(image: Image) -> None:
    tag, _ = ImageTag.objects.get_or_create(slug=AI_TAG["slug"], defaults={"label": AI_TAG["label"]})
    image.tags.add(tag)


def revert_derived(proposal) -> None:
    """Undo: `replace` restores the old file (`current_snapshot.file`); `add` deletes the image it made."""
    if getattr(proposal, "apply_mode", "") != MODE_REPLACE:
        if added := Image.objects.filter(uid=_uid_or_none(str(getattr(proposal, "result_ref", "") or ""))).first():
            added.delete()
        return
    source = get_image(proposal.subject_ref)
    old = (proposal.current_snapshot or {}).get("file") or ""
    if not old or not source.image.storage.exists(old):
        raise ValueError(f"cannot restore the original file of {proposal.subject_ref!r}: it is no longer available")
    source.image = old
    source.save()
    _refresh_thumbnails(source)


def _uid_or_none(value: str) -> str | None:
    return value if _is_uuid(value) else None


def _set_file(image: Image, proposal) -> None:
    staged = proposal.open_staged_file()
    try:
        image.image.save(os.path.basename(staged.name or "image.png"), staged, save=True)
    finally:
        staged.close()
    _refresh_thumbnails(image)


def _refresh_thumbnails(image: Image) -> None:
    for thumbnail in Thumbnail.objects.filter(source=image):
        thumbnail.delete()
    optimize_image(image.pk)


def _derived_meta(source: Image, value: dict) -> dict:
    meta = source.meta or {}
    stem = os.path.splitext(str(meta.get("fileName") or "image"))[0]
    operation = str(value.get("operation") or "")
    name = f"{stem} · {_OPERATION_NAMES.get(operation, operation or 'AI')}"
    if (value.get("of") or 1) > 1:
        name = f"{name} {value.get('variant')}"
    return {"fileName": name, "alt": meta.get("alt") or "", "source_image": str(source.uid), "ai_operation": operation}
