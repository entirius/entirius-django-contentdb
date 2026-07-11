# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from itertools import groupby

from rest_framework import serializers


class DraftContentSetMembersField(serializers.Field):
    def to_representation(self, instance):
        if instance.contentset_set.exists():
            qs = instance.contentset_set.first().members.values(
                "language__iso2", "content__uid", "routes__url", "routes__label"
            )
            key_func = lambda x: (x["language__iso2"], x["content__uid"])
            grouped = groupby(sorted(qs, key=key_func), key=key_func)
            result = {}
            for key, group in grouped:
                routes = []
                for elem in group:
                    if elem["routes__url"] is not None:
                        routes.append({"url": elem["routes__url"], "label": elem["routes__label"]})

                result[key[0]] = {"uid": key[1], "routes": routes}
            return result
        else:
            return {}
