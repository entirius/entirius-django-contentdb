# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
import os

from celery import shared_task
from django.conf import settings
from django.core.files import File

from .image_manager import ImageManager
from .models import Image, Thumbnail
from .settings import THUMBNAIL_QUALITY

logger = logging.getLogger(__name__)


@shared_task(queue="contentdb", ignore_result=True)
def optimize_image(image_pk: int) -> None:
    """
    Create or re-optimize a thumbnail for the given Image.

    Behavior:
    - If a thumbnail for the image+method+size already exists, overwrite the existing file in place
      with the new quality setting to keep the same URL.
    - If it does not exist, create it.
    """
    method = Thumbnail.ProcessingMethod.OPTIMIZE
    record = Image.objects.get(pk=image_pk)

    thumb_qs = Thumbnail.objects.filter(source=record, method=method, width=record.width, height=record.height)
    thumb_exists = thumb_qs.exists()

    src_path = record.image.path
    image = ImageManager.open_image(src_path)

    if thumb_exists:
        try:
            thumb = thumb_qs.get()
            ImageManager.save_image(image, thumb.image.path, quality=THUMBNAIL_QUALITY)
            logger.info(
                f"Re-optimized thumbnail IN-PLACE for Image {record.uid} with method {method} at {thumb.image.path}"
            )
        except Exception as e:
            logger.error(f"Unable to re-optimize thumbnail in place for Image {record.uid} with method {method}: {e}")
    else:
        src_ext = ImageManager.get_extension(src_path)
        tmp_file_name = f"{record.pk}-{method}{src_ext}"
        tmp_path = os.path.join(settings.TMP_DIR, tmp_file_name)
        ImageManager.check_or_create_dir(settings.TMP_DIR)
        ImageManager.save_image(image, tmp_path, quality=THUMBNAIL_QUALITY)
        f = open(tmp_path, "rb")
        try:
            thumb = Thumbnail(source=record, method=method)
            thumb.image.save(tmp_file_name, File(f, name=tmp_file_name))
            thumb.save()
            logger.info(f"Saved thumbnail for Image {record.uid} with method {method}")
        except Exception as e:
            logger.error(f"Unable to save thumbnail for Image {record.uid} with method {method}: {e}")
        finally:
            f.close()
            ImageManager.delete_image(tmp_path)
