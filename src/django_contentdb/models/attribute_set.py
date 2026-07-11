# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models
from slugify import slugify


class AttributeSet(models.Model):
    slug = models.CharField(max_length=64, editable=False)
    label = models.CharField(max_length=64)
    attributes = models.ManyToManyField("Attribute", related_name="attribute_sets", through="AttributeToSet")
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    objects = models.Manager()

    def __str__(self):
        return f"{self.slug}"

    def save(self, *args, **kwargs):
        self.slug = slugify(self.label)
        super().save(*args, **kwargs)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["slug"], name="attribute_set_slug_is_unique")]
