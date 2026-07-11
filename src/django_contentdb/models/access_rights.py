# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models


class AccessRights(models.Model):
    access_level = models.IntegerField(default=0, unique=True, primary_key=True)
    objects = models.Manager()

    def __str__(self):
        return f"{self.access_level}"
