# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models


class Language(models.Model):
    iso3 = models.CharField(max_length=3)
    iso2 = models.CharField(max_length=2)
    name_en = models.CharField(max_length=64, default="", blank=True)
    name_pl = models.CharField(max_length=64, default="", blank=True)
    objects = models.Manager()

    def __str__(self):
        return self.iso2

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["iso2"], name="unique_iso2_per_language"),
            models.UniqueConstraint(fields=["iso3"], name="unique_iso3_per_language"),
        ]
