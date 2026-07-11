# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models


class ContentChannel(models.Model):
    idx = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=128, default="", blank=True)
    default_language = models.ForeignKey(
        "Language", on_delete=models.SET_NULL, null=True, blank=True, related_name="default_for_channels"
    )
    is_default = models.BooleanField(default=False)
    objects = models.Manager()

    def __str__(self):
        return self.idx

    def save(self, *args, **kwargs):
        if self.is_default:
            ContentChannel.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
