# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models


class ImageTag(models.Model):
    slug = models.SlugField(max_length=64)
    label = models.CharField(max_length=64)
    objects = models.Manager()

    def __str__(self):
        return self.slug

    class Meta:
        constraints = [models.UniqueConstraint(fields=["slug"], name="unique_slug")]
