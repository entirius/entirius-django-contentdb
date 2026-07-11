# Models Reference -- django-contentdb

Complete field-level inventory of all 22 ORM models in `django_contentdb`. Covers fields, types, constraints, relationships, and special behavior.

---

## Enums

### Action (`django_contentdb.enums`)

`django.db.models.TextChoices` — used by `ActivityLog.action` and `ContentTypePermission.action`.

| Value (DB) | Label | Used when |
|------------|-------|-----------|
| `create` | Create | Record created |
| `update` | Update | Record updated |
| `delete` | Delete | Record deleted |
| `publish` | Publish | Draft published |
| `view` | View | Record viewed |

### Route.Placement

Inner `TextChoices` on the `Route` model.

| Value (DB) | Label | Meaning |
|------------|-------|---------|
| `top` | Top | Default navigation placement |
| `bottom` | Bottom | Footer navigation |

### Thumbnail.ProcessingMethod

Inner `TextChoices` on the `Thumbnail` model.

| Value (DB) | Label | Meaning |
|------------|-------|---------|
| `optimize` | Optimize | Image optimization pass |

---

## Content Pipeline Models

These five models form the core draft/publish workflow.

### Content

**File:** `models/content.py`

Stores the raw JSON page body. One `Content` record = one page version.

| Field | Django Type | null | blank | default | editable | Notes |
|-------|-------------|------|-------|---------|----------|-------|
| `id` | AutoField (PK) | | | auto | | Standard Django PK |
| `uid` | UUIDField | | | `uuid.uuid4` | No | Exposed in API and URLs |
| `content` | JSONField | | | `dict` | | Page body: `{tiles, sections, tiles_order, sections_order}` |
| `extension` | JSONField | Yes | Yes | | | Optional extra structured data |
| `meta` | JSONField | Yes | Yes | | | Optional metadata blob |
| `category` | ForeignKey → `Category` | Yes | Yes | | | `on_delete=SET_NULL` |
| `attributes` | ManyToManyField → `AttributeValue` | | | | | Through: `ContentAttribute`; `related_name="content_set"` |
| `created_at` | DateTimeField | | | auto | No | `auto_now_add=True` |
| `updated_at` | DateTimeField | | | auto | No | `auto_now=True` |

**Meta:** `ordering = ["-created_at", "-updated_at"]`

**Custom `delete()` — delete protection:**

Raises `Exception` if the `Content` is linked to a `Draft` whose routes include `url="home"` or `url="header"`, unless `bypass=True` is passed explicitly.

```python
content.delete()           # raises if home or header
content.delete(bypass=True)  # skips protection
```

**`__str__`:** Returns `str(uid)`.

---

### ContentType

**File:** `models/content_type.py`

Template descriptor. Each content item belongs to exactly one type (e.g., `static-page`, `header`, `blog-post`).

| Field | Django Type | null | blank | default | editable | Notes |
|-------|-------------|------|-------|---------|----------|-------|
| `id` | AutoField (PK) | | | auto | | |
| `slug` | CharField(64) | | | | | Auto-generated; unique (see constraint) |
| `label` | CharField(64) | | | | | Human-readable name |
| `attribute_set` | ForeignKey → `AttributeSet` | | | | | `on_delete=CASCADE`; `related_name="content_types"` |
| `is_layout_extender` | BooleanField | | | `False` | | `True` for header-type content; uses separate API routes |
| `created_at` | DateTimeField | | | auto | No | `auto_now_add=True` |
| `updated_at` | DateTimeField | | | auto | No | `auto_now=True` |

**Unique Constraints:**

| Name | Fields |
|------|--------|
| `content_type_slug_is_unique` | `slug` |

**`__str__`:** Returns `label`.

**Known ContentType slugs (fixture data):**

| slug | is_layout_extender |
|------|--------------------|
| `static-page` | False |
| `header` | True |
| `blog-post` | False |
| `product-rich-content` | False |
| `category-rich-content` | False |

---

### Draft

**File:** `models/draft.py`

Links a `Content` blob to its type, language, and access configuration. The editorial record for a page.

