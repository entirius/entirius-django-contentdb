# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image as PILImage

from django_contentdb.models import Image, Thumbnail
from django_contentdb.tasks import optimize_image


@pytest.fixture
def media_dirs(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    settings.TMP_DIR = str(tmp_path / "tmp")
    return settings


def _upload(width: int, height: int) -> SimpleUploadedFile:
    buffer = io.BytesIO()
    PILImage.new("RGB", (width, height), "red").save(buffer, format="JPEG")
    return SimpleUploadedFile("source.jpg", buffer.getvalue(), content_type="image/jpeg")


@pytest.mark.django_db
def test_optimize_image_creates_thumbnail(media_dirs):
    record = Image.objects.create(image=_upload(120, 80))

    optimize_image(record.pk)

    thumbnail = Thumbnail.objects.get(source=record, method=Thumbnail.ProcessingMethod.OPTIMIZE)
    assert (thumbnail.width, thumbnail.height) == (120, 80)
    assert thumbnail.image.name


@pytest.mark.django_db
def test_optimize_image_reuses_existing_thumbnail_path(media_dirs):
    record = Image.objects.create(image=_upload(120, 80))
    optimize_image(record.pk)
    original_name = Thumbnail.objects.get(source=record).image.name

    optimize_image(record.pk)

    assert Thumbnail.objects.filter(source=record).count() == 1
    assert Thumbnail.objects.get(source=record).image.name == original_name
