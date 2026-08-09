---
title: "ContentDB: Database Diagrams"
description: "Auto-generated ER diagrams for the ContentDB module."
sidebar:
  badge:
    text: "Auto-gen"
    variant: "note"
---

:::caution[Auto-generated]
These diagrams are auto-generated from Django model introspection.
Do not edit. Run `make erd` in entirius-docker to regenerate.
:::

## Content Pipeline

```d2 layout=elk
Content: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  category_id: int {constraint: foreign_key}
  uid: uuid
  content: jsonb
  extension: jsonb
  meta: jsonb
}

ContentType: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  attribute_set_id: int {constraint: foreign_key}
  slug: varchar
  "label": varchar
  is_layout_extender: bool
}

Draft: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  content_type_id: int {constraint: foreign_key}
  content_id: int {constraint: foreign_key}
  language_id: int {constraint: foreign_key}
  name: varchar
}

Published: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  draft_id: int {constraint: foreign_key}
  content_id: int {constraint: foreign_key}
}

Route: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  url: varchar
  "label": varchar
  placement: varchar
  created_at: timestamp
  updated_at: timestamp
}

Language: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  iso3: varchar
  iso2: varchar
  name_en: varchar
  name_pl: varchar
}

AccessRights: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  access_level: int {constraint: primary_key}
}

ContentChannel: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  idx: varchar {constraint: unique}
  default_language_id: int {constraint: foreign_key}
  name: varchar
  is_default: bool
}

Category: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  language_id: int {constraint: foreign_key}
  uid: uuid
  name: varchar
  url_key: varchar
}

ContentSet: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  uid: uuid
}

DraftToContentSet: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  content_set_id: int {constraint: foreign_key}
  draft_id: int {constraint: foreign_key}
}

Deleted: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  content_id: int {constraint: foreign_key}
}

AttributeSet: {
  shape: sql_table
  style.fill: "#484B57"
  style.stroke: "#1A1C25"
  style.stroke-dash: 3
  style.font-color: "#9A9CAA"
  id: int {constraint: primary_key}
  label: "AttributeSet (See attributes diagram)"
}



Content.category_id -> Category.id: {style.stroke: "#00ACC1"}

ContentType.attribute_set_id -> AttributeSet.id: {style.stroke: "#484B57"}

Draft.content_type_id -> ContentType.id: {style.stroke: "#00ACC1"}

Draft.content_id -> Content.id: {style.stroke: "#00ACC1"}

Draft.language_id -> Language.id: {style.stroke: "#00ACC1"}

Draft.id <-> AccessRights.access_level: {style.stroke: "#00ACC1"}

Draft.id <-> ContentChannel.id: {style.stroke: "#00ACC1"}

Published.draft_id -> Draft.id: {style.stroke: "#00ACC1"}

Published.content_id -> Content.id: {style.stroke: "#00ACC1"}

Route.id <-> Draft.id: {style.stroke: "#00ACC1"}

ContentChannel.default_language_id -> Language.id: {style.stroke: "#00ACC1"}

Category.language_id -> Language.id: {style.stroke: "#00ACC1"}

DraftToContentSet.content_set_id -> ContentSet.id: {style.stroke: "#00ACC1"}

DraftToContentSet.draft_id -> Draft.id: {style.stroke: "#00ACC1"}

Deleted.content_id -> Content.id: {style.stroke: "#00ACC1"}
```

## Attributes

```d2 layout=elk
Attribute: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  slug: varchar
  "label": varchar
  is_bool: bool
  is_int: bool
  is_txt: bool
  is_txt_t9n: bool
  is_txt_long: bool
}

AttributeSet: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  slug: varchar
  "label": varchar
}

AttributeToSet: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  attribute_set_id: int {constraint: foreign_key}
  attribute_id: int {constraint: foreign_key}
}

AttributeValue: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  attribute_id: int {constraint: foreign_key}
  value_bool: bool
  value_int: int
  value_txt: varchar
  value_txt_t9n: jsonb
  value_txt_long: varchar
  value_datetime: timestamp
}

ContentAttribute: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  content_id: int {constraint: foreign_key}
  attribute_value_id: int {constraint: foreign_key}
}

Content: {
  shape: sql_table
  style.fill: "#484B57"
  style.stroke: "#1A1C25"
  style.stroke-dash: 3
  style.font-color: "#9A9CAA"
  id: int {constraint: primary_key}
  label: "Content (See content-pipeline diagram)"
}



AttributeToSet.attribute_set_id -> AttributeSet.id: {style.stroke: "#00ACC1"}

AttributeToSet.attribute_id -> Attribute.id: {style.stroke: "#00ACC1"}

AttributeValue.attribute_id -> Attribute.id: {style.stroke: "#00ACC1"}

ContentAttribute.content_id -> Content.id: {style.stroke: "#484B57"}

ContentAttribute.attribute_value_id -> AttributeValue.id: {style.stroke: "#00ACC1"}
```

## Media

```d2 layout=elk
Image: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  uid: uuid
  meta: jsonb
  image: varchar
  "width": int
  "height": int
}

ImageTag: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  slug: varchar
  "label": varchar
}

ImageToTag: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  image_id: int {constraint: foreign_key}
  tag_id: int {constraint: foreign_key}
}

Thumbnail: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  source_id: int {constraint: foreign_key}
  method: varchar
  image: varchar
  "width": int
  "height": int
}



ImageToTag.image_id -> Image.id: {style.stroke: "#00ACC1"}

ImageToTag.tag_id -> ImageTag.id: {style.stroke: "#00ACC1"}

Thumbnail.source_id -> Image.id: {style.stroke: "#00ACC1"}
```

## Permissions & Audit

```d2 layout=elk
ContentTypePermission: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  content_type_id: int {constraint: foreign_key}
  action: varchar
  created_at: timestamp
  updated_at: timestamp
}

ActivityLog: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  content_type_id: int {constraint: foreign_key}
  user_id: int {constraint: foreign_key}
  action: varchar
  object_id: int
  None: varchar
}

ContentType: {
  shape: sql_table
  style.fill: "#484B57"
  style.stroke: "#1A1C25"
  style.stroke-dash: 3
  style.font-color: "#9A9CAA"
  id: int {constraint: primary_key}
  label: "ContentType (See content-pipeline diagram)"
}

Group: {
  shape: sql_table
  style.fill: "#484B57"
  style.stroke: "#1A1C25"
  style.stroke-dash: 3
  style.font-color: "#9A9CAA"
  id: int {constraint: primary_key}
  label: "Group (External: auth)"
}

User: {
  shape: sql_table
  style.fill: "#484B57"
  style.stroke: "#1A1C25"
  style.stroke-dash: 3
  style.font-color: "#9A9CAA"
  id: int {constraint: primary_key}
  label: "User (External: auth)"
}



ContentTypePermission.content_type_id -> ContentType.id: {style.stroke: "#484B57"}

ContentTypePermission.id <-> User.id: {style.stroke: "#484B57"}

ContentTypePermission.id <-> Group.id: {style.stroke: "#484B57"}

ActivityLog.content_type_id -> ContentType.id: {style.stroke: "#484B57"}

ActivityLog.user_id -> User.id: {style.stroke: "#484B57"}
```
