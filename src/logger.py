"""Typed logger: two names, two integers, no silent cast. Do not log full API keys."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_FORBIDDEN_G_ALIASES = frozenset(
    {
        "g",
        "g_pass",
        "g_score",
        "success",
        "flag_as_success",
        "G",
    }
)


def redact_key(value: str) -> str:
    if not value:
        return ""
    if value.startswith("yk_live_") and len(value) > 12:
        return "yk_live_***"
    if len(value) > 8:
        return value[:4] + "***"
    return "***"


@dataclass(frozen=True)
class TraceRecord:
    item_id: str
    arm: str
    pi_k: str
    hash_L: dict[str, str]
    r_pass: bool
    w_after_r: int
    token_volume: int
    SOURCE: str
    model_id: str
    protocol_version: str
    allele: str = "tool"
    grammar: str = "optional_v0"
    xml_W: int = 0
    text_W: int = 0
    text_W_global: int = 0
    lemma_present_after_r: bool = False
    lemma_is_none: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.r_pass, bool):
            raise TypeError("r_pass is a boolean predicate; it is not a G integer")
        if not isinstance(self.w_after_r, int) or isinstance(self.w_after_r, bool):
            raise TypeError("w_after_r is an int count; it is not r_pass")
        if not isinstance(self.xml_W, int) or isinstance(self.xml_W, bool):
            raise TypeError("xml_W is an int count")
        if not isinstance(self.text_W, int) or isinstance(self.text_W, bool):
            raise TypeError("text_W is an int count")
        if not isinstance(self.text_W_global, int) or isinstance(
            self.text_W_global, bool
        ):
            raise TypeError("text_W_global is an int count")
        if not isinstance(self.lemma_present_after_r, bool):
            raise TypeError("lemma_present_after_r is a bool")
        if not isinstance(self.lemma_is_none, bool):
            raise TypeError("lemma_is_none is a bool")


def record(**fields: Any) -> TraceRecord:
    overlap = _FORBIDDEN_G_ALIASES.intersection(fields)
    if overlap:
        raise TypeError(
            f"silent cast refused: cannot store an integer under R and G ({sorted(overlap)})"
        )
    if "r_pass" in fields and "w_after_r" in fields:
        if fields["r_pass"] is fields["w_after_r"]:
            raise TypeError("silent cast refused: one integer stored under R and G")
    return TraceRecord(
        item_id=fields["item_id"],
        arm=fields["arm"],
        pi_k=fields["pi_k"],
        hash_L=fields["hash_L"],
        r_pass=fields["r_pass"],
        w_after_r=fields["w_after_r"],
        token_volume=fields["token_volume"],
        SOURCE=fields["SOURCE"],
        model_id=fields["model_id"],
        protocol_version=fields["protocol_version"],
        allele=fields.get("allele", "tool"),
        grammar=fields.get("grammar", "optional_v0"),
        xml_W=fields.get("xml_W", fields["w_after_r"]),
        text_W=fields.get("text_W", 0),
        text_W_global=fields.get("text_W_global", 0),
        lemma_present_after_r=fields.get("lemma_present_after_r", False),
        lemma_is_none=fields.get("lemma_is_none", False),
    )


def dump_jsonl(path: Path, rows: list[TraceRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(asdict(row), sort_keys=True) + "\n")

