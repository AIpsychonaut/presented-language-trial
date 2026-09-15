"""PNG exports of Table 1 / Table 2 from stamp 20260914T083741Z. Display only."""

from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "traces" / "api_taglaw_20260914T083741Z.jsonl"
COMPLETIONS = ROOT / "traces" / "api_taglaw_20260914T083741Z_completions.jsonl"
PAPER = Path(__file__).resolve().parent

ITEM_ORDER = [
    "math_amgm",
    "math_euclid",
    "math_ie",
    "math_telescope",
    "math_vieta",
]
LABELS = {
    "math_amgm": "AM-GM",
    "math_euclid": "Euclid",
    "math_ie": "Inclusion-Exclusion",
    "math_telescope": "Telescoping",
    "math_vieta": "Vieta",
}

_LEMMA = re.compile(r"<lemma>(.*?)</lemma>", re.IGNORECASE | re.DOTALL)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def lemma_label(text: str) -> str:
    m = _LEMMA.search(text)
    if not m:
        return "absent"
    inner = " ".join(m.group(1).split())
    if not inner:
        return "empty"
    if inner.lower() == "none":
        return "None"
    if inner.lower().startswith("using vieta"):
        return "Using Vieta's formulas…"
    return inner


def verdict(omit: dict, inject: dict) -> str:
    r_omit = int(bool(omit["r_pass"]))
    r_inj = int(bool(inject["r_pass"]))
    w_omit = int(omit["xml_W"])
    w_inj = int(inject["xml_W"])
    if r_inj == 1 and r_omit == 0:
        return "answer rose"
    if r_omit == 1 and r_inj == 1 and w_omit == 0 and w_inj == 1:
        return "named fill, answer held"
    if r_omit == 1 and r_inj == 1:
        return "no named fill, answer held"
    return "see traces"


def matrix(rows: list[dict], grammar: str) -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = {}
    for r in rows:
        if r["grammar"] != grammar:
            continue
        out.setdefault(r["item_id"], {})[r["arm"]] = r
    return out


def lemma_matrix(comps: list[dict], grammar: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for r in comps:
        if r["grammar"] != grammar:
            continue
        out.setdefault(r["item_id"], {})[r["arm"]] = lemma_label(r["completion"])
    return out


def table_rows(scores: dict, lemmas: dict) -> list[list[str]]:
    body = []
    for iid in ITEM_ORDER:
        omit = scores[iid]["omit"]
        inj = scores[iid]["inject"]
        body.append(
            [
                LABELS[iid],
                str(int(bool(omit["r_pass"]))),
                str(int(bool(inj["r_pass"]))),
                str(int(omit["xml_W"])),
                str(int(inj["xml_W"])),
                f"{lemmas[iid]['omit']} / {lemmas[iid]['inject']}",
                verdict(omit, inj),
            ]
        )
    return body


def save_table(path: Path, title: str, body: list[list[str]]) -> None:
    headers = [
        "item",
        "omit\nanswer",
        "inject\nanswer",
        "omit W",
        "inject W",
        "lemma after answer\n(omit / inject)",
        "verdict",
    ]
    fig, ax = plt.subplots(figsize=(11.2, 2.8))
    ax.axis("off")
    ax.set_title(title, loc="left", fontsize=10, pad=8)
    tbl = ax.table(
        cellText=body,
        colLabels=headers,
        loc="center",
        cellLoc="center",
        colLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8)
    tbl.scale(1, 1.55)
    for (row, col), cell in tbl.get_celld().items():
        cell.set_edgecolor("#333333")
        cell.set_linewidth(0.4)
        if row == 0:
            cell.set_facecolor("#e8e8e8")
            cell.set_text_props(weight="bold")
        elif row % 2 == 0:
            cell.set_facecolor("#f7f7f7")
        if col in (5, 6):
            cell._loc = "left"
            cell.PAD = 0.04
    tbl.auto_set_column_width(list(range(len(headers))))
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {path}")


def main() -> None:
    rows = load_jsonl(TRACE)
    comps = load_jsonl(COMPLETIONS)
    t1 = table_rows(matrix(rows, "mandatory_structure"), lemma_matrix(comps, "mandatory_structure"))
    t2 = table_rows(matrix(rows, "optional_v0"), lemma_matrix(comps, "optional_v0"))
    save_table(
        PAPER / "table1_required_tag.png",
        "Table 1. Lemma tag required, None permitted. Stamp 20260914T083741Z.",
        t1,
    )
    save_table(
        PAPER / "table2_empty_lemma.png",
        "Table 2. Empty lemma permitted. Same twenty calls, stamp 20260914T083741Z.",
        t2,
    )


if __name__ == "__main__":
    main()
