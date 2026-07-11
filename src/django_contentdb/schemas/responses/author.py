# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuthorBriefResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uid: UUID = Field(description="Author UUID", examples=["d0000001-0001-4000-8000-000000000001"])
    name: str = Field(description="Author display name", examples=["Anna Kowalska"])
    slug: str = Field(description="URL slug", examples=["anna-kowalska"])
    role_t9n: dict[str, str] = Field(description="Role per language", examples=[{"en": "Editor"}])
    description_t9n: dict[str, str] = Field(default_factory=dict, description="Bio per language", examples=[{}])
    photo_uid: UUID | None = Field(None, description="Photo image UUID", examples=[None])
    photo_url: str | None = Field(None, description="Photo image URL", examples=[None])
    is_active: bool = Field(default=True, description="Whether author is active", examples=[True])


class AuthorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uid: UUID = Field(description="Author UUID", examples=["a0000001-0001-4000-8000-000000000001"])
    name: str = Field(description="Author display name", examples=["Anna Kowalska"])
    slug: str = Field(description="URL slug", examples=["anna-kowalska"])
    role_t9n: dict[str, str] = Field(description="Role per language", examples=[{"en": "Editor"}])
    description_t9n: dict[str, str] = Field(description="Bio per language", examples=[{}])
    tag_t9n: dict[str, str] = Field(description="Short tag per language", examples=[{}])
    photo_uid: UUID | None = Field(None, description="Photo image UUID", examples=[None])
    photo_url: str | None = Field(None, description="Photo image URL", examples=[None])
    contact_email: str = Field(description="Contact email", examples=["anna@example.com"])
    contact_phone: str = Field(description="Contact phone", examples=["+48 123 456 789"])
    contact_url: str = Field(description="Personal website URL", examples=["https://example.com"])
    social_profiles: dict = Field(description="Social media links", examples=[{}])
    is_active: bool = Field(description="Whether author is active", examples=[True])
    published_post_count: int = Field(description="Number of published blog posts", examples=[5])


class AuthorListResponse(BaseModel):
    count: int = Field(description="Total number of authors", examples=[10])
    next: str | None = Field(None, description="URL for next page", examples=[None])
    previous: str | None = Field(None, description="URL for previous page", examples=[None])
    results: list[AuthorResponse] = Field(description="List of authors", examples=[[]])
