# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from itertools import groupby

from rest_framework import serializers

from django_contentdb.models import Content


class PublishedContentSetMembersField(serializers.Field):
    def to_representation(self, instance):
        if instance.contentset_set.exists():
            qs = (
                Content.objects.filter(
                    published__isnull=False, published__draft__in=instance.contentset_set.first().members.all()
                )
                .order_by("published__draft_id", "-published__created_at")
                .distinct("published__draft_id")
                .values(
                    "uid",
                    "published__draft__language__iso2",
                    "published__draft__routes__url",
                    "published__draft__routes__label",
                )
            )
            key_func = lambda x: (x["published__draft__language__iso2"], x["uid"])
            grouped = groupby(sorted(qs, key=key_func), key=key_func)
            result = {}
            for key, group in grouped:
                routes = []
                for elem in group:
                    if elem["published__draft__routes__url"] is not None:
                        routes.append(
                            {
                                "url": elem["published__draft__routes__url"],
                                "label": elem["published__draft__routes__label"],
                            }
                        )

                result[key[0]] = {"uid": key[1], "routes": routes}

            return result
        else:
            return {}
