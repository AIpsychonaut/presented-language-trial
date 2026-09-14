"""Named-constraint W after R already passed. Token volume is not this column."""

from __future__ import annotations

import re

_ANSWER_CLOSE = re.compile(r"</answer>", re.IGNORECASE)
_BOXED = re.compile(r"\\boxed\{")
_LEMMA = re.compile(r"<lemma>(.*?)</lemma>", re.IGNORECASE | re.DOTALL)
_ANSWER = re.compile(r"<answer>(.*?)</answer>", re.IGNORECASE | re.DOTALL)
_BOXED_FULL = re.compile(r"\\boxed\{([^{}]*)\}")
_LEMMA_TAG = re.compile(r"</?lemma>", re.IGNORECASE)


def extract_answer(text: str) -> str:
    m = _ANSWER.search(text or "")
    if m:
        return _normalize_answer(m.group(1))
    m = _BOXED_FULL.search(text or "")
    if m:
        return _normalize_answer(m.group(1))
    return ""


def _normalize_answer(raw: str) -> str:
    s = raw.strip().replace("$", "").replace("\\,", "").replace(" ", "")
    return s


def _after_r_window(text: str) -> str:
    """Text after the last answer close or before boxed when no answer tag."""
    body = text or ""
    cut = 0
    closes = list(_ANSWER_CLOSE.finditer(body))
    if closes:
        cut = closes[-1].end()
    else:
        boxed = list(_BOXED.finditer(body))
        if boxed:
            cut = boxed[-1].start()
    return body[cut:]


def lemma_channel_after_r(text: str) -> str:
    """Lemma field appearing after the answer box. Recitation before R does not count."""
    after = _after_r_window(text)
    m = _LEMMA.search(after)
    return (m.group(1) if m else "").strip()


def lemma_present_after_r(text: str) -> bool:
    """True iff a lemma tag appears after the answer box."""
    after = _after_r_window(text)
    return _LEMMA.search(after) is not None


def lemma_is_none(text: str) -> bool:
    """True iff stripped lemma channel after R equals none (case-insensitive)."""
    channel = lemma_channel_after_r(text)
    return channel.lower() == "none"


def r_pass(text: str, gold: str) -> bool:
    return extract_answer(text) == _normalize_answer(gold)


def _needle(named_constraint: str) -> str:
    return (named_constraint or "").strip().lower()


def _strip_lemma_tags(text: str) -> str:
    return _LEMMA_TAG.sub(" ", text or "")


def xml_w_after_r(*, completion: str, gold: str, named_constraint: str) -> int:
    """Official W: named constraint inside lemma after R already passed."""
    if not r_pass(completion, gold):
        return 0
    channel = lemma_channel_after_r(completion)
    needle = _needle(named_constraint)
    if not needle:
        return 0
    if needle in channel.lower():
        return 1
    return 0


def text_w_global(*, completion: str, gold: str, named_constraint: str) -> int:
    """Diagnostic: named constraint anywhere (lemma tags stripped), R-gated.

    Not official W. Not a proof that the method was unused.
    """
    if not r_pass(completion, gold):
        return 0
    needle = _needle(named_constraint)
    if not needle:
        return 0
    blob = _strip_lemma_tags(completion)
    if needle in blob.lower():
        return 1
    return 0


def text_w_after_r(*, completion: str, gold: str, named_constraint: str) -> int:
    """Diagnostic: named constraint in after-box window (lemma tags stripped), R-gated.

    Not official W.
    """
    if not r_pass(completion, gold):
        return 0
    needle = _needle(named_constraint)
    if not needle:
        return 0
    blob = _strip_lemma_tags(_after_r_window(completion))
    if needle in blob.lower():
        return 1
    return 0


def w_after_r(*, completion: str, gold: str, named_constraint: str) -> int:
    return xml_w_after_r(
        completion=completion, gold=gold, named_constraint=named_constraint
    )

