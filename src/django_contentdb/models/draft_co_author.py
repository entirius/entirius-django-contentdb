# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models


class DraftCoAuthor(models.Model):
    draft = models.ForeignKey("Draft", on_delete=models.CASCADE, related_name="draft_co_authors")
    author = models.ForeignKey("Author", on_delete=models.CASCADE, related_name="draft_co_author_links")
    position = models.PositiveIntegerField(default=0)
    objects = models.Manager()

    def __str__(self):
        return f"{self.draft} - {self.author} (co, pos {self.position})"

    class Meta:
        constraints = [models.UniqueConstraint(fields=["draft", "author"], name="unique_co_author_per_draft")]
        ordering = ["position"]
