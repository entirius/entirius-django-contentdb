# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models


class ImageToTag(models.Model):
    image = models.ForeignKey("Image", on_delete=models.CASCADE)
    tag = models.ForeignKey("ImageTag", on_delete=models.CASCADE)
    objects = models.Manager()

    def __str__(self):
        return f"{self.image} => {self.tag}"

    class Meta:
        constraints = [models.UniqueConstraint(fields=["image", "tag"], name="unique_tag_per_image")]
