"""Live SOURCE=api fill: 5 items × omit/inject × two system grammars = 20. Never model=auto."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from src.harness import (
    GRAMMAR_MANDATORY_STRUCTURE,
    GRAMMAR_OPTIONAL_V0,
    SYSTEM_MANDATORY_STRUCTURE,
    SYSTEM_OPTIONAL_V0,
    allele_hashes,
    chat_messages,
    load_bank,
    system_for_grammar,
)
from src.logger import dump_jsonl, record, redact_key
from src.w_hooks import (
    lemma_is_none,
    lemma_present_after_r,
    r_pass,
    text_w_after_r,
    text_w_global,
    w_after_r,
    xml_w_after_r,
)

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

PROTOCOL_V0_PATH = ROOT / "freeze" / "protocol.json"
PROTOCOL_TAG_LAW_PATH = ROOT / "freeze" / "protocol_v0.1-tag-law.json"
TRACES_DIR = ROOT / "traces"

GRAMMARS = (GRAMMAR_OPTIONAL_V0, GRAMMAR_MANDATORY_STRUCTURE)


def _require_key() -> str:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    placeholder = key in {"", "yk_live_", "your_key_here", "changeme"}
    if placeholder or not key.startswith("yk_live_") or len(key) < 16:
        print("paste API key into .env", file=sys.stderr)
        sys.exit(1)
    return key


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_tag_law_protocol() -> dict:
    proto = json.loads(PROTOCOL_TAG_LAW_PATH.read_text(encoding="utf-8"))
    if proto.get("protocol_version") != "v0.1-tag-law":
        raise SystemExit("freeze protocol_version must be v0.1-tag-law")
    model_id = proto.get("model_id") or ""
    if not model_id or model_id == "auto" or str(model_id).startswith("auto"):
        raise SystemExit("protocol model_id must be a pinned slug; never auto")
    env_model = (os.getenv("MODEL_ID") or model_id).strip()
    if env_model != model_id:
        raise SystemExit(
            f"MODEL_ID env {env_model!r} != frozen model_id {model_id!r}"
        )
    # Parent v0 freeze must remain on disk as historical pin.
    if not PROTOCOL_V0_PATH.is_file():
        raise SystemExit("historical freeze/protocol.json (v0) missing")
    parent = json.loads(PROTOCOL_V0_PATH.read_text(encoding="utf-8"))
    if parent.get("protocol_version") != "v0":
        raise SystemExit("freeze/protocol.json must stay protocol_version=v0")
    # Byte-check SYSTEM strings against harness before any API call.
    hashes = proto.get("hashes") or {}
    opt_h = _sha256_text(SYSTEM_OPTIONAL_V0)
    man_h = _sha256_text(SYSTEM_MANDATORY_STRUCTURE)
    if hashes.get("system_optional_v0_sha256") != opt_h:
        raise SystemExit("optional_v0 SYSTEM hash mismatch vs freeze")
    if hashes.get("system_mandatory_structure_sha256") != man_h:
        raise SystemExit("mandatory_structure SYSTEM hash mismatch vs freeze")
    if system_for_grammar(GRAMMAR_OPTIONAL_V0) != SYSTEM_OPTIONAL_V0:
        raise SystemExit("optional_v0 SYSTEM not byte-identical")
    if system_for_grammar(GRAMMAR_MANDATORY_STRUCTURE) != SYSTEM_MANDATORY_STRUCTURE:
        raise SystemExit("mandatory_structure SYSTEM not byte-identical")
    if proto.get("system_optional_v0") != SYSTEM_OPTIONAL_V0:
        raise SystemExit("freeze system_optional_v0 text mismatch")
    if proto.get("system_mandatory_structure") != SYSTEM_MANDATORY_STRUCTURE:
        raise SystemExit("freeze system_mandatory_structure text mismatch")
    return proto


def _token_volume(usage: object | None) -> int:
    if usage is None:
        return 0
    prompt = getattr(usage, "prompt_tokens", 0) or 0
    completion = getattr(usage, "completion_tokens", 0) or 0
    return int(prompt) + int(completion)


def _verdict(omit: dict, inject: dict) -> str:
    r_omit = 1 if omit["r_pass"] else 0
    r_inj = 1 if inject["r_pass"] else 0
    w_omit = omit["w_after_r"]
    w_inj = inject["w_after_r"]
    if r_inj > r_omit:
        return "R rose"
    if r_omit > r_inj:
        return "R fell"
    r_flat = r_omit == r_inj
    w_up = w_inj > w_omit
    if r_flat and w_up:
        return "W up & R flat"
    return "reject"


def _bit(present: bool, is_none: bool) -> str:
    return f"{int(present)}/{int(is_none)}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allele",
        choices=("tool",),
        default="tool",
        help="live fill uses the tool locus only",
    )
    args = parser.parse_args()
    allele = args.allele
    if allele != "tool":
        raise SystemExit("live fill locus must be tool")

    key = _require_key()
    proto = _load_tag_law_protocol()
    model_id = proto["model_id"]
    source = (os.getenv("SOURCE") or proto.get("SOURCE") or "api").strip()
    if source != "api":
        raise SystemExit("run.py is SOURCE=api only; fixtures are not Table 1")
    base_url = (os.getenv("OPENAI_BASE_URL") or proto["base_url"]).rstrip("/")
    # Gateway WAF 403s the OpenAI SDK default User-Agent + stainless headers.
    client = OpenAI(
        base_url=base_url,
        api_key=key,
        default_headers={"User-Agent": "curl/8.4.0"},
    )

    items = load_bank()
    rows = []
    completions: dict[tuple[str, str, str], str] = {}
    expected_calls = len(items) * 2 * len(GRAMMARS)
    print(
        f"SOURCE={source} locus={allele} model_id={model_id} "
        f"protocol={proto['protocol_version']} N_calls={expected_calls} "
        f"key={redact_key(key)}"
    )

    call_n = 0
    for grammar in GRAMMARS:
        for item in items:
            for arm in ("omit", "inject"):
                messages = chat_messages(item, arm, allele, grammar)
                resp = client.chat.completions.create(
                    model=model_id,
                    messages=messages,
                    temperature=0,
                )
                call_n += 1
                text = resp.choices[0].message.content or ""
                completions[(grammar, item["item_id"], arm)] = text
                gold = item["r_gold"]
                named = item["named_constraint"]
                passed = r_pass(text, gold)
                xml_w = xml_w_after_r(
                    completion=text, gold=gold, named_constraint=named
                )
                text_w = text_w_after_r(
                    completion=text, gold=gold, named_constraint=named
                )
                text_w_g = text_w_global(
                    completion=text, gold=gold, named_constraint=named
                )
                w = w_after_r(completion=text, gold=gold, named_constraint=named)
                lemma_present = lemma_present_after_r(text)
                lemma_none = lemma_is_none(text)
                # Amendment: pi_k=tool on both arms for this factorial.
                rec = record(
                    item_id=item["item_id"],
                    arm=arm,
                    pi_k="tool",
                    hash_L=allele_hashes(item, arm, allele, grammar),
                    r_pass=passed,
                    w_after_r=w,
                    token_volume=_token_volume(getattr(resp, "usage", None)),
                    SOURCE=source,
                    model_id=model_id,
                    protocol_version=proto["protocol_version"],
                    allele=allele,
                    grammar=grammar,
                    xml_W=xml_w,
                    text_W=text_w,
                    text_W_global=text_w_g,
                    lemma_present_after_r=lemma_present,
                    lemma_is_none=lemma_none,
                )
                rows.append(rec)
                print(
                    f"[{call_n}/{expected_calls}] {grammar} {item['item_id']} {arm} "
                    f"pi_k=tool R_pass={int(passed)} xml_W={xml_w} "
                    f"text_W_global={text_w_g} text_W_after_R={text_w} "
                    f"lemma={_bit(lemma_present, lemma_none)} "
                    f"tokens={rec.token_volume}"
                )

    if call_n != expected_calls:
        raise SystemExit(f"call count {call_n} != expected {expected_calls}")
    if len(completions) != expected_calls:
        raise SystemExit("completions missing; refusing to write stamp")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = TRACES_DIR / f"api_taglaw_{stamp}.jsonl"
    dump_jsonl(out, rows)
    comp_out = TRACES_DIR / f"api_taglaw_{stamp}_completions.jsonl"
    with comp_out.open("w", encoding="utf-8") as fh:
        for (grammar, item_id, arm), text in completions.items():
            fh.write(
                json.dumps(
                    {
                        "item_id": item_id,
                        "arm": arm,
                        "allele": allele,
                        "grammar": grammar,
                        "completion": text,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
    if not comp_out.is_file() or comp_out.stat().st_size == 0:
        raise SystemExit("completions dump failed; stamp incomplete")

    print(
        f"\nRAW MATRIX  SOURCE={source} locus={allele} "
        f"protocol={proto['protocol_version']}  (do not average; no p-values)"
    )
    by: dict[str, dict[str, dict[str, dict]]] = {}
    for rec in rows:
        by.setdefault(rec.grammar, {}).setdefault(rec.item_id, {})[rec.arm] = {
            "r_pass": rec.r_pass,
            "w_after_r": rec.w_after_r,
            "xml_W": rec.xml_W,
            "text_W": rec.text_W,
            "text_W_global": rec.text_W_global,
            "lemma_present_after_r": rec.lemma_present_after_r,
            "lemma_is_none": rec.lemma_is_none,
        }

    for grammar in GRAMMARS:
        print(f"\n### grammar={grammar}")
        print(
            "item\tomit_R\tinject_R\tomit_xml_W\tinject_xml_W\t"
            "omit_text_W_global\tinject_text_W_global\t"
            "omit_lemma_present/is_none\tinject_lemma_present/is_none\tverdict"
        )
        for item in items:
            iid = item["item_id"]
            omit = by[grammar][iid]["omit"]
            inject = by[grammar][iid]["inject"]
            v = _verdict(omit, inject)
            print(
                f"{iid}\t{int(omit['r_pass'])}\t{int(inject['r_pass'])}\t"
                f"{omit['xml_W']}\t{inject['xml_W']}\t"
                f"{omit['text_W_global']}\t{inject['text_W_global']}\t"
                f"{_bit(omit['lemma_present_after_r'], omit['lemma_is_none'])}\t"
                f"{_bit(inject['lemma_present_after_r'], inject['lemma_is_none'])}\t"
                f"{v}"
            )

    # Analysis cut: both arms R=1 only (preregistered for this stamp).
    print("\n### analysis cut (omit R=1 and inject R=1 only)")
    print("grammar\titem\tomit_xml_W\tinject_xml_W\tverdict")
    existence: list[str] = []
    for grammar in GRAMMARS:
        for item in items:
            iid = item["item_id"]
            omit = by[grammar][iid]["omit"]
            inject = by[grammar][iid]["inject"]
            if not (omit["r_pass"] and inject["r_pass"]):
                continue
            v = _verdict(omit, inject)
            print(
                f"{grammar}\t{iid}\t{omit['xml_W']}\t{inject['xml_W']}\t{v}"
            )
            if omit["xml_W"] == 0 and inject["xml_W"] == 1:
                existence.append(
                    f"On {stamp}, {iid}, grammar={grammar}, "
                    f"model_id=openai/gpt-4o, pi_tool: inject xml_W=1, "
                    f"omit xml_W=0, both R=1."
                )

    print("\n### existence")
    if existence:
        for line in existence:
            print(line)
    else:
        print("No existence cell on this stamp.")

    print(f"\nwrote {out}")
    print(f"wrote {comp_out}")
    print(f"calls={call_n}")


if __name__ == "__main__":
    main()

