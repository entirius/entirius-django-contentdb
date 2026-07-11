# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import uuid

from django.db import models

from django_contentdb.utils import HashedImageField, UniqueFileSystemStorage


class Image(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, editable=False)
    meta = models.JSONField(null=True, blank=True)
    tags = models.ManyToManyField("ImageTag", through="ImageToTag")
    image = HashedImageField(
        upload_to="image", storage=UniqueFileSystemStorage(), height_field="height", width_field="width", editable=False
    )
    width = models.PositiveSmallIntegerField(blank=True, null=True, editable=False)
    height = models.PositiveSmallIntegerField(blank=True, null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    objects = models.Manager()

    def __str__(self):
        return f"{self.uid}"

    def delete(self, *args, **kwargs):
        self.image.delete(self.image.path)
        return super().delete(*args, **kwargs)

    class Meta:
        ordering = ["-created_at", "-updated_at"]
