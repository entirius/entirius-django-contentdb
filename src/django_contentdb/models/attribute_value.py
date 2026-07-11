# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models


class AttributeValue(models.Model):
    attribute = models.ForeignKey("Attribute", on_delete=models.CASCADE, related_name="values")
    value_bool = models.BooleanField(null=True, blank=True)
    value_int = models.IntegerField(null=True, blank=True)
    value_txt = models.CharField(null=True, blank=True, max_length=128)
    value_txt_t9n = models.JSONField(null=True, blank=True)
    value_txt_long = models.CharField(null=True, blank=True, max_length=2048)
    value_datetime = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    objects = models.Manager()

    @property
    def value(self):
        attr = self.attribute
        if attr.is_bool:
            return self.value_bool
        elif attr.is_int:
            return self.value_int
        elif attr.is_txt:
            return self.value_txt
        elif attr.is_txt_t9n:
            raise NotImplementedError
        elif attr.is_txt_long:
            return self.value_txt_long
        elif attr.is_datetime:
            return self.value_datetime
        else:
            raise Exception("Unsupported attribute value")

    def __str__(self):
        attr = self.attribute
        if attr.is_bool:
            val = self.value_bool
        elif attr.is_int:
            val = self.value_int
        elif attr.is_txt:
            val = self.value_txt
        elif attr.is_txt_t9n:
            raise NotImplementedError
        elif attr.is_txt_long:
            val = self.value_txt_long
        elif attr.is_datetime:
            val = self.value_datetime
        else:
            raise Exception("Unsupported attribute value")

        return f"{val} of {attr.label}"
