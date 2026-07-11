# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models


class ContentType(models.Model):
    slug = models.CharField(max_length=64)
    label = models.CharField(max_length=64)
    attribute_set = models.ForeignKey("AttributeSet", on_delete=models.CASCADE, related_name="content_types")
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    is_layout_extender = models.BooleanField(default=False)
    supports_authors = models.BooleanField(default=False)
    objects = models.Manager()

    def __str__(self):
        return self.label

    class Meta:
        constraints = [models.UniqueConstraint(fields=["slug"], name="content_type_slug_is_unique")]
