# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class NavigationLink(BaseModel):
    id: str = Field(description="UUID string identifier", examples=["550e8400-e29b-41d4-a716-446655440001"])
    label: str = Field(description="Display label for the link", examples=["Best sellers"])
    link_type: Literal["category", "page", "url"] = Field(description="Type of link target", examples=["category"])
    link_value: str = Field(
        description="Target value: category url_key, page route, or absolute URL",
        examples=["sofas"],
    )
    sort_order: int = Field(default=0, description="Display order within column", examples=[0])


class NavigationColumn(BaseModel):
    id: str = Field(description="UUID string identifier", examples=["550e8400-e29b-41d4-a716-446655440010"])
    type: Literal["links", "banner"] = Field(description="Column content type", examples=["links"])
    heading: str = Field(default="", description="Column heading (for links type)", examples=["Shop by Category"])
    sort_order: int = Field(default=0, description="Display order within item", examples=[0])
    links: list[NavigationLink] = Field(default_factory=list, description="Links in this column (for links type)")
    media_type: Literal["image", "video"] = Field(
        default="image", description="Media type (for banner type)", examples=["image"]
    )
    media_url: str = Field(default="", description="Media URL (for banner type)", examples=["/media/banner.jpg"])
    caption: str = Field(default="", description="Banner caption text", examples=["Explore our collection"])
    button_label: str = Field(default="", description="Banner CTA button label", examples=["Shop Now"])
    button_link_type: Literal["category", "page", "url"] = Field(
        default="url", description="Banner button link type", examples=["category"]
    )
    button_link_value: str = Field(default="", description="Banner button link target", examples=["del-mar"])
    alt_text: str = Field(default="", description="Accessibility alt text for banner media", examples=[""])


class NavigationItem(BaseModel):
    id: str = Field(description="UUID string identifier", examples=["550e8400-e29b-41d4-a716-446655440020"])
    label: str = Field(description="Top-level navigation label", examples=["FURNITURE"])
    display_as: Literal["link", "megamenu"] = Field(
        description="Display mode: simple link or expandable megamenu", examples=["megamenu"]
    )
    link_type: Literal["category", "page", "url"] = Field(
        description="Link type for the item itself", examples=["category"]
    )
    link_value: str = Field(default="", description="Link target value", examples=["furniture"])
    icon: str = Field(default="", description="Optional icon identifier", examples=[""])
    color: str = Field(default="", description="Optional hex color (#RRGGBB)", examples=[""])
    sort_order: int = Field(default=0, description="Display order in navigation bar", examples=[0])
    columns: list[NavigationColumn] = Field(
        default_factory=list, description="Megamenu columns (max 4, only for display_as=megamenu)"
    )

    @field_validator("columns")
    @classmethod
    def validate_max_columns(cls, v, info):
        display_as = info.data.get("display_as", "link")
        if display_as == "megamenu" and len(v) > 4:
            raise ValueError("Megamenu items cannot have more than 4 columns")
        return v


class NavigationContent(BaseModel):
    items: list[NavigationItem] = Field(default_factory=list, description="Top-level navigation items")
