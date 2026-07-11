# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models


class Deleted(models.Model):
    content = models.OneToOneField("Content", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    objects = models.Manager()
