# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
from types import SimpleNamespace

import pytest

from django_contentdb.enums import Action
from django_contentdb.models import ActivityLog, Content, Draft, Published, Route
from django_contentdb.services import enrichment_adapter as adapter

pytestmark = pytest.mark.django_db

DOCUMENT = {
    "language": "en",
    "title": "Orbital Foundry field notes",
    "slug": "First Post",
    "body_markdown": "## Workshop\n\nWe <script>alert(1)</script>measure **twice**.",
    "meta": {"title": "Field notes", "description": "Notes from the workshop floor."},
    "faq": [{"question": "Why measure twice?", "answer": "To cut once."}],
}


def field_proposal(draft, path, value, snapshot=None, reviewer=None):
    return SimpleNamespace(
        subject_ref=str(draft.content.uid),
        target_kind="attribute_value",
        target_locator={"path": path},
        proposed_value=value,
        current_snapshot=snapshot or {},
        reviewed_by=reviewer,
    )


def document_proposal(channel="web", reviewer=None, value=None):
    return SimpleNamespace(
        subject_ref="run:1",
        target_kind="document",
        target_locator={"channel": channel},
        proposed_value=value or DOCUMENT,
        current_snapshot={},
        result_ref="",
        reviewed_by=reviewer,
    )


def read(draft, path):
    return adapter.read_current(
        subject_ref=str(draft.content.uid), target_kind="attribute_value", target_locator={"path": path}
    )


class TestResolveTargets:
    def test_list_pages_refs(self):
        refs = [f"r{i}" for i in range(150)]
        assert adapter.resolve_targets({"mode": "list", "refs": refs}, page=2) == refs[100:]

    def test_filter_by_channel_and_content_type(self, blog_draft):
        spec = {"mode": "filter", "channel": "web", "filters": {"content_type": "blog-post"}}
        assert adapter.resolve_targets(spec) == [str(blog_draft.content.uid)]
        spec["filters"] = {"content_type": "landing"}
        assert adapter.resolve_targets(spec) == []

    def test_unknown_filter_raises(self, blog_draft):
        with pytest.raises(ValueError, match="ignored"):
            adapter.resolve_targets({"mode": "filter", "channel": "web", "filters": {"ignored": "x"}})

    def test_filter_without_channel_raises(self):
        with pytest.raises(ValueError, match="channel"):
            adapter.resolve_targets({"mode": "filter", "filters": {}})

    @pytest.mark.parametrize("mode", ["gap", "csv"])
    def test_unknown_mode_raises(self, mode):
        with pytest.raises(ValueError):
            adapter.resolve_targets({"mode": mode, "refs": ["r1"]})

    def test_find_gaps_is_empty(self):
        assert adapter.find_gaps("any", {}, {"channel": "web"}) == []


class TestReadCurrent:
    def test_static_and_content_paths(self, blog_draft):
        assert read(blog_draft, "name") == {"text": "First post"}
        assert read(blog_draft, "meta.title") == {"text": "Old title"}
        assert read(blog_draft, "meta.og_title") == {"text": ""}
        assert read(blog_draft, "content.sections.s-1.description") == {"text": "<p>Hello world</p>"}

    def test_attributes(self, blog_draft):
        assert read(blog_draft, "attributes.topic") == {"option": ""}
        assert read(blog_draft, "attributes.tags") == {"options": []}
        assert read(blog_draft, "attributes.subtitle") == {"text": ""}

    def test_document_has_no_current_value(self):
        assert adapter.read_current(subject_ref="run:1", target_kind="document", target_locator={}) == {}

    def test_unknown_draft_or_path_raises(self, blog_draft):
        with pytest.raises(ValueError):
            adapter.read_current(
                subject_ref="not-a-uid", target_kind="attribute_value", target_locator={"path": "name"}
            )
        with pytest.raises(ValueError):
            read(blog_draft, "content.body")


