"""Figure 1 from live stamp 20260914T083741Z. Raw 0/1 counts, two grammars."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "traces" / "api_taglaw_20260914T083741Z.jsonl"
OUT = Path(__file__).resolve().parent / "figure1_taglaw.png"

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
    "math_ie": "Incl.-excl.",
    "math_telescope": "Telescope",
    "math_vieta": "Vieta",
}


def load_rows() -> list[dict]:
    rows = []
    for line in TRACE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def matrix(rows: list[dict], grammar: str) -> dict[str, dict[str, tuple[int, int]]]:
    out: dict[str, dict[str, tuple[int, int]]] = {}
    for r in rows:
        if r["grammar"] != grammar:
            continue
        iid = r["item_id"]
        arm = r["arm"]
        out.setdefault(iid, {})[arm] = (int(bool(r["r_pass"])), int(r["xml_W"]))
    return out


def panel(ax, mat: dict, title: str, annotate_r_rose: bool) -> None:
    x = np.arange(len(ITEM_ORDER))
    width = 0.18
    omit_r = [mat[i]["omit"][0] for i in ITEM_ORDER]
    inj_r = [mat[i]["inject"][0] for i in ITEM_ORDER]
    omit_w = [mat[i]["omit"][1] for i in ITEM_ORDER]
    inj_w = [mat[i]["inject"][1] for i in ITEM_ORDER]
    ax.bar(x - 1.5 * width, omit_r, width, label="omit answer", color="#4d4d4d", edgecolor="black", linewidth=0.4)
    ax.bar(x - 0.5 * width, inj_r, width, label="inject answer", color="#1a1a1a", edgecolor="black", linewidth=0.4, hatch="//")
    ax.bar(x + 0.5 * width, omit_w, width, label="omit W", color="#c8c8c8", edgecolor="black", linewidth=0.4)
    ax.bar(x + 1.5 * width, inj_w, width, label="inject W", color="#6b8e9f", edgecolor="black", linewidth=0.4, hatch="..")
    ax.set_ylim(0, 1.35)
    ax.set_yticks([0, 1])
    ax.set_ylabel("Pass / hit (0 or 1)")
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[i] for i in ITEM_ORDER])
    ax.set_title(title, loc="left", fontsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if annotate_r_rose:
        ax.annotate(
            "answer rose",
            xy=(3 + 0.5 * width, 1.0),
            xytext=(3.05, 1.18),
            fontsize=8,
            arrowprops=dict(arrowstyle="-", lw=0.6, color="black"),
        )
    ax.legend(frameon=False, ncol=4, fontsize=8, loc="upper left")


def main() -> None:
    rows = load_rows()
    opt = matrix(rows, "optional_v0")
    man = matrix(rows, "mandatory_structure")
    fig, axes = plt.subplots(2, 1, figsize=(7.4, 5.8))
    panel(
        axes[0],
        opt,
        "A. Empty lemma permitted",
        annotate_r_rose=True,
    )
    panel(
        axes[1],
        man,
        "B. Lemma tag required; None permitted",
        annotate_r_rose=False,
    )
    fig.text(
        0.5,
        0.02,
        "Five contest-math items. Live API, openai/gpt-4o, stamp 20260914T083741Z. Missing bars are zeros.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(OUT, dpi=200)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
