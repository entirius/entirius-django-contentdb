# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import uuid

from django.db import models
from slugify import slugify


class Author(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=256)
    slug = models.SlugField(max_length=256, unique=True)
    role_t9n = models.JSONField(default=dict, blank=True)
    description_t9n = models.JSONField(default=dict, blank=True)
    tag_t9n = models.JSONField(default=dict, blank=True)
    photo = models.ForeignKey("Image", on_delete=models.SET_NULL, null=True, blank=True)
    contact_email = models.EmailField(max_length=256, blank=True, default="")
    contact_phone = models.CharField(max_length=64, blank=True, default="")
    contact_url = models.URLField(max_length=512, blank=True, default="")
    social_profiles = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    objects = models.Manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:256]
            self.slug = self._generate_unique_slug(base)
        else:
            normalized = slugify(self.slug)[:256]
            self.slug = self._generate_unique_slug(normalized)
        super().save(*args, **kwargs)

    def _generate_unique_slug(self, base_slug: str) -> str:
        slug = base_slug
        counter = 2
        while Author.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug
