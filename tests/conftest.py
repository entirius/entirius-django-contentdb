# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import io
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from PIL import Image as PilImage
from rest_framework.test import APIClient

from django_contentdb.models import (
    Attribute,
    AttributeSet,
    AttributeValue,
    Content,
    ContentChannel,
    ContentType,
    Draft,
    Image,
    Language,
    Route,
)

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(username="admin", password="admin123", email="admin@test.com")


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(username="user", password="user123", email="user@test.com")


@pytest.fixture
def blog_setup(db):
    """A `web` channel (EN) with a blog-post type whose set holds a select, a multiselect and a text attribute."""
    language = Language.objects.create(iso2="EN", iso3="ENG")
    channel = ContentChannel.objects.create(idx="web", default_language=language, is_default=True)
    attribute_set = AttributeSet.objects.create(label="Blog")
    attributes = {
        "topic": Attribute.objects.create(label="Topic", is_txt=True, allow_new_values=False),
        "tags": Attribute.objects.create(label="Tags", is_txt=True, allow_new_values=False, allow_many_values=True),
        "subtitle": Attribute.objects.create(label="Subtitle", is_txt=True),
    }
    attribute_set.attributes.add(*attributes.values())
    for attribute, values in ((attributes["topic"], ["news", "guides"]), (attributes["tags"], ["a", "b", "c"])):
        AttributeValue.objects.bulk_create(AttributeValue(attribute=attribute, value_txt=value) for value in values)
    content_type = ContentType.objects.create(slug="blog-post", label="Blog post", attribute_set=attribute_set)
    return SimpleNamespace(language=language, channel=channel, content_type=content_type, attributes=attributes)


@pytest.fixture
def blog_draft(blog_setup):
    """One draft of the blog-post type in the `web` channel, with a section, a tile, meta and a header."""
    content = Content.objects.create(
        content={
            "sections": {
                "s-1": {"core_type": "section-text", "title": "Intro", "description": "<p>Hello world</p>"},
                "s-2": {"core_type": "section-banner", "images_set": {}},
            },
            "sections_order": ["s-1", "s-2"],
            "tiles": {"t-1": {"title": "Tile title", "description": ""}},
            "tiles_order": {},
        },
        meta={"index": "Index", "title": "Old title"},
        extension={"title": "Header", "description": "Lead"},
    )
    draft = Draft.objects.create(
        content_type=blog_setup.content_type, content=content, name="First post", language=blog_setup.language
    )
    draft.channels.add(blog_setup.channel)
    Route.objects.create(url="first-post").drafts.add(draft)
    return draft


def png(color: str) -> bytes:
    """A small PNG of one colour — different colours give different files."""
    buffer = io.BytesIO()
    PilImage.new("RGB", (8, 6), color).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def media_root(settings, tmp_path):
    """Image files and thumbnail scratch space under the test's own directory."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    settings.TMP_DIR = str(tmp_path / "tmp")
    return tmp_path


@pytest.fixture
def gallery_image(db, media_root):
    """A gallery image `mug.png` (red) with an alt text."""
    image = Image.objects.create(meta={"fileName": "mug.png", "alt": "A red mug"})
    image.image.save("mug.png", ContentFile(png("red")), save=True)
    return image
