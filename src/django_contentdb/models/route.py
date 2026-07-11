# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models
from django.utils import timezone
from django.utils.timezone import now
from rest_framework.exceptions import ValidationError


class Route(models.Model):
    class Placement(models.TextChoices):
        TOP = "top", "Top"
        BOTTOM = "bottom", "Bottom"

    url = models.CharField(max_length=256)
    label = models.CharField(max_length=256, default="", blank=True)
    placement = models.CharField(max_length=12, choices=Placement.choices, default=Placement.TOP)
    drafts = models.ManyToManyField("Draft", related_name="routes")
    created_at = models.DateTimeField(default=now, editable=False)
    updated_at = models.DateTimeField(default=now, editable=False)
    objects = models.Manager()

    def __str__(self):
        return self.url

    def save(self, *args, **kwargs):
        if not self.id:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        return super().save(*args, **kwargs)

    def delete(self, *args, bypass=False, **kwargs):
        if bypass:
            return super().delete(*args, **kwargs)
        if self.url == "home":
            raise ValidationError("Cannot delete home route")
        if self.url == "header":
            raise ValidationError("Cannot delete header route")
        return super().delete(*args, **kwargs)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["url"], name="route_is_unique")]