class TestApply:
    def test_path_merge_keeps_other_json(self, blog_draft):
        adapter.apply(field_proposal(blog_draft, "content.sections.s-1.title", {"text": "Welcome"}))
        adapter.apply(field_proposal(blog_draft, "meta.description", {"text": "New description"}))
        content = Content.objects.get(pk=blog_draft.content.pk)
        assert content.content["sections"]["s-1"] == {
            "core_type": "section-text",
            "title": "Welcome",
            "description": "<p>Hello world</p>",
        }
        assert content.content["sections"]["s-2"] == {"core_type": "section-banner", "images_set": {}}
        assert content.content["sections_order"] == ["s-1", "s-2"]
        assert content.meta == {"index": "Index", "title": "Old title", "description": "New description"}

    def test_markup_is_sanitised(self, blog_draft):
        value = {"text": '<p onclick="x()">Hi<script>alert(1)</script> <a href="javascript:x">there</a></p>'}
        adapter.apply(field_proposal(blog_draft, "content.sections.s-1.description", value))
        assert read(blog_draft, "content.sections.s-1.description") == {"text": "<p>Hi <a>there</a></p>"}

    def test_name_is_capped(self, blog_draft):
        with pytest.raises(ValueError):
            adapter.apply(field_proposal(blog_draft, "name", {"text": "x" * 129}))

    def test_missing_section_raises(self, blog_draft):
        with pytest.raises(ValueError):
            adapter.apply(field_proposal(blog_draft, "content.sections.nope.title", {"text": "x"}))

    @pytest.mark.parametrize("path", ["meta.title", "attributes.subtitle"])
    @pytest.mark.parametrize("value", [{"text": {"a": 1}}, {}])
    def test_non_string_text_raises(self, blog_draft, path, value):
        before = read(blog_draft, path)
        with pytest.raises(ValueError, match="string"):
            adapter.apply(field_proposal(blog_draft, path, value))
        assert read(blog_draft, path) == before

    def test_unknown_option_raises(self, blog_draft):
        with pytest.raises(ValueError):
            adapter.apply(field_proposal(blog_draft, "attributes.topic", {"option": "sports"}))

    def test_activity_log_carries_the_reviewer(self, blog_draft, admin_user):
        adapter.apply(field_proposal(blog_draft, "meta.title", {"text": "T"}, reviewer=admin_user))
        log = ActivityLog.objects.get()
        assert (log.user, log.action, log.object_id) == (admin_user, Action.UPDATE, blog_draft.content.pk)

    def test_no_log_without_reviewer(self, blog_draft):
        adapter.apply(field_proposal(blog_draft, "meta.title", {"text": "T"}))
        assert not ActivityLog.objects.exists()


class TestRevertAndDrift:
    def test_revert_restores_the_snapshot(self, blog_draft):
        snapshot = read(blog_draft, "extension.title")
        proposal = field_proposal(blog_draft, "extension.title", {"text": "New header"}, snapshot)
        adapter.apply(proposal)
        adapter.revert(proposal)
        assert read(blog_draft, "extension.title") == {"text": "Header"}

    def test_revert_multiselect(self, blog_draft):
        adapter.apply(field_proposal(blog_draft, "attributes.tags", {"options": ["a"]}))
        snapshot = read(blog_draft, "attributes.tags")
        proposal = field_proposal(blog_draft, "attributes.tags", {"options": ["b", "c"]}, snapshot)
        adapter.apply(proposal)
        assert read(blog_draft, "attributes.tags") == {"options": ["b", "c"]}
        adapter.revert(proposal)
        assert read(blog_draft, "attributes.tags") == {"options": ["a"]}

    def test_drift_shows_in_read_current(self, blog_draft):
        adapter.apply(field_proposal(blog_draft, "meta.title", {"text": "Applied"}))
        content = Content.objects.get(pk=blog_draft.content.pk)
        content.meta["title"] = "Edited in the CMS"
        content.save()
        assert read(blog_draft, "meta.title") == {"text": "Edited in the CMS"}


