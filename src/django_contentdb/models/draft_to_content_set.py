# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models


class DraftToContentSet(models.Model):
    content_set = models.ForeignKey("ContentSet", on_delete=models.CASCADE)
    draft = models.ForeignKey("Draft", on_delete=models.CASCADE)
    objects = models.Manager()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["draft"], name="draft_unique_per_table")]
