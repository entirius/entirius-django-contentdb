# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import models
from django.utils import timezone
from django.utils.timezone import now

from django_contentdb.enums import Action


class ContentTypePermission(models.Model):
    action = models.CharField(max_length=12, choices=Action.choices)
    content_type = models.ForeignKey("ContentType", related_name="user_permissions", on_delete=models.CASCADE)
    user = models.ManyToManyField(get_user_model(), blank=True)
    group = models.ManyToManyField(Group, blank=True)
    created_at = models.DateTimeField(default=now, editable=False)
    updated_at = models.DateTimeField(default=now, editable=False)
    objects = models.Manager()

    def save(self, *args, **kwargs):
        if not self.id:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.action} -> {self.content_type}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["action", "content_type"], name="unique_action_per_type_per_permission")
        ]