class TestCatalog:
    def test_static_and_attribute_fields(self, blog_setup):
        fields = {f["key"]: f for f in adapter.describe_fields(channel="web", language="en")}
        assert {"name", "meta.title", "extension.description"} <= set(fields)
        assert fields["name"]["max_length"] == 128
        assert fields["attributes.topic"]["type"] == "select"
        assert fields["attributes.topic"]["options"] == [
            {"value": "news", "label": "news"},
            {"value": "guides", "label": "guides"},
        ]
        assert fields["attributes.tags"]["type"] == "multiselect"
        assert fields["attributes.subtitle"]["type"] == "text"
        assert not any(key.startswith("content.") for key in fields)

    def test_draft_text_paths(self, blog_draft):
        fields = adapter.describe_fields(channel="web", subject_ref=str(blog_draft.content.uid))
        parts = {f["key"]: f for f in fields if f["key"].startswith("content.")}
        assert list(parts) == [
            "content.sections.s-1.title",
            "content.sections.s-1.description",
            "content.tiles.t-1.title",
        ]
        assert parts["content.sections.s-1.description"]["type"] == "html"
        assert parts["content.sections.s-1.title"]["label"] == "Section 1 (section-text) title"

    def test_channel_languages_main_first(self, blog_draft, blog_setup):
        from django_contentdb.models import Language

        polish = Language.objects.create(iso2="PL", iso3="POL")
        content = Content.objects.create(content={})
        other = Draft.objects.create(content_type=blog_setup.content_type, content=content, language=polish)
        other.channels.add(blog_setup.channel)
        assert adapter.channel_languages(channel="web") == ["en", "pl"]

    def test_make_locator_and_field_key(self, blog_setup):
        locator = adapter.make_locator(field_key="content.tiles.t-1.title", channel="web", language="EN")
        assert locator == {"path": "content.tiles.t-1.title", "language": "en"}
        assert adapter.make_locator(field_key="attributes.topic", channel="web", language=None) == {
            "path": "attributes.topic"
        }
        assert adapter.field_key(locator=locator) == "content.tiles.t-1.title"
        with pytest.raises(ValueError):
            adapter.make_locator(field_key="meta.robots", channel="web", language="en")
        with pytest.raises(ValueError):
            adapter.make_locator(field_key="attributes.unknown", channel="web", language=None)


class TestWriteLanguages:
    """The `write` kind asks for one locator per field × language; only the draft's own language may land."""

    def _proposals(self, draft, languages):
        locators = [adapter.make_locator(field_key="meta.title", channel="web", language=lang) for lang in languages]
        return [
            SimpleNamespace(
                subject_ref=str(draft.content.uid),
                target_kind="attribute_value",
                target_locator=locator,
                proposed_value={"text": f"Title in {locator['language']}"},
                current_snapshot={},
                reviewed_by=None,
            )
            for locator in locators
        ]

    def test_two_languages_get_distinct_locators(self, blog_draft):
        english, polish = self._proposals(blog_draft, ["en", "pl"])
        assert english.target_locator != polish.target_locator

    def test_only_the_draft_language_reads_and_applies(self, blog_draft):
        english, polish = self._proposals(blog_draft, ["en", "pl"])
        adapter.read_current(
            subject_ref=english.subject_ref, target_kind="attribute_value", target_locator=english.target_locator
        )
        adapter.apply(english)
        with pytest.raises(ValueError, match="not 'pl'"):
            adapter.read_current(
                subject_ref=polish.subject_ref, target_kind="attribute_value", target_locator=polish.target_locator
            )
        with pytest.raises(ValueError, match="not 'pl'"):
            adapter.apply(polish)
        assert read(blog_draft, "meta.title") == {"text": "Title in en"}

    def test_language_less_locator_still_works(self, blog_draft):
        adapter.apply(field_proposal(blog_draft, "meta.title", {"text": "Plain"}))
        assert read(blog_draft, "meta.title") == {"text": "Plain"}


