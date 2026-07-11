# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch
from django_filters import rest_framework as django_filters
from rest_framework import status as status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from django_contentdb.enums import Action
from django_contentdb.filters import DraftFilter
from django_contentdb.models import ActivityLog, Content, ContentType, Deleted, Draft, DraftAuthor, DraftCoAuthor
from django_contentdb.permissions import ContentTypePermission
from django_contentdb.serializers import DraftContentSerializer, PublishedContentSerializer
from django_contentdb.utils import DjangoAuth as TokenAuthentication
from django_contentdb.utils import StandardPagination
from django_contentdb.viewsets import ContentDBModelViewSet as ModelViewSet


class DraftViewSet(ModelViewSet):
    """
    API endpoint that allows documents to be viewed or edited.
    """

    content_type_model = ContentType
    queryset = Content.objects.all()
    serializer_class = DraftContentSerializer
    published_serializer_class = PublishedContentSerializer
    filter_backends = (django_filters.DjangoFilterBackend,)
    filterset_class = DraftFilter
    pagination_class = StandardPagination
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated & (IsAdminUser | ContentTypePermission)]
    lookup_field = "uid"

    def get_content_type(self):
        slug = self.kwargs.get("content_type", None)
        try:
            return self.content_type_model.objects.get(slug=slug, is_layout_extender=False)
        except ObjectDoesNotExist:
            raise NotFound

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset()
        content_type = self.get_content_type()
        result = queryset.filter(draft__isnull=False, draft__content_type=content_type)
        return result.prefetch_related(
            "draft__published__content",
            "draft__channels",
            Prefetch(
                "draft__draft_authors",
                queryset=DraftAuthor.objects.select_related("author__photo").order_by("position"),
            ),
            Prefetch(
                "draft__draft_co_authors",
                queryset=DraftCoAuthor.objects.select_related("author__photo").order_by("position"),
            ),
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"_type": self.get_content_type()})
        return context

    def get_published_serializer_class(self):
        return self.published_serializer_class

    def get_published_serializer(self, *args, **kwargs):
        serializer_class = self.get_published_serializer_class()
        kwargs.setdefault("context", self.get_serializer_context())
        return serializer_class(*args, **kwargs)

    def list(self, request, *args, **kwargs):
        res = super().list(request, *args, **kwargs)
        ct = self.get_content_type()
        res.data = {**res.data, "content_type": ct.slug}
        return res

    @action(detail=True, name="published-content")
    def published(self, request, uid=None, *args, **kwargs):
        published_content = Content.objects.filter(published__draft__content__uid=uid).order_by(
            "-published__created_at"
        )
        page = self.paginate_queryset(published_content)
        if page is not None:
            serializer = self.get_published_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_published_serializer(published_content, many=True)
        response = {"meta": {"status": "OK", "message": ""}, "data": serializer.data}
        return Response(response)

    @published.mapping.post
    def published_create(self, request, uid=None, *args, **kwargs):
        serializer = self.get_published_serializer(data=request.data)
        serializer.context.update({"draft_uid": uid})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        log = ActivityLog(user=request.user, target=serializer.instance, action=Action.PUBLISH)
        log.save()

        response = {"meta": {"status": "CREATED", "message": ""}, "data": serializer.data}
        return Response(response, status=status.HTTP_201_CREATED, headers=headers)

    @published.mapping.delete
    def published_delete(self, request, uid=None, *args, **kwargs):
        is_all = True if self.request.query_params.get("all", False) in ["true", "True"] else False
        try:
            draft = Draft.objects.get(content__uid=uid)
        except ObjectDoesNotExist:
            raise Exception(f"Draft {uid} does not exists")

        deleted_uid = []
        error_uid = []
        if not is_all:
            try:
                latest = draft.published.last()
            except Exception as e:
                raise Exception(f"Error getting draft published version: {e}")

            if latest:
                luid = latest.content.uid
                try:
                    log = ActivityLog(user=request.user, target=latest, action=Action.DELETE)
                    log.save()

                    content = latest.content
                    latest.delete()
                    deleted_uid.append(luid)

                    deleted = Deleted(content=content)
                    deleted.save()
                except Exception as e:
                    raise Exception(f"Unable to delete published content {luid}: {e}")
            else:
                raise NotFound(f"Draft {uid} has no published version")
        else:
            try:
                all_published = draft.published.all()
            except Exception as e:
                raise Exception(f"Error getting draft published version: {e}")

            if all_published:
                for published in all_published:
                    puid = published.content.uid
                    try:
                        log = ActivityLog(user=request.user, target=published, action=Action.DELETE)
                        log.save()

                        content = published.content
                        published.delete()
                        deleted_uid.append(puid)

                        deleted = Deleted(content=content)
                        deleted.save()
                    except Exception:
                        error_uid.append(puid)
            else:
                raise NotFound(f"Draft {uid} has no published version")

        data = {"deleted_uid": deleted_uid, "error_uid": error_uid}
        status_name = "DELETED" if len(data["error_uid"]) == 0 else "ERROR"
        message = "" if len(data["error_uid"]) == 0 else "Unable to delete published content"
        response = {"meta": {"status": status_name, "message": message}, "data": data}
        return Response(response, status=status.HTTP_204_NO_CONTENT)


class LayoutViewSet(DraftViewSet):
    def get_content_type(self):
        slug = self.kwargs.get("content_type", None)
        try:
            return self.content_type_model.objects.get(slug=slug, is_layout_extender=True)
        except ObjectDoesNotExist:
            raise NotFound

    def perform_create(self, serializer):
        super().perform_create(serializer)
        self._validate_navigation_content(serializer.instance)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        self._validate_navigation_content(serializer.instance)

    def published_create(self, request, uid=None, *args, **kwargs):
        response = super().published_create(request, uid=uid, *args, **kwargs)
        self._invalidate_cache()
        return response

    def published_delete(self, request, uid=None, *args, **kwargs):
        response = super().published_delete(request, uid=uid, *args, **kwargs)
        self._invalidate_cache()
        return response

    def _invalidate_cache(self):
        from django_contentdb.services.navigation_service import invalidate_navigation_cache

        try:
            ct = self.get_content_type()
            invalidate_navigation_cache(ct.slug)
        except Exception:
            pass

    def _validate_navigation_content(self, content):
        if not hasattr(content, "draft") or not content.draft:
            return
        ct_slug = content.draft.content_type.slug
        if ct_slug not in ("header", "footer"):
            return
        from pydantic import ValidationError

        from django_contentdb.schemas.navigation import NavigationContent

        try:
            NavigationContent(**content.content)
        except (ValidationError, TypeError):
            pass
