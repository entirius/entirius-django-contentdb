# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import re
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SocialProfiles(BaseModel):
    twitter: str | None = Field(None, description="Twitter/X profile URL", examples=["https://x.com/author"])
    linkedin: str | None = Field(None, description="LinkedIn profile URL", examples=["https://linkedin.com/in/author"])
    github: str | None = Field(None, description="GitHub profile URL", examples=["https://github.com/author"])
    facebook: str | None = Field(None, description="Facebook profile URL", examples=["https://facebook.com/author"])
    instagram: str | None = Field(None, description="Instagram profile URL", examples=["https://instagram.com/author"])
    youtube: str | None = Field(None, description="YouTube channel URL", examples=["https://youtube.com/@author"])
    other: dict[str, str] = Field(default_factory=dict, description="Additional platform URLs", examples=[{}])


def _validate_email(v: str | None) -> str:
    if not v:
        return ""
    v = v.strip()
    if v and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
        raise ValueError("Invalid email address")
    return v


def _validate_phone(v: str | None) -> str:
    if not v:
        return ""
    v = v.strip()
    if v and not re.match(r"^[+\d][\d\s\-().]{2,30}$", v):
        raise ValueError("Invalid phone number")
    return v


def _validate_url(v: str | None) -> str:
    if not v:
        return ""
    v = v.strip()
    if v and not re.match(r"^https?://", v):
        raise ValueError("URL must start with http:// or https://")
    return v


class CreateAuthorRequest(BaseModel):
    name: str = Field(description="Author display name", examples=["Anna Kowalska"], min_length=1)
    slug: str | None = Field(
        None, description="URL slug (auto-generated from name if empty)", examples=["anna-kowalska"]
    )
    role_t9n: dict[str, str] = Field(
        default_factory=dict, description="Role per language", examples=[{"en": "Editor", "pl": "Redaktor"}]
    )
    description_t9n: dict[str, str] = Field(
        default_factory=dict, description="Bio per language", examples=[{"en": "Senior editor at Entirius"}]
    )
    tag_t9n: dict[str, str] = Field(
        default_factory=dict, description="Short tag per language", examples=[{"en": "tech"}]
    )
    photo_uid: UUID | None = Field(None, description="Image UUID for author photo", examples=[None])
    contact_email: str | None = Field("", description="Contact email", examples=["anna@example.com"])
    contact_phone: str | None = Field("", description="Contact phone", examples=["+48 123 456 789"])
    contact_url: str | None = Field("", description="Personal website URL", examples=["https://example.com"])
    social_profiles: SocialProfiles = Field(
        default_factory=SocialProfiles, description="Social media links", examples=[{}]
    )
    is_active: bool = Field(True, description="Whether author is active and visible in picker", examples=[True])

    _clean_email = field_validator("contact_email", mode="before")(_validate_email)
    _clean_phone = field_validator("contact_phone", mode="before")(_validate_phone)
    _clean_url = field_validator("contact_url", mode="before")(_validate_url)


class UpdateAuthorRequest(BaseModel):
    name: str | None = Field(None, description="Author display name", examples=["Anna Kowalska"])
    slug: str | None = Field(None, description="URL slug", examples=["anna-kowalska"])
    role_t9n: dict[str, str] | None = Field(None, description="Role per language", examples=[{"en": "Editor"}])
    description_t9n: dict[str, str] | None = Field(None, description="Bio per language", examples=[{}])
    tag_t9n: dict[str, str] | None = Field(None, description="Short tag per language", examples=[{}])
    photo_uid: UUID | None = Field(None, description="Image UUID for author photo", examples=[None])
    contact_email: str | None = Field(None, description="Contact email", examples=["anna@example.com"])
    contact_phone: str | None = Field(None, description="Contact phone", examples=["+48 123 456 789"])
    contact_url: str | None = Field(None, description="Personal website URL", examples=["https://example.com"])
    social_profiles: SocialProfiles | None = Field(None, description="Social media links", examples=[{}])
    is_active: bool | None = Field(None, description="Whether author is active", examples=[True])

    _clean_email = field_validator("contact_email", mode="before")(_validate_email)
    _clean_phone = field_validator("contact_phone", mode="before")(_validate_phone)
    _clean_url = field_validator("contact_url", mode="before")(_validate_url)


class DeleteAuthorRequest(BaseModel):
    reassign_to: UUID | None = Field(
        None,
        description="Author UID to reassign posts to, or null to remove from all posts",
        examples=["d0000001-0001-4000-8000-000000000002"],
    )