| Field | Django Type | null | blank | default | editable | Notes |
|-------|-------------|------|-------|---------|----------|-------|
| `id` | AutoField (PK) | | | auto | | |
| `content_type` | ForeignKey → `ContentType` | | | | | `on_delete=CASCADE` |
| `content` | OneToOneField → `Content` | | | | | `on_delete=CASCADE`; reverse: `content.draft` |
| `name` | CharField(128) | | Yes | `""` | | Display label in admin |
| `access_rights` | ManyToManyField → `AccessRights` | | | | | `related_name="draft_access"` |
| `language` | ForeignKey → `Language` | | | `1` | | `on_delete=CASCADE`; default pk=1 |
| `created_at` | DateTimeField | | | auto | No | `auto_now_add=True` |

**Meta:** `ordering = ["-created_at"]`

**`__str__`:** Returns `str(content)` (i.e., the Content's UUID string).

**Relationship summary:**

- `draft.routes` — M2M back-reference from `Route.drafts`
- `draft.published` — reverse FK from `Published`
- `draft.draft_access` — reverse M2M from `AccessRights`

---

### Published

**File:** `models/published.py`

Immutable snapshot. Creating a new `Published` from a `Draft` + `Content` produces a new row — does not update an existing one.

| Field | Django Type | null | blank | default | editable | Notes |
|-------|-------------|------|-------|---------|----------|-------|
| `id` | AutoField (PK) | | | auto | | |
| `draft` | ForeignKey → `Draft` | | | | | `on_delete=CASCADE`; `related_name="published"` |
| `content` | OneToOneField → `Content` | | | | | `on_delete=CASCADE`; unique — one Published per Content |
| `created_at` | DateTimeField | | | auto | No | `auto_now_add=True` |

**Meta:** `ordering = ["-created_at"]`

**`__str__`:** Returns `str(content)`.

**Key behavioral note:** Publishing creates a new `Content` snapshot (clone) and attaches it to the new `Published` row. The `Draft.content` and `Published.content` fields point to **different** `Content` rows.

---

### Route

**File:** `models/route.py`

URL path that links to one or more `Draft` records. `home` and `header` are protected system routes.

| Field | Django Type | null | blank | default | editable | Notes |
|-------|-------------|------|-------|---------|----------|-------|
| `id` | AutoField (PK) | | | auto | | |
| `url` | CharField(256) | | | | | Unique (see constraint); e.g., `"home"`, `"about-us"` |
| `label` | CharField(256) | | Yes | `""` | | Nav link label |
| `placement` | CharField(12, choices) | | | `"top"` | | `Route.Placement` choices |
| `drafts` | ManyToManyField → `Draft` | | | | | `related_name="routes"` |
| `created_at` | DateTimeField | | | `now` | No | Set explicitly in `save()` on create |
| `updated_at` | DateTimeField | | | `now` | No | Always updated in `save()` |

**Unique Constraints:**

| Name | Fields |
|------|--------|
| `route_is_unique` | `url` |

**Custom `save()`:** Sets `created_at = timezone.now()` on first save; always sets `updated_at = timezone.now()`.

**Custom `delete()` — delete protection:**

Raises `Exception("Cannot delete home route")` if `url == "home"` and `bypass` is not `True`.
Raises `Exception("Cannot delete header route")` if `url == "header"` and `bypass` is not `True`.

```python
route.delete()            # raises for home/header
route.delete(bypass=True) # skips protection
```

**`__str__`:** Returns `url`.

---

## Attribute System

Four models provide typed metadata that can be attached to `Content` records.

### Attribute

**File:** `models/attribute.py`

Defines a typed metadata field. Type is expressed via exactly one `is_*` boolean flag being `True`.

| Field | Django Type | null | blank | default | editable | Notes |
|-------|-------------|------|-------|---------|----------|-------|
| `id` | AutoField (PK) | | | auto | | |
| `slug` | CharField(64) | | | | No | Auto-generated from `label` via `python-slugify`; unique |
| `label` | CharField(64) | | | | | Human-readable name; drives slug generation |
| `is_bool` | BooleanField | | | `False` | | Value type: boolean |
| `is_int` | BooleanField | | | `False` | | Value type: integer |
| `is_txt` | BooleanField | | | `False` | | Value type: short text (max 128) |
| `is_txt_t9n` | BooleanField | | | `False` | | Value type: translatable text (JSONField); `NotImplementedError` in current code |
| `is_txt_long` | BooleanField | | | `False` | | Value type: long text (max 2048) |
| `is_datetime` | BooleanField | | | `False` | | Value type: datetime |
| `is_filterable` | BooleanField | | | `False` | | Whether values can be used as filters |
| `is_searchable` | BooleanField | | | `False` | | Whether values are indexed for search |
| `is_comparable` | BooleanField | | | `False` | | Whether values support comparison |
| `allow_new_values` | BooleanField | | | `True` | | Whether new `AttributeValue` records can be created |
| `allow_many_values` | BooleanField | | | `False` | | Whether a `Content` can have multiple values for this attribute |
| `created_at` | DateTimeField | | | auto | No | `auto_now_add=True` |
| `updated_at` | DateTimeField | | | auto | No | `auto_now=True` |

**Unique Constraints:**

| Name | Fields |
|------|--------|
| `attribute_slug_is_unique` | `slug` |

**Custom `save()`:** Calls `slugify(self.label)` and stores result in `slug` before every save.

**Properties:**

| Property | Returns | Notes |
|----------|---------|-------|
| `type_as_str` | `str` | `"bool"` / `"int"` / `"txt"` / `"txt_long"` / `"datetime"` — raises `NotImplementedError` for `is_txt_t9n` |

**Methods:**

| Method | Signature | Behavior |
|--------|-----------|---------|
| `parse_value` | `(value) -> Any` | Parses a raw string into the typed value; uses `dateutil.parser.parse` for datetime; raises `NotImplementedError` for `is_txt_t9n` |

**`__str__`:** Returns `slug`.

---

### AttributeSet

**File:** `models/attribute_set.py`

Named group of `Attribute` records. Assigned to `ContentType` to define which attributes apply to a content type.

| Field | Django Type | null | blank | default | editable | Notes |
|-------|-------------|------|-------|---------|----------|-------|
| `id` | AutoField (PK) | | | auto | | |
| `slug` | CharField(64) | | | | No | Auto-generated from `label`; unique |
| `label` | CharField(64) | | | | | Human-readable name |
| `attributes` | ManyToManyField → `Attribute` | | | | | Through: `AttributeToSet`; `related_name="attribute_sets"` |
| `created_at` | DateTimeField | | | auto | No | `auto_now_add=True` |
| `updated_at` | DateTimeField | | | auto | No | `auto_now=True` |

**Unique Constraints:**

| Name | Fields |
|------|--------|
| `attribute_set_slug_is_unique` | `slug` |

**Custom `save()`:** Calls `slugify(self.label)` and stores result in `slug` before every save.

**`__str__`:** Returns `slug`.

---

### AttributeValue

**File:** `models/attribute_value.py`

Holds the typed value for a specific `Attribute`. Exactly one `value_*` field will be populated, matching the attribute's type flag.

| Field | Django Type | null | blank | default | editable | Notes |
|-------|-------------|------|-------|---------|----------|-------|
| `id` | AutoField (PK) | | | auto | | |
| `attribute` | ForeignKey → `Attribute` | | | | | `on_delete=CASCADE`; `related_name="values"` |
| `value_bool` | BooleanField | Yes | Yes | | | Populated when `attribute.is_bool` |
| `value_int` | IntegerField | Yes | Yes | | | Populated when `attribute.is_int` |
| `value_txt` | CharField(128) | Yes | Yes | | | Populated when `attribute.is_txt` |
| `value_txt_t9n` | JSONField | Yes | Yes | | | Populated when `attribute.is_txt_t9n` (unimplemented) |
| `value_txt_long` | CharField(2048) | Yes | Yes | | | Populated when `attribute.is_txt_long` |
| `value_datetime` | DateTimeField | Yes | Yes | | | Populated when `attribute.is_datetime` |
| `created_at` | DateTimeField | | | auto | No | `auto_now_add=True` |
| `updated_at` | DateTimeField | | | auto | No | `auto_now=True` |

**Properties:**

| Property | Returns | Notes |
|----------|---------|-------|
| `value` | typed value | Reads the correct `value_*` field based on `attribute.is_*` flags; raises `NotImplementedError` for `is_txt_t9n`; raises `Exception` for unknown type |

**`__str__`:** Returns `"{value} of {attribute.label}"`.

---

### AttributeToSet

**File:** `models/attribute_to_set.py`

Through table for the `AttributeSet.attributes` M2M relationship.

| Field | Django Type | null | blank | Notes |
|-------|-------------|------|-------|-------|
| `id` | AutoField (PK) | | | |
| `attribute_set` | ForeignKey → `AttributeSet` | | | `on_delete=CASCADE` |
| `attribute` | ForeignKey → `Attribute` | | | `on_delete=CASCADE` |

No additional constraints or methods.

---

### ContentAttribute

**File:** `models/content_attribute.py`

Through table for the `Content.attributes` M2M relationship.

| Field | Django Type | null | blank | Notes |
|-------|-------------|------|-------|-------|
| `id` | AutoField (PK) | | | |
| `content` | ForeignKey → `Content` | | | `on_delete=CASCADE` |
| `attribute_value` | ForeignKey → `AttributeValue` | | | `on_delete=CASCADE` |

No additional constraints or methods.

---

## Media

### Image

**File:** `models/image.py`

Stores an uploaded image using content-addressed (SHA256) storage to deduplicate files on disk.

| Field | Django Type | null | blank | default | editable | Notes |
|-------|-------------|------|-------|---------|----------|-------|
| `id` | AutoField (PK) | | | auto | | |
| `uid` | UUIDField | | | `uuid.uuid4` | No | External identifier |
| `meta` | JSONField | Yes | Yes | | | Optional metadata blob |
| `tags` | ManyToManyField → `ImageTag` | | | | | Through: `ImageToTag` |
| `image` | HashedImageField | | | | No | `upload_to="image"`; `storage=UniqueFileSystemStorage()`; auto-populates `width`/`height` |
| `width` | PositiveSmallIntegerField | Yes | Yes | | No | Auto-set via `height_field`/`width_field` on `HashedImageField` |
| `height` | PositiveSmallIntegerField | Yes | Yes | | No | Auto-set on upload |
| `created_at` | DateTimeField | | | auto | No | `auto_now_add=True` |
| `updated_at` | DateTimeField | | | auto | No | `auto_now=True` |

**Meta:** `ordering = ["-created_at", "-updated_at"]`

**Custom `delete()`:** Calls `self.image.delete(self.image.path)` to remove the file from disk before deleting the DB row.

**`__str__`:** Returns `str(uid)`.

**HashedImageField behavior:**

1. On upload, optionally downscales the image to `CONTENTDB_IMAGE_MAX_WIDTH` (default 2560 px), preserving aspect ratio. Uses `image_transformations.resize_ratio_safe` if available, falls back to Pillow.
2. Computes SHA256 of the (possibly resized) file content.
3. Derives storage path: `{upload_to}/{hash[0:2]}/{hash[2:4]}/{hash[4:]}.{ext}` — e.g., `image/aa/bb/cccccccc....jpg`.
4. Same file uploaded twice → same hash → same path → deduplicated on disk.

---

### Thumbnail

**File:** `models/thumbnail.py`

Derived image produced from a source `Image`. Unique per processing method + source + dimensions.

| Field | Django Type | null | blank | default | editable | Notes |
|-------|-------------|------|-------|---------|----------|-------|
| `id` | AutoField (PK) | | | auto | | |
| `method` | CharField(32, choices) | | | | No | `Thumbnail.ProcessingMethod` choices; currently only `"optimize"` |
| `source` | ForeignKey → `Image` | | | | No | `on_delete=CASCADE`; `related_name="thumbnails"` |
| `image` | HashedImageField | | | | No | `upload_to="thumb"`; `storage=UniqueFileSystemStorage()`; auto-populates `width`/`height` |
| `width` | PositiveSmallIntegerField | Yes | Yes | | No | Auto-set on upload |
| `height` | PositiveSmallIntegerField | Yes | Yes | | No | Auto-set on upload |
| `created_at` | DateTimeField | | | auto | No | `auto_now_add=True` |
| `updated_at` | DateTimeField | | | auto | No | `auto_now=True` |

**Unique Constraints:**

| Name | Fields |
|------|--------|
| `unique_thumbnail_per_source_per_method_per_size` | `method`, `source`, `width`, `height` |

**Custom `delete()`:** Calls `self.image.delete(self.image.path)` to remove the thumbnail file from disk.

**`__str__`:** Returns `self.image.path`.

---

### ImageTag

**File:** `models/image_tag.py`

Label record for categorising images. Linked to `Image` via `ImageToTag`.

| Field | Django Type | null | blank | Notes |
|-------|-------------|------|-------|-------|
| `id` | AutoField (PK) | | | |
| `slug` | SlugField(64) | | | Unique (see constraint) |
| `label` | CharField(64) | | | Human-readable name |

**Unique Constraints:**

| Name | Fields |
|------|--------|
| `unique_slug` | `slug` |

**`__str__`:** Returns `slug`.

---

### ImageToTag

**File:** `models/image_to_tag.py`

Through table for the `Image.tags` M2M relationship. Prevents duplicate tag assignments.

| Field | Django Type | null | blank | Notes |
|-------|-------------|------|-------|-------|
| `id` | AutoField (PK) | | | |
| `image` | ForeignKey → `Image` | | | `on_delete=CASCADE` |
| `tag` | ForeignKey → `ImageTag` | | | `on_delete=CASCADE` |

**Unique Constraints:**

| Name | Fields |
|------|--------|
| `unique_tag_per_image` | `image`, `tag` |

**`__str__`:** Returns `f"{image} => {tag}"`.

---

## Access Control

### AccessRights

**File:** `models/access_rights.py`

Access level descriptor. `access_level` is both the semantic value and the primary key.

| Field | Django Type | null | blank | default | Notes |
|-------|-------------|------|-------|---------|-------|
| `access_level` | IntegerField | | | `0` | **Primary key** (`primary_key=True`); `unique=True` implied by PK |

**Key convention:** `pk=1` = public access. There is no auto-increment; values must be inserted explicitly.

**`__str__`:** Returns `f"{access_level}"`.

**Reverse relations:**
- `access_rights.draft_access` — all `Draft` records that include this access level.

---

### Language

**File:** `models/language.py`

ISO language descriptor. Referenced by `Draft` and `Category`.

| Field | Django Type | null | blank | Notes |
|-------|-------------|------|-------|-------|
| `id` | AutoField (PK) | | | |
| `iso3` | CharField(3) | | | Three-letter ISO code; unique |
| `iso2` | CharField(2) | | | Two-letter ISO code; unique |

**Unique Constraints:**

| Name | Fields |
|------|--------|
| `unique_iso2_per_language` | `iso2` |
| `unique_iso3_per_language` | `iso3` |

**`__str__`:** Returns `iso2`.

---

### Category

**File:** `models/category.py`

Content category. `url_key` is auto-generated from `name` via slugification and URL normalization.

| Field | Django Type | null | blank | default | editable | Notes |
|-------|-------------|------|-------|---------|----------|-------|
| `id` | AutoField (PK) | | | auto | | |
| `uid` | UUIDField | | | `uuid.uuid4` | No | External identifier |
| `name` | CharField(256) | | | | | Display name |
| `url_key` | CharField(256) | | | | | SEO-friendly key; auto-derived from `name` if blank |
| `language` | ForeignKey → `Language` | Yes | Yes | | | `on_delete=SET_NULL` |
| `created_at` | DateTimeField | | | auto | No | `auto_now_add=True` |
| `updated_at` | DateTimeField | | | auto | No | `auto_now=True` |

**Meta:** `verbose_name_plural = "Categories"`

**Custom `save()`:**

- If `url_key` is blank/empty: generates from `name` via `slugify(name)` then `normalize_url_key(slug)`.
- If `url_key` is provided: normalizes it with `generate_url_key(url_key)`.
- Uses `idx_normalizator.normalize_url_key` from the `idx-normalizator` package.

**Methods:**

| Method | Signature | Behavior |
|--------|-----------|---------|
| `generate_url_key` | `(name: str, max_length: int = 256) -> str` | Slugifies `name`, truncates to `max_length`, then normalizes |

**`__str__`:** Returns `f"{name} ({language.iso2})"` if language is set; otherwise `name`.

---

### ContentTypePermission

**File:** `models/content_type_permission.py`

Permission rule binding an `Action` to a `ContentType`, with optional user/group assignments.

| Field | Django Type | null | blank | default | editable | Notes |
|-------|-------------|------|-------|---------|----------|-------|
| `id` | AutoField (PK) | | | auto | | |
| `action` | CharField(12, choices) | | | | | `Action` choices |
| `content_type` | ForeignKey → `ContentType` | | | | | `on_delete=CASCADE`; `related_name="user_permissions"` |
| `user` | ManyToManyField → `AUTH_USER_MODEL` | | Yes | | | Users granted the permission |
| `group` | ManyToManyField → `auth.Group` | | Yes | | | Groups granted the permission |
| `created_at` | DateTimeField | | | `now` | No | Set in `save()` on create |
| `updated_at` | DateTimeField | | | `now` | No | Always updated in `save()` |

**Unique Constraints:**

| Name | Fields |
|------|--------|
| `unique_action_per_type_per_permission` | `action`, `content_type` |

**Custom `save()`:** Sets `created_at = timezone.now()` on first save; always sets `updated_at = timezone.now()`.

**`__str__`:** Returns `f"{action} -> {content_type}"`.

**Runtime usage:** The `permissions.py` `ContentTypePermission` DRF permission class checks this model by looking up the URL kwarg `content_type` to resolve the `ContentType`, then verifying that the requesting user (directly or via group) has the required action.

---

## Workflow

### ContentSet

**File:** `models/content_set.py`

Named collection of `Draft` records, enabling bulk operations across multiple pieces of content.

| Field | Django Type | null | blank | default | editable | Notes |
|-------|-------------|------|-------|---------|----------|-------|
| `id` | AutoField (PK) | | | auto | | |
| `uid` | UUIDField | | | `uuid.uuid4` | No | External identifier |
| `members` | ManyToManyField → `Draft` | | | | | Through: `DraftToContentSet` |
| `created_at` | DateTimeField | | | auto | No | `auto_now_add=True` |
| `updated_at` | DateTimeField | | | auto | No | `auto_now=True` |

**`__str__`:** Returns `str(uid)`.

---

### DraftToContentSet

**File:** `models/draft_to_content_set.py`

Through table for `ContentSet.members`. Enforces that each `Draft` belongs to at most one `ContentSet`.

| Field | Django Type | null | blank | Notes |
|-------|-------------|------|-------|-------|
| `id` | AutoField (PK) | | | |
| `content_set` | ForeignKey → `ContentSet` | | | `on_delete=CASCADE` |
| `draft` | ForeignKey → `Draft` | | | `on_delete=CASCADE` |

**Unique Constraints:**

| Name | Fields |
|------|--------|
| `draft_unique_per_table` | `draft` |

This constraint means a `Draft` can only be a member of one `ContentSet` at a time.

---

### ActivityLog

**File:** `models/activity_log.py`

Append-only audit trail for actions performed on any model via the admin API ViewSets. Uses Django's `GenericForeignKey` to reference any target object.

| Field | Django Type | null | blank | Notes |
|-------|-------------|------|-------|-------|
| `id` | AutoField (PK) | | | |
| `action` | CharField(12, choices) | | | `Action` choices |
| `content_type` | ForeignKey → `django.contrib.contenttypes.ContentType` | | | `on_delete=CASCADE`; part of GenericFK |
| `object_id` | PositiveIntegerField | | | Part of GenericFK |
| `target` | GenericForeignKey | | | `("content_type", "object_id")` — resolved at runtime |
| `user` | ForeignKey → `AUTH_USER_MODEL` | | | `on_delete=CASCADE` |
| `created_at` | DateTimeField | | | auto | `auto_now_add=True` |

**`__str__`:** Returns `f"{user} performed {action} on {target} | {created_at}"`.

**Usage:** `ContentDBModelViewSet` (base class in `viewsets.py`) automatically writes an `ActivityLog` entry on every mutating request.

---

### Deleted

**File:** `models/deleted.py`

Soft-delete audit record. Created when a `Content` is flagged for deletion rather than immediately removing it from the database.

| Field | Django Type | null | blank | Notes |
|-------|-------------|------|-------|-------|
| `id` | AutoField (PK) | | | |
| `content` | OneToOneField → `Content` | | | `on_delete=CASCADE`; unique — one `Deleted` record per `Content` |
| `created_at` | DateTimeField | | | auto | `auto_now_add=True` |

No additional methods or constraints.

---

## Unique Constraints Summary

All `UniqueConstraint` declarations and `unique=True` fields across the module.

| Model | Constraint name | Fields |
|-------|----------------|--------|
| `AccessRights` | (field-level `unique=True`) | `access_level` (also PK) |
| `Attribute` | `attribute_slug_is_unique` | `slug` |
| `AttributeSet` | `attribute_set_slug_is_unique` | `slug` |
| `ContentType` | `content_type_slug_is_unique` | `slug` |
| `ContentTypePermission` | `unique_action_per_type_per_permission` | `action`, `content_type` |
| `DraftToContentSet` | `draft_unique_per_table` | `draft` |
| `ImageTag` | `unique_slug` | `slug` |
| `ImageToTag` | `unique_tag_per_image` | `image`, `tag` |
| `Language` | `unique_iso2_per_language` | `iso2` |
| `Language` | `unique_iso3_per_language` | `iso3` |
| `Route` | `route_is_unique` | `url` |
| `Thumbnail` | `unique_thumbnail_per_source_per_method_per_size` | `method`, `source`, `width`, `height` |

---

## Django Admin Configuration

All registered admin classes with their notable features.

| Model | Admin class | list_display | list_filter | search_fields | Inlines | Notable |
|-------|-------------|-------------|-------------|---------------|---------|---------|
| `AccessRights` | `AccessRightsAdmin` | (default) | — | — | — | |
| `Attribute` | `AttributeAdmin` | (default) | — | — | `AttributeValueInline` | Inline value management |
| `AttributeSet` | `AttributeSetAdmin` | (default) | — | — | `AttributeToSetInline` | Tabular attribute membership |
| `Route` | `RouteAdmin` | url, label, placement, created_at, updated_at, len_drafts, list_drafts | placement, created_at, updated_at, drafts__language__iso2, drafts__access_rights__access_level | url, label, drafts__content__uid | — | `filter_horizontal` for drafts; custom columns for draft count and list |
| `ContentTypePermission` | `ContentTypePermissionAdmin` | action, content_type, users, groups | action, content_type | content_type__name | — | Custom `users` and `groups` columns (email / group name) |
| `ContentType` | `ContentTypeAdmin` | slug, label, attribute_set, is_layout_extender, created_at, updated_at | is_layout_extender, attribute_set | slug, label | — | `readonly_fields`: created_at, updated_at |
| `ContentSet` | `ContentSetAdmin` | (default) | — | — | `DraftInline` (StackedInline of `DraftToContentSet`) | |
| `Content` | `ContentAdmin` | uid, category, draft_language, draft_access_rights, created_at, content_type_slug, updated_at | attributes, created_at, updated_at, draft__access_rights__access_level, draft__language__iso2, draft__content_type, category | uid | `ContentAttributeInline` | `readonly_fields`: prettified JSON for content, meta, extension; `autocomplete_fields`: category |
| `Draft` | `DraftAdmin` | content, name, content_type, language, created_at | content_type, language__iso2, access_rights__access_level, created_at | name | — | `filter_horizontal` for access_rights; custom `category` column |
| `Published` | `PublishedAdmin` | content, draft, created_at | content__draft__access_rights__access_level, content__draft__language__iso2 | content | — | `readonly_fields`: created_at |
| `Deleted` | `DeletedAdmin` | (default) | content__draft__access_rights__access_level, content__draft__language__iso2 | — | — | |
| `ImageTag` | `ImageTagAdmin` | slug, label | — | — | — | |
| `Image` | `ImageAdmin` | uid, created_at, updated_at, width, height, image_path, all_tags | tags, created_at, updated_at | uid, tags__name | `ImageTagInline`, `ThumbnailInline` | `readonly_fields`: prettified JSON for meta; custom `image_path` and `all_tags` columns |
| `Thumbnail` | `ThumbnailAdmin` | source, method, image, width, height, created_at, updated_at | method, created_at, updated_at | source__uid | — | |
| `ActivityLog` | `ActivityLogAdmin` | (default) | user, action | user__email | — | `readonly_fields`: action, user, content_type, object_id |
| `Language` | `LanguageAdmin` | iso2, iso3 | — | — | — | |
| `Category` | `CategoryAdmin` | uid, name, url_key, language, created_at, updated_at | language | uid, name, url_key | — | `readonly_fields`: created_at, updated_at |

---

## Settings Reference

All settings are read from Django's `settings` module with a module-specific default.

| Django setting name | Module constant | Default | Description |
|--------------------|----------------|---------|-------------|
| `API_ADMIN_BASE_URL` | `ADMIN_BASE_URL` | `"/api-admin/"` | URL prefix for admin API endpoints |
| `API_PUBLIC_BASE_URL` | `PUBLIC_BASE_URL` | `"/api/"` | URL prefix for public API endpoints |
| `CONTENTDB_THUMBNAIL_QUALITY` | `THUMBNAIL_QUALITY` | `60` | JPEG quality for generated thumbnails (0–100) |
| `CONTENTDB_IMAGE_MAX_WIDTH` | `CONTENTDB_IMAGE_MAX_WIDTH` | `2560` | Maximum upload width in pixels; `0` disables resize |

---

## Utility Classes

### HashedImageField / HashedImageFieldFile

**File:** `utils.py`

Custom `ImageField` subclass that uses SHA256 content-addressing for storage.

**Storage path formula:**

```
{upload_to}/{sha256[0:2]}/{sha256[2:4]}/{sha256[4:]}.{ext}
# Example: image/aa/bb/cccccccccccccccccccccccccccccccccccccccccccccccccccc.jpg
```

**Upload pipeline (in `HashedImageFieldFile.save()`):**

1. Call `_maybe_resize_image()` — downscale if wider than `CONTENTDB_IMAGE_MAX_WIDTH`; uses `image_transformations.resize_ratio_safe` then falls back to Pillow `LANCZOS` resize.
2. Call `_get_content_name()` — compute SHA256 of processed content, derive path.
3. Delegate to Django's standard `ImageField.save()` with the computed path.

**Deduplication:** uploading the same file twice produces the same hash and thus the same path. `UniqueFileSystemStorage` handles conflicts via Django's alternative name generation.

### StandardPagination

**File:** `utils.py`

DRF `PageNumberPagination` subclass used by all contentdb viewsets.

| Parameter | Value |
|-----------|-------|
| `page_query_param` | `"page"` |
| `page_size` | `6` |
| `page_size_query_param` | `"limit"` |
| `max_page_size` | `100` |

Response envelope adds a `pagination` key:

```json
{
  "meta": {"status": "OK", "message": ""},
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 6,
    "pages": 5,
    "records": 30
  }
}
```

### ImageManager

**File:** `image_manager.py`

PIL utility class. Used internally by Celery tasks for image post-processing.

| Method | Signature | Description |
|--------|-----------|-------------|
| `check_or_create_dir` | `(path) -> bool` | Creates directory if missing |
| `is_image` | `(filename: str) -> bool` | Checks extension against `ImageExtension` enum |
| `get_extension` | `(filename: str) -> str` | Returns file extension including dot |
| `set_extension` | `(filename: str, ext: ImageExtension) -> str` | Replaces file extension |
| `open_image` | `(path: str) -> ImageClass` | Opens PIL Image |
| `save_image` | `(image, path, quality=70, optimize=True) -> None` | Saves PIL Image |
| `delete_image` | `(path: str) -> None` | Deletes file from disk |
| `remove_transparency` | `(image, fill_with="WHITE") -> ImageClass` | Flattens RGBA to RGB |
| `resize_fill_crop` | `(image, out_x, out_y) -> ImageClass` | Resizes with `ImageOps.fit`/`pad` |

`ImageExtension` enum values: `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp`
