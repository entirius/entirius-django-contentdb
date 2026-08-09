---
title: CMS Configuration
description: CMS Blueprint configuration system for ContentDB — config files, variant matching, section/tile types, and prop definitions.
---

## Config Directory

CMS Blueprint uses a layered config system:

```
cms-blueprint/
├── __client_default/    # Committed defaults (base config)
│   ├── configs/         # Section/tile types, options, constraints
│   └── props/           # Property definitions, handlers, group fields
└── __client/            # Gitignored client overrides (takes priority)
    ├── configs/
    └── props/
```

On `npm run serve` or `npm run build`, `scripts/init-client.js` copies only **missing** files from `__client_default/` to `__client/`. Existing `__client/` files are preserved.

## Config Files

### configs/

| File | Purpose |
|------|---------|
| `__core_config.json` | Section and tile type definitions with `core_type` and `variant` dropdowns. Defines all 17 section types and 13 tile types |
| `__hidden_config.json` | Internal configs not shown to users: `doc_type` (document type) and `section_core_type` (tile-section dependency) |
| `__optional_config.json` | Optional config dropdowns: `dye`, `width`, `tile_align`, `margin`, `banner_type`, `grid`, `grid_mobile`, `grid_desktop`, `form_type`, `rating` |
| `__config_options.json` | Per-section constraints like `max_tiles` |

### props/

| File | Purpose |
|------|---------|
| `__props.json` | Property definitions: `title`, `description`, `images_set`, `custom_buttons`, `accordion_tile`, etc. Each has type, label, and `variants_group` controlling visibility |
| `__props_handlers.json` | Maps prop types to Vue components: `text` -> `BasicInput`, `wysiwyg` -> `BasicWysiwyg`, `images` -> `ImagesController`, `group-fields` -> `GroupFieldsController` |
| `__props_options.json` | Group field structures for complex props: `simple_button`, `accordion_tile`, `chart_tile`, `form_tile`, `consents`, `blog_section` |

## Config Structure

Each config file is a JSON array of config entries. An entry has:

```json
{
  "prop": "core_type",
  "label": "Type",
  "type": "dropdown",
  "__value": null,
  "_for": {
    "section_configs": [
      { "label": "Hero slider", "value": "section-hero-slider", "variants": [...] }
    ],
    "tile_configs": [
      { "label": "Hero tile", "value": "tile-hero", "variants": [...] }
    ]
  },
  "_dependent": null,
  "hidden": false
}
```

`_for.section_configs` lists options available for sections. `_for.tile_configs` lists options for tiles. Each option has `variants` controlling when it appears.

## Variant Matching

Variants control conditional visibility of options based on current config values. Format: `"prop:value"` strings in arrays.

```json
// OR logic — show if doc_type is static-page OR blog-post:
"variants": [
  ["doc_type:static-page"],
  ["doc_type:blog-post"]
]

// AND logic — all conditions in one array must match:
"variants": [
  ["section_core_type:section-image-text", "core_type:tile-txt-btn"]
]
```

Each inner array is an AND group. The outer array is OR — if any inner array fully matches, the option is visible.

Variant strings must **exactly** match the `prop:value` format. Typos cause silent failures — the option simply never appears.

The matching logic lives in `src/composables/useVariantMatching.js`.

## Props Structure

Props in `__props.json` use `variants_group` (not `variants`) to control visibility:

```json
{
  "prop": "title",
  "type": "text",
  "label": "Title",
  "__value": null,
  "_for": {
    "section_configs": [{
      "variants_group": [
        ["core_type:section-content-slider"],
        ["core_type:section-banner"],
        ["core_type:section-text"]
      ],
      "related_options": null
    }],
    "tile_configs": [{
      "variants_group": [
        ["core_type:tile-hero"],
        ["core_type:tile-testimonial"]
      ],
      "related_options": null
    }]
  }
}
```

For `group-fields` type props, `related_options` points to a key in `__props_options.json` that defines the repeatable field structure.

## Adding a New Section Type

1. Add option to `__core_config.json` `_for.section_configs` with appropriate `variants`
2. Add the section's props to `__props.json` by including the new `core_type` in each prop's `variants_group`
3. Add optional configs in `__optional_config.json` if the section needs dye, width, margin, etc.
4. Set `max_tiles` in `__config_options.json`
5. Add corresponding tile types to `__core_config.json` `_for.tile_configs` with `section_core_type` variant

## Adding a New Tile Type

1. Add option to `__core_config.json` `_for.tile_configs` with `section_core_type` variant
2. Add the tile's props to `__props.json` by including the new `core_type` in each prop's `variants_group`
3. Create a storefront Vue component: `Tiles/Tile-{Name}/index.vue`
4. Register the component in `Tiles/index.js`

## Adding a New Prop

**Simple prop** (text, wysiwyg):

Add entry to `__props.json` with type, label, and `variants_group` targeting the relevant section/tile types.

**Complex prop** (group-fields):

1. Add entry to `__props.json` with `"type": "group-fields"` and `"related_options": "option_key"`
2. Add the field structure to `__props_options.json` under that option key with `fields` and `group_rules.max`

See [Rich Content Building](/cynthia/cms/rich-content-building/) for the complete section/tile catalog, dye system, and config options reference.
