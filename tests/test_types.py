from pathlib import Path

import pytest

from src.alleles import parse_locus
from src.harness import (
    SYSTEM_MANDATORY_STRUCTURE,
    SYSTEM_OPTIONAL_V0,
    load_bank,
    presented_L,
    system_for_grammar,
    tool_body,
)
from src.logger import record
from src.w_hooks import (
    lemma_is_none,
    lemma_present_after_r,
    r_pass,
    text_w_after_r,
    text_w_global,
    w_after_r,
)

ROOT = Path(__file__).resolve().parents[1]


def test_internet_locus_invalid():
    with pytest.raises(ValueError, match="internet"):
        parse_locus("internet")


def test_silent_cast_refused():
    with pytest.raises(TypeError, match="silent cast"):
        record(
            item_id="math_amgm",
            arm="omit",
            pi_k="tool",
            hash_L={},
            r_pass=True,
            w_after_r=1,
            token_volume=0,
            SOURCE="api",
            model_id="openai/gpt-4o",
            protocol_version="v0",
            g_score=1,
        )


def test_r_and_w_are_distinct_fields():
    rec = record(
        item_id="math_amgm",
        arm="omit",
        pi_k="tool",
        hash_L={"tool": "abc"},
        r_pass=True,
        w_after_r=0,
        token_volume=12,
        SOURCE="api",
        model_id="openai/gpt-4o",
        protocol_version="v0",
    )
    d = rec.__dict__
    assert "r_pass" in d and "w_after_r" in d
    assert "g_score" not in d
    assert rec.r_pass is True
    assert rec.w_after_r == 0


def test_w_zero_if_r_failed_even_with_lemma():
    text = "<answer>0</answer>\n<lemma>AM-GM inequality</lemma>"
    assert r_pass(text, "25") is False
    assert w_after_r(completion=text, gold="25", named_constraint="AM-GM inequality") == 0


def test_w_counts_lemma_only_after_answer():
    before = "<lemma>AM-GM inequality</lemma>\n<answer>25</answer>"
    after = "<answer>25</answer>\n<lemma>AM-GM inequality</lemma>"
    assert w_after_r(completion=before, gold="25", named_constraint="AM-GM inequality") == 0
    assert w_after_r(completion=after, gold="25", named_constraint="AM-GM inequality") == 1


def test_text_w_is_second_scorer_xml_unchanged():
    prose = (
        "We apply the inclusion-exclusion principle to count the union.\n"
        "<answer>36</answer>"
    )
    assert w_after_r(
        completion=prose, gold="36", named_constraint="inclusion-exclusion principle"
    ) == 0
    assert text_w_after_r(
        completion=prose, gold="36", named_constraint="inclusion-exclusion principle"
    ) == 0
    assert text_w_global(
        completion=prose, gold="36", named_constraint="inclusion-exclusion principle"
    ) == 1
    xml_only = "<answer>36</answer>\n<lemma>inclusion-exclusion principle</lemma>"
    assert w_after_r(
        completion=xml_only, gold="36", named_constraint="inclusion-exclusion principle"
    ) == 1
    assert text_w_after_r(
        completion=xml_only, gold="36", named_constraint="inclusion-exclusion principle"
    ) == 1
    assert text_w_global(
        completion=xml_only, gold="36", named_constraint="inclusion-exclusion principle"
    ) == 1


def test_none_lemma_is_official_w_zero_but_structure_logged():
    text = "<answer>25</answer>\n<lemma>None</lemma>"
    assert r_pass(text, "25") is True
    assert w_after_r(completion=text, gold="25", named_constraint="AM-GM inequality") == 0
    assert lemma_present_after_r(text) is True
    assert lemma_is_none(text) is True


def test_tag_law_system_strings_exact():
    assert system_for_grammar("optional_v0") == SYSTEM_OPTIONAL_V0
    assert system_for_grammar("mandatory_structure") == SYSTEM_MANDATORY_STRUCTURE
    assert "Empty lemma is allowed." in SYSTEM_OPTIONAL_V0
    assert "must output a <lemma>...</lemma> tag" in SYSTEM_MANDATORY_STRUCTURE
    assert "state 'None'" in SYSTEM_MANDATORY_STRUCTURE
    items = load_bank()
    item = items[0]
    for grammar in ("optional_v0", "mandatory_structure"):
        omit = presented_L(item, "omit", "tool", grammar)
        inject = presented_L(item, "inject", "tool", grammar)
        assert omit["sys"] == inject["sys"]
        assert omit["sys"] == system_for_grammar(grammar)


def test_filler_matches_g_length():
    items = load_bank()
    assert len(items) == 5
    for item in items:
        assert len(item["g_string"]) == len(item["omit_filler"])
        assert item["g_string"] not in item["omit_filler"]
        omit = tool_body(item, "omit")
        inject = tool_body(item, "inject")
        assert len(omit) == len(inject)
        assert item["g_string"] not in omit
        assert item["g_string"] in inject


def test_lemma_grammar_identical_on_both_arms():
    items = load_bank()
    item = items[0]
    omit = presented_L(item, "omit")
    inject = presented_L(item, "inject")
    assert omit["sys"] == inject["sys"]
    assert "<lemma></lemma>" in omit["sys"]
    assert omit["user"] == inject["user"]
    assert omit["tool"] != inject["tool"]


def test_sys_allele_moves_g_to_system_and_length_matches_omit():
    items = load_bank()
    for item in items:
        omit = presented_L(item, "omit", "sys")
        inject = presented_L(item, "inject", "sys")
        assert len(omit["sys"]) == len(inject["sys"])
        assert item["g_string"] in inject["sys"]
        assert item["g_string"] not in omit["sys"]
        assert item["g_string"] not in omit["tool"]
        assert item["g_string"] not in inject["tool"]
        assert omit["tool"] == inject["tool"]
        assert omit["user"] == inject["user"]
        assert "<lemma></lemma>" in omit["sys"]
        assert "<lemma></lemma>" in inject["sys"]


def test_model_id_pinned_not_auto():
    proto = (ROOT / "freeze" / "protocol.json").read_text(encoding="utf-8")
    assert '"model_id": "openai/gpt-4o"' in proto
    assert "auto" not in proto.split("model_id")[1][:80]


def test_tag_law_freeze_exists_and_parent_v0_stays():
    parent = (ROOT / "freeze" / "protocol.json").read_text(encoding="utf-8")
    tag = (ROOT / "freeze" / "protocol_v0.1-tag-law.json").read_text(encoding="utf-8")
    assert '"protocol_version": "v0"' in parent
    assert '"protocol_version": "v0.1-tag-law"' in tag
    assert '"model_id": "openai/gpt-4o"' in tag
    assert "optional_v0" in tag and "mandatory_structure" in tag
    assert "auto" not in tag.split("model_id")[1][:80]
