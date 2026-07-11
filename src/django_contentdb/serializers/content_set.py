# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework import serializers

from django_contentdb.models import ContentSet, Draft, DraftToContentSet


class ContentSetSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        # Create empty content set
        Model = self.Meta.model
        instance = Model.objects.create()
        # Add members
        for member in validated_data["members"]:
            DraftToContentSet.objects.update_or_create(draft=member["draft"], defaults={"content_set": instance})
        return instance

    def update(self, instance, validated_data):
        # clear members
        DraftToContentSet.objects.filter(content_set=instance).delete()
        # add members
        for member in validated_data["members"]:
            DraftToContentSet.objects.update_or_create(draft=member["draft"], defaults={"content_set": instance})

        return instance

    def to_representation(self, instance):
        qs = instance.members.all().values("content__uid", "language__iso2", "name")
        result = {
            "uid": instance.uid,
            "members": [
                {"name": member["name"], "draft": member["content__uid"], "language": member["language__iso2"]}
                for member in qs
            ],
        }
        return result

    def to_internal_value(self, data):
        result = []
        for member in data["members"]:
            draft = Draft.objects.get(content__uid=member["draft"])
            result.append({"draft": draft})
        return {"members": result}

    class Meta:
        model = ContentSet
        fields = ["uid", "members"]
