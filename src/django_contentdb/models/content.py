# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import uuid

from django.db import models
from rest_framework.exceptions import ValidationError

PROTECTED_ROUTES = ("home", "header")


class Content(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, editable=False)
    content = models.JSONField(default=dict)
    extension = models.JSONField(null=True, blank=True)
    attributes = models.ManyToManyField("AttributeValue", related_name="content_set", through="ContentAttribute")
    meta = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    category = models.ForeignKey("Category", on_delete=models.SET_NULL, null=True, blank=True)
    objects = models.Manager()

    def __str__(self):
        return f"{self.uid}"

    def delete(self, *args, bypass=False, **kwargs):
        if bypass or not hasattr(self, "draft") or self.draft is None:
            return super().delete(*args, **kwargs)

        draft = self.draft
        if draft.is_system:
            raise ValidationError("Cannot delete system content")

        from django_contentdb.models import Draft

        for protected_url in PROTECTED_ROUTES:
            if not draft.routes.filter(url=protected_url).exists():
                continue
            others = Draft.objects.filter(routes__url=protected_url).exclude(pk=draft.pk).count()
            if others == 0:
                raise ValidationError(f"Cannot delete the last {protected_url} page")

        return super().delete(*args, **kwargs)

    class Meta:
        ordering = ["-created_at", "-updated_at"]
