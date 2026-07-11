# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models


class Published(models.Model):
    draft = models.ForeignKey("Draft", on_delete=models.CASCADE, related_name="published")
    content = models.OneToOneField("Content", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    objects = models.Manager()

    def __str__(self):
        return str(self.content)

    class Meta:
        ordering = ["-created_at"]
