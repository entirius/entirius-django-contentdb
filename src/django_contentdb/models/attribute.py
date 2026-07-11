# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from dateutil import parser
from django.db import models
from slugify import slugify


class Attribute(models.Model):
    slug = models.CharField(max_length=64, editable=False)

    label = models.CharField(max_length=64)

    # CLASSIFIERS
    is_bool = models.BooleanField(default=False)
    is_int = models.BooleanField(default=False)
    is_txt = models.BooleanField(default=False)
    is_txt_t9n = models.BooleanField(default=False)
    is_txt_long = models.BooleanField(default=False)
    is_datetime = models.BooleanField(default=False)

    # POLICY
    is_filterable = models.BooleanField(default=False)
    is_searchable = models.BooleanField(default=False)
    is_comparable = models.BooleanField(default=False)
    allow_new_values = models.BooleanField(default=True)
    allow_many_values = models.BooleanField(default=False)

    # TIMESTAMPS
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    objects = models.Manager()

    @property
    def type_as_str(self):
        if self.is_bool:
            return "bool"
        elif self.is_int:
            return "int"
        elif self.is_txt:
            return "txt"
        elif self.is_txt_t9n:
            raise NotImplementedError
        elif self.is_txt_long:
            return "txt_long"
        elif self.is_datetime:
            return "datetime"
        else:
            raise NotImplementedError

    # TODO probably should move to some kind of manager or helper class
    def parse_value(self, value):
        if self.is_bool:
            return bool(int(value))
        elif self.is_int:
            return int(value)
        elif self.is_txt:
            return str(value)
        elif self.is_txt_t9n:
            raise NotImplementedError
        elif self.is_txt_long:
            return str(value)
        elif self.is_datetime:
            return parser.parse(str(value))
        else:
            raise NotImplementedError

    def __str__(self):
        return f"{self.slug}"

    def save(self, *args, **kwargs):
        self.slug = slugify(self.label)
        super().save(*args, **kwargs)

    class Meta:
        # TODO is_searchable can be true only for text fields
        constraints = [models.UniqueConstraint(fields=["slug"], name="attribute_slug_is_unique")]
