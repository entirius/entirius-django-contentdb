# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json

from django.contrib import admin
from django.utils.safestring import mark_safe

from . import models


class AccessRightsInline(admin.StackedInline):
    model = models.AccessRights


class AttributeValueInline(admin.StackedInline):
    model = models.AttributeValue


@admin.register(models.AccessRights)
class AccessRightsAdmin(admin.ModelAdmin):
    pass


@admin.register(models.Attribute)
class AttributeAdmin(admin.ModelAdmin):
    inlines = [AttributeValueInline]


class AttributeToSetInline(admin.TabularInline):
    model = models.AttributeToSet


@admin.register(models.AttributeSet)
class AttributeSetAdmin(admin.ModelAdmin):
    inlines = [AttributeToSetInline]


@admin.register(models.Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ["url", "label", "placement", "created_at", "updated_at", "len_drafts", "list_drafts"]
    list_filter = [
        "placement",
        ("created_at", admin.DateFieldListFilter),
        ("updated_at", admin.DateFieldListFilter),
        "drafts__language__iso2",
        "drafts__access_rights__access_level",
    ]
    search_fields = ["url", "label", "drafts__content__uid"]
    autocomplete_fields = ["drafts"]
    filter_horizontal = ("drafts",)

    def len_drafts(self, instance):
        return len(instance.drafts.all())

    def list_drafts(self, obj):
        return ", ".join([draft.name for draft in obj.drafts.all()])

    list_drafts.short_description = "Drafts"


@admin.register(models.ContentTypePermission)
class ContentTypePermissionAdmin(admin.ModelAdmin):
    list_display = ("action", "content_type", "users", "groups")
    autocomplete_fields = ("user", "group")
    list_filter = ("action", "content_type")
    search_fields = ["content_type__name"]

    def users(self, obj):
        return ", ".join([user.email for user in obj.user.all()])

    users.short_description = "Users"

    def groups(self, obj):
        return ", ".join([group.name for group in obj.group.all()])

    groups.short_description = "Groups"


@admin.register(models.ContentType)
class ContentTypeAdmin(admin.ModelAdmin):
    list_display = (
        "slug",
        "label",
        "attribute_set",
        "is_layout_extender",
        "supports_authors",
        "created_at",
        "updated_at",
    )
    readonly_fields = ["created_at", "updated_at"]
    search_fields = ["slug", "label"]
    list_filter = ["is_layout_extender", "supports_authors", "attribute_set"]


class DraftInline(admin.StackedInline):
    model = models.DraftToContentSet
    readonly_fields = ["draft"]


@admin.register(models.ContentSet)
class ContentSetAdmin(admin.ModelAdmin):
    inlines = [DraftInline]


class ContentAttributeInline(admin.StackedInline):
    model = models.ContentAttribute


@admin.register(models.Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = [
        "uid",
        "category",
        "draft_language",
        "draft_access_rights",
        "created_at",
        "content_type_slug",
        "updated_at",
    ]
    search_fields = ["uid"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "data_prettified_meta",
        "data_prettified_content",
        "data_prettified_extension",
    ]
    list_filter = [
        "attributes",
        ("created_at", admin.DateFieldListFilter),
        ("updated_at", admin.DateFieldListFilter),
        "draft__access_rights__access_level",
        "draft__language__iso2",
        ("draft__content_type", admin.RelatedFieldListFilter),
        "category",
    ]
    inlines = [ContentAttributeInline]
    autocomplete_fields = ("category",)

    def draft_language(self, instance):
        return instance.draft.language

    def draft_access_rights(self, instance):
        return [access.access_level for access in instance.draft.access_rights.all()]

    def content_type_slug(self, instance):
        return instance.draft.content_type.slug

    def data_prettified_meta(self, instance):
        if instance.meta and len(instance.meta) > 10000:
            return "Too much data, not formating."
        response = json.dumps(instance.meta, sort_keys=False, indent=4)
        return mark_safe(f"<pre>{response}</pre>")

    def data_prettified_content(self, instance):
        if instance.content and len(instance.content) > 10000:
            return "Too much data, not formating."
        response = json.dumps(instance.content, sort_keys=False, indent=4)
        return mark_safe(f"<pre>{response}</pre>")

    def data_prettified_extension(self, instance):
        if instance.extension and len(instance.extension) > 10000:
            return "Too much data, not formating."
        response = json.dumps(instance.extension, sort_keys=False, indent=4)
        return mark_safe(f"<pre>{response}</pre>")

    data_prettified_content.allow_tags = True
    data_prettified_content.short_description = "data prettified content"

    data_prettified_meta.allow_tags = True
    data_prettified_meta.short_description = "data prettified meta"

    data_prettified_extension.allow_tags = True
    data_prettified_extension.short_description = "data prettified extension"


class DraftAuthorInline(admin.TabularInline):
    model = models.DraftAuthor
    extra = 0
    autocomplete_fields = ["author"]


class DraftCoAuthorInline(admin.TabularInline):
    model = models.DraftCoAuthor
    extra = 0
    autocomplete_fields = ["author"]


@admin.register(models.Draft)
class DraftAdmin(admin.ModelAdmin):
    fields = ["content", "name", "content_type", "language", "channels", "created_at"]
    readonly_fields = ["created_at"]
    list_display = ["content", "name", "content_type", "language", "created_at"]
    inlines = [DraftAuthorInline, DraftCoAuthorInline]
    list_filter = [
        "content_type",
        "language__iso2",
        "access_rights__access_level",
        "channels",
        ("created_at", admin.DateFieldListFilter),
    ]
    filter_horizontal = ("access_rights", "channels")
    autocomplete_fields = ["content"]
    search_fields = ["name"]

    def category(self, obj):
        return obj.content.category

    category.short_description = "Category"


@admin.register(models.Published)
class PublishedAdmin(admin.ModelAdmin):
    fields = ["content", "draft", "created_at"]
    readonly_fields = ["created_at"]
    list_display = ["content", "draft", "created_at"]
    autocomplete_fields = ["content", "draft"]
    list_filter = ["content__draft__access_rights__access_level", "content__draft__language__iso2"]
    search_fields = ["content"]


@admin.register(models.Deleted)
class DeletedAdmin(admin.ModelAdmin):
    list_filter = ["content__draft__access_rights__access_level", "content__draft__language__iso2"]


@admin.register(models.ImageTag)
class ImageTagAdmin(admin.ModelAdmin):
    list_display = ["slug", "label"]


class ImageTagInline(admin.StackedInline):
    model = models.ImageToTag
    # list_display = ["tag", "image"]


class ThumbnailInline(admin.StackedInline):
    model = models.Thumbnail


@admin.register(models.Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ["uid", "created_at", "updated_at", "width", "height", "image_path", "all_tags"]
    search_fields = ["uid", "tags__name"]
    list_filter = ["tags", ("created_at", admin.DateFieldListFilter), ("updated_at", admin.DateFieldListFilter)]
    readonly_fields = ["data_prettified"]
    inlines = [ImageTagInline, ThumbnailInline]

    def data_prettified(self, instance):
        if instance.meta is None:
            return None
        if len(instance.meta) > 10000:
            return "Too much data, not formating."
        response = json.dumps(instance.meta, sort_keys=False, indent=4)
        return mark_safe(f"<pre>{response}</pre>")

    data_prettified.allow_tags = True
    data_prettified.short_description = "data prettified"

    def all_tags(self, instance):
        return ", ".join([tag.label for tag in instance.tags.all()])

    def image_path(self, instance):
        return instance.image.path


@admin.register(models.Thumbnail)
class ThumbnailAdmin(admin.ModelAdmin):
    list_display = ["source", "method", "image", "width", "height", "created_at", "updated_at"]
    search_fields = ["source__uid"]
    list_filter = ["method", ("created_at", admin.DateFieldListFilter), ("updated_at", admin.DateFieldListFilter)]


@admin.register(models.ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    search_fields = ["user__email"]
    list_filter = ["user", "action"]
    readonly_fields = ["action", "user", "content_type", "object_id"]


@admin.register(models.ContentChannel)
class ContentChannelAdmin(admin.ModelAdmin):
    list_display = ["idx", "name", "default_language", "is_default"]
    list_filter = ["is_default"]
    search_fields = ["idx", "name"]
    actions = ["sync_from_pim"]

    @admin.action(description="Sync channels from PIM")
    def sync_from_pim(self, request, queryset):
        from django_contentdb.services.sync_service import sync_channels_from_pim

        count = sync_channels_from_pim()
        self.message_user(request, f"Synced {count} channels from PIM")


@admin.register(models.Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ["iso2", "iso3", "name_en", "name_pl"]
    actions = ["sync_from_pim"]

    @admin.action(description="Sync languages from PIM")
    def sync_from_pim(self, request, queryset):
        from django_contentdb.services.sync_service import sync_languages_from_pim

        created, updated = sync_languages_from_pim()
        self.message_user(request, f"Synced languages from PIM ({created} created, {updated} updated)")


@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("uid", "name", "url_key", "language", "created_at", "updated_at")
    list_filter = ("language",)
    readonly_fields = ["created_at", "updated_at"]
    search_fields = ("uid", "name", "url_key")


@admin.register(models.Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    search_fields = ("name", "slug")
    list_filter = ("is_active",)
    readonly_fields = ["created_at", "updated_at"]
