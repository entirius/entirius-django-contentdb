# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models


class Draft(models.Model):
    content_type = models.ForeignKey("ContentType", on_delete=models.CASCADE)
    content = models.OneToOneField("Content", on_delete=models.CASCADE)
    name = models.CharField(max_length=128, default="", blank=True)
    access_rights = models.ManyToManyField("AccessRights", related_name="draft_access")
    channels = models.ManyToManyField("ContentChannel", related_name="drafts", blank=True)
    language = models.ForeignKey("Language", on_delete=models.CASCADE, default=1)
    is_system = models.BooleanField(default=False)
    authors = models.ManyToManyField("Author", through="DraftAuthor", related_name="drafted_as_author", blank=True)
    co_authors = models.ManyToManyField(
        "Author", through="DraftCoAuthor", related_name="drafted_as_co_author", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    objects = models.Manager()

    def __str__(self):
        return str(self.content)

    class Meta:
        ordering = ["-created_at"]
