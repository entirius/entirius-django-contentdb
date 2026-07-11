# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import uuid

from django.db import models
from idx_normalizator import normalize_url_key
from slugify import slugify


class Category(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256)
    url_key = models.CharField(max_length=256, null=False, blank=False)
    language = models.ForeignKey("Language", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    objects = models.Manager()

    def generate_url_key(self, name: str, max_length: int = 256):
        slug = slugify(name)
        url_key = slug[:max_length]
        return normalize_url_key(url_key)

    def save(self, *args, **kwargs):
        if not self.url_key or (self.url_key and self.url_key == ""):
            self.url_key = self.generate_url_key(str(self.name))
        else:
            self.url_key = self.generate_url_key(self.url_key)
        super().save(*args, **kwargs)

    def __str__(self):
        if self.language is not None:
            return f"{self.name} ({self.language.iso2})"
        return self.name

    class Meta:
        verbose_name_plural = "Categories"
