# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from pydantic import BaseModel, ConfigDict, Field


class NavigationPublishedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uid: str = Field(description="Content UUID", examples=["c0000017-0000-4000-8000-000000000001"])
    name: str = Field(description="Navigation name", examples=["Main Header Navigation"])
    content: dict = Field(description="Navigation JSON (items with columns/links/banners)")
    language: str = Field(description="ISO2 language code", examples=["en"])
    published_at: str = Field(description="Publication timestamp", examples=["2026-03-15T10:00:00Z"])
