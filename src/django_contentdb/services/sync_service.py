# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from django_contentdb.models import ContentChannel, Language

logger = logging.getLogger(__name__)


def sync_channels_from_pim() -> int:
    """Sync ContentChannels from PIM Channel model. Returns count of synced channels."""
    try:
        from django_pim.models import Channel
    except ImportError:
        logger.info("django_pim not installed, skipping channel sync")
        return 0

    lang_map = {lang.iso2.upper(): lang for lang in Language.objects.all()}
    existing = {ch.idx: ch for ch in ContentChannel.objects.all()}

    pim_channels = list(Channel.objects.select_related("default_language"))
    to_create = []
    to_update = []

    for pim_ch in pim_channels:
        local_lang = None
        if pim_ch.default_language:
            local_lang = lang_map.get(pim_ch.default_language.iso2.upper())

        if pim_ch.idx in existing:
            ch = existing[pim_ch.idx]
            ch.name = pim_ch.name
            ch.default_language = local_lang
            ch.is_default = pim_ch.is_default
            to_update.append(ch)
        else:
            to_create.append(
                ContentChannel(
                    idx=pim_ch.idx, name=pim_ch.name, default_language=local_lang, is_default=pim_ch.is_default
                )
            )

    if to_create:
        ContentChannel.objects.bulk_create(to_create, batch_size=500)
    if to_update:
        ContentChannel.objects.bulk_update(to_update, fields=["name", "default_language", "is_default"], batch_size=500)

    # Ensure at most one is_default=True (bulk_update skips custom save logic)
    default_channels = ContentChannel.objects.filter(is_default=True).order_by("pk")
    if default_channels.count() > 1:
        keep = default_channels.last()
        ContentChannel.objects.filter(is_default=True).exclude(pk=keep.pk).update(is_default=False)

    return len(pim_channels)


def sync_languages_from_pim(sync_all: bool = False) -> tuple[int, int]:
    """Sync Languages from django_regional. Returns (created, updated) counts."""
    try:
        from django_regional.models import Language as RegionalLanguage
    except ImportError:
        logger.info("django_regional not installed, skipping language sync")
        return 0, 0

    if sync_all:
        regional_languages = RegionalLanguage.objects.all()
    else:
        try:
            from django_pim.models import Channel

            channel_lang_ids = set(Channel.objects.values_list("languages__pk", flat=True).exclude(languages__pk=None))
            regional_languages = RegionalLanguage.objects.filter(pk__in=channel_lang_ids)
        except ImportError:
            regional_languages = RegionalLanguage.objects.all()

    created_count = 0
    updated_count = 0
    for reg_lang in regional_languages:
        obj, created = Language.objects.update_or_create(
            iso2__iexact=reg_lang.iso2,
            defaults={
                "iso2": reg_lang.iso2.upper(),
                "iso3": reg_lang.iso3.upper(),
                "name_en": getattr(reg_lang, "name_en", ""),
                "name_pl": getattr(reg_lang, "name_pl", ""),
            },
        )
        if created:
            created_count += 1
        else:
            updated_count += 1

    return created_count, updated_count
