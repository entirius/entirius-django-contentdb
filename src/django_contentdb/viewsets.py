# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from rest_framework import status as status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from django_contentdb.enums import Action
from django_contentdb.models import ActivityLog


class PublishedSortMixin:
    """Mixin that maps created_at sorting to draft's created_at for published content"""

    SORT_FIELD_MAP = {
        "created_at": "published__draft__created_at",
        "-created_at": "-published__draft__created_at",
    }

    def sort(self, request, queryset):
        available_sorting_fields = getattr(self, "available_sorting_fields", None)
        default_sorting_field = getattr(self, "default_sorting_field", None)
        sort_fields = request.query_params.getlist("sort")

        if default_sorting_field and not sort_fields:
            mapped_default = self.SORT_FIELD_MAP.get(default_sorting_field, default_sorting_field)
            default_field_without_direction = mapped_default[1:] if mapped_default.startswith("-") else mapped_default
            queryset = queryset.order_by(mapped_default)
            if distinct_fields := getattr(self, "distinct_fields", None):
                queryset = queryset.distinct(default_field_without_direction, *distinct_fields)
            return queryset

        if not available_sorting_fields or not sort_fields:
            return queryset

        flat_fields = [f.strip() for entry in sort_fields for f in entry.split(",")]
        validated = [f for f in flat_fields if f.lstrip("-") in available_sorting_fields]
        mapped = [self.SORT_FIELD_MAP.get(f, f) for f in validated]
        if mapped:
            queryset = queryset.order_by(*mapped)
        return queryset


class ContentDBModelViewSet(ModelViewSet):
    def sort(self, request, queryset):
        available_sorting_fields = getattr(self, "available_sorting_fields", None)
        default_sorting_field = getattr(self, "default_sorting_field", None)
        sort_fields = request.query_params.getlist("sort")
        if default_sorting_field and not sort_fields:
            default_sorting_field_without_direction = (
                default_sorting_field[1:] if default_sorting_field.startswith("-") else default_sorting_field
            )
            if (
                default_sorting_field in available_sorting_fields
                or default_sorting_field_without_direction in available_sorting_fields
            ):
                queryset = queryset.order_by(default_sorting_field)
                if distinct_fields := getattr(self, "distinct_fields", None):
                    queryset = queryset.distinct(default_sorting_field_without_direction, *distinct_fields)

                return queryset

        if available_sorting_fields:
            available_sorting_fields_with_prefix = [
                *available_sorting_fields,
                *[f"-{sorter}" for sorter in available_sorting_fields],
            ]
            sort_fields = [field.strip() for sorter in sort_fields for field in sorter.split(",")]
            sort_fields = [field for field in sort_fields if field in available_sorting_fields_with_prefix]
            queryset = queryset.order_by(*sort_fields)
        return queryset

    def create(self, request, *args, **kwargs):
        """Create a model instance."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        log = ActivityLog(user=request.user, target=serializer.instance, action=Action.CREATE)
        log.save()

        response = {"meta": {"status": "CREATED", "message": ""}, "data": serializer.data}
        return Response(response, status=status.HTTP_201_CREATED, headers=headers)

    def list(self, request, *args, **kwargs):
        """List a queryset."""
        queryset = self.filter_queryset(self.get_queryset())
        queryset = self.sort(request, queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        response = {"meta": {"status": "OK", "message": ""}, "data": serializer.data}
        return Response(response)

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a model instance."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        response = {"meta": {"status": "OK", "message": ""}, "data": serializer.data}
        return Response(response)

    def update(self, request, *args, **kwargs):
        """Update a model instance."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        log = ActivityLog(user=request.user, target=serializer.instance, action=Action.UPDATE)
        log.save()

        response = {"meta": {"status": "UPDATED", "message": ""}, "data": serializer.data}
        return Response(response)

    def destroy(self, request, *args, **kwargs):
        """Destroy a model instance."""

        instance = self.get_object()
        log = ActivityLog(user=request.user, target=instance, action=Action.DELETE)
        log.save()
        self.perform_destroy(instance)

        response = {"meta": {"status": "DELETED", "message": ""}, "data": ""}
        return Response(response, status=status.HTTP_204_NO_CONTENT)


class ROContentDBModelViewSet(ReadOnlyModelViewSet):
    def sort(self, request, queryset):
        available_sorting_fields = getattr(self, "available_sorting_fields", None)
        default_sorting_field = getattr(self, "default_sorting_field", None)
        sort_fields = request.query_params.getlist("sort")
        if default_sorting_field and not sort_fields:
            default_sorting_field_without_direction = (
                default_sorting_field[1:] if default_sorting_field.startswith("-") else default_sorting_field
            )
            if (
                default_sorting_field in available_sorting_fields
                or default_sorting_field_without_direction in available_sorting_fields
            ):
                queryset = queryset.order_by(default_sorting_field)
                if distinct_fields := getattr(self, "distinct_fields", None):
                    queryset = queryset.distinct(default_sorting_field_without_direction, *distinct_fields)

                return queryset

        if available_sorting_fields:
            available_sorting_fields_with_prefix = [
                *available_sorting_fields,
                *[f"-{sorter}" for sorter in available_sorting_fields],
            ]
            sort_fields = [field.strip() for sorter in sort_fields for field in sorter.split(",")]
            sort_fields = [field for field in sort_fields if field in available_sorting_fields_with_prefix]
            queryset = queryset.order_by(*sort_fields)
        return queryset

    def list(self, request, *args, **kwargs):
        """List a queryset."""
        queryset = self.filter_queryset(self.get_queryset())
        queryset = self.sort(request, queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        response = {"meta": {"status": "OK", "message": ""}, "data": serializer.data}
        return Response(response)

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a model instance."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        response = {"meta": {"status": "OK", "message": ""}, "data": serializer.data}
        return Response(response)
