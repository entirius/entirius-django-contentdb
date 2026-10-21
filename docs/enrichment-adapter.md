---
title: Enrichment adapter
description: How the enrichment bus reads and writes ContentDB drafts — field paths, attributes, document create and undo.
---

`django_contentdb.services.enrichment_adapter` lets the enrichment bus (`entirius-django-enrichment`) propose
changes to ContentDB drafts and create new blog-post drafts. The module imports nothing from the bus or from the
translator; the host service registers it:

```python
ENRICHMENT_ADAPTERS = {"contentdb": "django_contentdb.services.enrichment_adapter"}
```

The contract and its fallbacks are described in the enrichment module's adapter guide.

## Conventions

| | Field of a draft | New document |
|---|---|---|
| `subject_ref` | the draft's content uid | anything (e.g. `run:<uid>`); the new uid comes back from `apply` |
| `target_kind` | `attribute_value` | `document` |
| `target_locator` | `{"path": <field key>}` | `{"channel": <idx or "">}` |
| `proposed_value` | `{"text"}` / `{"option"}` / `{"options"}` | `{language, title, slug, body_markdown, meta, faq}` |
| `current_snapshot` | same shape as the value, read raw | `{}` |

A draft has one language, so the locator carries none.

## Field keys

| Key | Type | Notes |
|---|---|---|
| `name` | text, ≤ 128 | the draft name |
| `meta.title`, `meta.description`, `meta.og_title`, `meta.og_description` | text | SEO meta (60 / 160 / 90 / 200 as a hint) |
| `extension.title`, `extension.description` | text | the blog header |
| `attributes.<slug>` | select / multiselect / text | content-type attributes, see below |
| `content.sections.<uid>.title` / `.description` | text / html | per draft |
| `content.tiles.<uid>.title` / `.description` | text / html | per draft |

`describe_fields(channel=, language="")` lists the static fields and the attributes. With `subject_ref=` it also
lists that draft's section and tile texts (a small port of the contentdb-translator extractor: title and description
of every section and tile that has text, in page order). Labels are English.

Attributes: an attribute closed to new values (`allow_new_values=False`, text or int) is a `select` of its stored
values (`multiselect` with `allow_many_values`); an open single-value text attribute is `text` (128 or 2048
characters). Bool, datetime and open multi-value attributes are not offered. A write checks that the attribute
belongs to the draft's content type.

## Writes

- **Merge.** A path write changes only the addressed key; the rest of `content`, `meta` or `extension` is kept.
  A section or tile that does not exist raises `ValueError`.
- **Strings only.** A text path or text attribute takes `{"text": <str>}`; any other value (a dict, a missing
  `text`) raises `ValueError` instead of being stringified.
- **Sanitising.** Values pass `content_service.sanitize_content` (the editor allowlist), like an API write.
- **Audit.** Every apply and revert writes an `ActivityLog` row as `proposal.reviewed_by`; a proposal without a
  reviewer is not logged.
- **Drift and undo.** `read_current` returns the stored value as is, so a CMS edit after an apply shows up as drift;
  `revert` writes `current_snapshot` back.

## Documents

`apply` of a `document` proposal creates an unpublished draft of the content type
`CONTENTDB_ENRICHMENT_DOCUMENT_TYPE` (default `blog-post`) and returns `{"subject_ref": <content uid>}`:

- the payload comes from `services/article_converter.py`, a port of the article markdown converter: H1 title,
  one `section-text` per run of text (images end a section and are dropped — no image pipeline yet), a
  `section-faq` from the `## FAQ` block, SEO meta and the blog header; the `faq` list is appended as a `## FAQ`
  block unless the body already has one;
- language by iso2 (unknown → `ValueError`), public access rights, the locator's channel;
- route = the slugified `slug` (or title), suffixed `-2`, `-3`, … when taken;
- a proposal with a staged picture (the bus's `compose` with a cover, value `cover: {alt, file_name}`) adds it to the
  gallery (tag `ai`, `meta.alt` / `meta.fileName`), stores it as the blog tile's `extension.images_set` (`desktop` and
  `mobile`, the shape the CMS writes) and sets `meta.og_image` to its URL; `revert` deletes that image with the draft.

`revert` deletes the created draft (`proposal.result_ref`) and the routes only it uses. A draft that has been
published, or edited after it was created (its content saved again, e.g. in the CMS), is never deleted: `revert`
raises `ValueError`. `create_draft` aligns the content's `updated_at` with `created_at`, so any later save counts
as an edit.

## Gallery images

A gallery `Image` is a subject too: `subject_ref` = `image:<uid>` (`services/media_enrichment_service.py`). It is the
source of the enrichment `image` kind (packshot, lifestyle, enhance, own instruction) and the place its results land.
Images belong to no channel: the channel the bus passes is ignored.

- `list_pictures` gives the image as its own one picture (marked main); `picture` reads its bytes and mime and
  refuses (`LookupError`) a `picture_ref` that is another image. An unknown image raises `Image.DoesNotExist`.
- `subject_labels` returns `{ref: file name}` of the `image:<uid>` refs that exist (other refs are left out);
  `build_context` gives uid, name, alt text and tags, so a review card is named after the file.
- A `picture` proposal (locator `{channel, source_picture_ref, operation, variant}`) offers two ways
  (`apply_modes` → `["add", "replace"]`): `add` (the default, and what a bulk accept does) makes a new gallery image
  tagged `ai`, named "<original name> · packshot" (`enhanced`, `edited`, …; numbered when a run made several), with
  the original's alt text and `meta.source_image` = the original's uid, and returns `{"ref": <its uid>}` — undo
  deletes it. `replace` saves the new file on the same image; the old file stays on disk and is the undo anchor
  (`current_snapshot.file`); undo puts it back, or raises `ValueError` when it is gone. Both rebuild the thumbnail.
- `read_current` of a picture is the original's `{ref, file, url}` — the review shows `url` as "before", and a file
  replaced since is drift.
- Video is not supported: the gallery stores images only (`HashedImageField`), so there is no video worker for
  ContentDB.

## Other callables

- `resolve_targets`: `list` pages the `refs` (the bus parses `csv` itself); `filter` pages the draft uids of
  `channel` (filters `content_type`, `language`). A missing channel or an unknown filter key raises `ValueError`.
- `find_gaps`: no checks yet, always `[]`.
- `channel_languages`: the channel's default language first, then the other languages of its drafts.
- `subject_languages`: the draft's own language (lowercase iso2), so a `write` over `["*"]` writes only that one
  and skips the others without an AI call or a failed subject.
- `make_locator` / `field_key`: `{"path": key}` and back; an unknown key raises `ValueError`.
- `build_context`: uid, content type, name, route, SEO title/description and the page text as plain text, at most
  3000 characters as JSON.

## Tests

`tests/test_enrichment_adapter.py` covers every callable, `tests/test_media_enrichment.py` the gallery images; `tests/test_article_converter.py` checks the converter
against golden files produced by the original converter; `tests/test_enrichment_conformance.py` runs the
enrichment conformance kit (draft fields, documents, and a gallery image replaced and restored) and is skipped where `django_enrichment` is not installed; `tests/test_enrichment_write.py`
runs the bus's `write` kind on a draft and needs the bus's runtime too (`make module-test
MODULE=entirius-django-contentdb` in zeno), skipped elsewhere.
