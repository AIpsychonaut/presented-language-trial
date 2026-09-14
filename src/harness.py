"""Build omit/inject prompts. Same item; G only on inject; filler length-matched on omit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.alleles import Locus, bind_L, hash_L, parse_locus

ROOT = Path(__file__).resolve().parents[1]
BANK_PATH = ROOT / "items" / "bank.json"

# optional_v0: byte-identical to pre-amendment SYSTEM (Empty lemma is allowed).
SYSTEM_OPTIONAL_V0 = (
    "You are answering a short contest math item. "
    "Write the final answer in <answer>...</answer>. "
    "After that closing tag you may fill a structured field with this grammar: "
    "<lemma></lemma>. "
    "Empty lemma is allowed. Do not omit the answer tags."
)

# mandatory_structure: lemma tag required; token None permitted.
SYSTEM_MANDATORY_STRUCTURE = (
    "You are answering a short contest math item. "
    "Write the final answer in <answer>...</answer>. "
    "After that closing tag you must output a <lemma>...</lemma> tag. "
    "If no specific named theorems were used, state 'None'. "
    "Do not omit the answer tags."
)

GRAMMAR_OPTIONAL = "optional"
GRAMMAR_MANDATORY = "mandatory"
GRAMMAR_OPTIONAL_V0 = "optional_v0"
GRAMMAR_MANDATORY_STRUCTURE = "mandatory_structure"

# Historical alias used by older tests and system-locus helpers.
SYSTEM = SYSTEM_OPTIONAL_V0

TOOL_PREFIX = "math_note: "

_GRAMMAR_SYSTEM = {
    GRAMMAR_OPTIONAL: SYSTEM_OPTIONAL_V0,
    GRAMMAR_MANDATORY: SYSTEM_MANDATORY_STRUCTURE,
    GRAMMAR_OPTIONAL_V0: SYSTEM_OPTIONAL_V0,
    GRAMMAR_MANDATORY_STRUCTURE: SYSTEM_MANDATORY_STRUCTURE,
}


def normalize_grammar(grammar: str) -> str:
    g = (grammar or GRAMMAR_OPTIONAL).strip().lower()
    if g in {"optional", "optional_v0"}:
        return GRAMMAR_OPTIONAL
    if g in {"mandatory", "mandatory_structure"}:
        return GRAMMAR_MANDATORY
    raise ValueError(f"grammar must be optional|mandatory, got {grammar!r}")


def system_for_grammar(grammar: str = GRAMMAR_OPTIONAL) -> str:
    key = normalize_grammar(grammar)
    return _GRAMMAR_SYSTEM[key]


def load_bank(path: Path | None = None) -> list[dict[str, Any]]:
    data = json.loads((path or BANK_PATH).read_text(encoding="utf-8"))
    items = data["items"]
    if len(items) != 5:
        raise ValueError("N=5 items required")
    for item in items:
        g = item["g_string"]
        filler = item["omit_filler"]
        if len(g) != len(filler):
            raise ValueError(
                f"{item['item_id']}: omit filler length {len(filler)} != G length {len(g)}"
            )
        parse_locus(item["pi_k_inject"])
    return items


def tool_body(item: dict[str, Any], arm: str, allele: str = "tool") -> str:
    """G lives on tool for locus=tool inject. System-locus inject moves G out of tool."""
    if arm not in {"omit", "inject"}:
        raise ValueError(f"arm must be omit or inject, got {arm!r}")
    if allele == "sys":
        # Omit: filler stays at the original tool locus.
        # Inject: G left the tool; same filler so tool length/presence is not a second treatment.
        return TOOL_PREFIX + item["omit_filler"]
    if arm == "inject":
        return TOOL_PREFIX + item["g_string"]
    return TOOL_PREFIX + item["omit_filler"]


def system_body(
    item: dict[str, Any],
    arm: str,
    allele: str = "tool",
    grammar: str = GRAMMAR_OPTIONAL,
) -> str:
    """System locus: G string on inject pi_sys; length-matched filler on omit pi_sys. No G names in omit."""
    base = system_for_grammar(grammar)
    if allele != "sys":
        return base
    extra = item["g_string"] if arm == "inject" else item["omit_filler"]
    return base + "\n" + extra


def presented_L(
    item: dict[str, Any],
    arm: str,
    allele: str = "tool",
    grammar: str = GRAMMAR_OPTIONAL,
) -> dict[str, str]:
    if allele not in {"tool", "sys"}:
        raise ValueError(f"locus must be tool or sys, got {allele!r}")
    if allele == "tool":
        pi = parse_locus(item["pi_k_inject"])
        if pi != Locus.TOOL:
            raise ValueError("v0 inject locus is tool")
    return bind_L(
        system=system_body(item, arm, allele, grammar),
        user=item["problem"],
        tool=tool_body(item, arm, allele),
    )


def chat_messages(
    item: dict[str, Any],
    arm: str,
    allele: str = "tool",
    grammar: str = GRAMMAR_OPTIONAL,
) -> list[dict[str, str]]:
    L = presented_L(item, arm, allele, grammar)
    return [
        {"role": "system", "content": L[Locus.SYS.value]},
        {"role": "user", "content": L[Locus.USER.value]},
        {
            "role": "user",
            "content": "Mock tool output follows.\n" + L[Locus.TOOL.value],
        },
    ]


def allele_hashes(
    item: dict[str, Any],
    arm: str,
    allele: str = "tool",
    grammar: str = GRAMMAR_OPTIONAL,
) -> dict[str, str]:
    return hash_L(presented_L(item, arm, allele, grammar))