class TestBuildContext:
    def test_plain_text_facts(self, blog_draft):
        context = adapter.build_context(subject_ref=str(blog_draft.content.uid), channel="web", language="en")
        assert context["name"] == "First post"
        assert context["route"] == "first-post"
        assert context["seo_title"] == "Old title"
        assert context["text"] == "Intro Hello world Tile title"

    def test_capped_at_3000_chars(self, blog_draft):
        content = blog_draft.content
        content.content["sections"]["s-1"]["description"] = '<p>"quoted" text </p>' * 1000
        content.save()
        context = adapter.build_context(subject_ref=str(content.uid), channel="web", language="en")
        assert len(json.dumps(context, ensure_ascii=False)) <= adapter.CONTEXT_MAX_CHARS
        assert context["text"].endswith("…")


class TestDocument:
    def test_creates_an_unpublished_blog_post(self, blog_draft, admin_user):
        result = adapter.apply(document_proposal(reviewer=admin_user))
        content = Content.objects.get(uid=result["subject_ref"])
        draft = content.draft
        assert draft.content_type.slug == "blog-post"
        assert draft.name == "Orbital Foundry field notes"
        assert draft.language.iso2 == "EN"
        assert not draft.published.exists()
        assert list(draft.channels.values_list("idx", flat=True)) == ["web"]
        assert list(draft.routes.values_list("url", flat=True)) == ["first-post-2"]
        assert content.meta["title"] == "Field notes"
        sections = [content.content["sections"][uid] for uid in content.content["sections_order"]]
        assert [s["core_type"] for s in sections] == ["section-text", "section-faq"]
        assert "<script>" not in sections[0]["description"]
        assert sections[1]["faq_items"] == [{"question": "Why measure twice?", "answer": "<p>To cut once.</p>"}]
        assert ActivityLog.objects.filter(user=admin_user, action=Action.CREATE).exists()

    def test_body_faq_heading_wins_over_faq_list(self, blog_setup):
        value = {**DOCUMENT, "body_markdown": "Text.\n\n## FAQ\n\n### Own question?\n\nOwn answer."}
        content = Content.objects.get(uid=adapter.apply(document_proposal(value=value))["subject_ref"])
        faq = [s for s in content.content["sections"].values() if s["core_type"] == "section-faq"]
        assert [item["question"] for item in faq[0]["faq_items"]] == ["Own question?"]

    def test_unknown_language_or_type_raises(self, blog_setup):
        with pytest.raises(ValueError):
            adapter.apply(document_proposal(value={**DOCUMENT, "language": "xx"}))
        blog_setup.content_type.slug = "page"
        blog_setup.content_type.save()
        with pytest.raises(ValueError):
            adapter.apply(document_proposal())

    def test_revert_deletes_the_draft_and_its_route(self, blog_setup):
        proposal = document_proposal()
        proposal.result_ref = adapter.apply(proposal)["subject_ref"]
        adapter.revert(proposal)
        assert not Content.objects.filter(uid=proposal.result_ref).exists()
        assert not Route.objects.filter(url="first-post").exists()

    def test_revert_refuses_a_published_draft(self, blog_setup):
        proposal = document_proposal()
        proposal.result_ref = adapter.apply(proposal)["subject_ref"]
        draft = Draft.objects.get(content__uid=proposal.result_ref)
        Published.objects.create(draft=draft, content=Content.objects.create(content={}))
        with pytest.raises(ValueError):
            adapter.revert(proposal)
        assert Draft.objects.filter(pk=draft.pk).exists()

    def test_revert_refuses_an_edited_draft(self, blog_setup):
        proposal = document_proposal()
        proposal.result_ref = adapter.apply(proposal)["subject_ref"]
        content = Content.objects.get(uid=proposal.result_ref)
        content.meta["title"] = "Reworked in the CMS"
        content.save()
        with pytest.raises(ValueError, match="edited"):
            adapter.revert(proposal)
        assert Draft.objects.filter(content=content).exists()

    def test_revert_of_a_missing_draft_is_a_no_op(self, blog_setup):
        proposal = document_proposal()
        proposal.result_ref = "00000000-0000-0000-0000-000000000000"
        adapter.revert(proposal)
