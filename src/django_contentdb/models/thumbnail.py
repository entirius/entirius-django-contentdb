# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models

from django_contentdb.utils import HashedImageField, UniqueFileSystemStorage


class Thumbnail(models.Model):
    class ProcessingMethod(models.TextChoices):
        OPTIMIZE = "optimize", "Optimize"

    method = models.CharField(max_length=32, choices=ProcessingMethod.choices, editable=False)
    source = models.ForeignKey("Image", on_delete=models.CASCADE, related_name="thumbnails", editable=False)
    image = HashedImageField(
        upload_to="thumb", storage=UniqueFileSystemStorage(), height_field="height", width_field="width", editable=False
    )
    width = models.PositiveSmallIntegerField(blank=True, null=True, editable=False)
    height = models.PositiveSmallIntegerField(blank=True, null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["method", "source", "width", "height"], name="unique_thumbnail_per_source_per_method_per_size"
            )
        ]

    def delete(self, *args, **kwargs):
        self.image.delete(self.image.path)
        return super().delete(*args, **kwargs)

    def __str__(self) -> str:
        return self.image.path
