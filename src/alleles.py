"""Typed presentation loci. Catch-all 'internet' is invalid."""

from __future__ import annotations

import hashlib
from enum import Enum


class Locus(str, Enum):
    SYS = "sys"
    USER = "user"
    FILE = "file"
    TOOL = "tool"
    STIG = "stig"


_INVALID_CATCHALL = {"internet", "the internet", "web", "online"}


def parse_locus(value: str) -> Locus:
    raw = (value or "").strip().lower()
    if raw in _INVALID_CATCHALL:
        raise ValueError('catch-all "internet" is invalid')
    try:
        return Locus(raw)
    except ValueError as exc:
        raise ValueError(
            f"invalid locus {value!r}; typed loci are sys, user, file, tool, stig"
        ) from exc


def bind_L(
    *,
    system: str,
    user: str,
    tool: str | None = None,
    file_text: str | None = None,
    stig: str | None = None,
) -> dict[str, str]:
    presented: dict[str, str] = {
        Locus.SYS.value: system,
        Locus.USER.value: user,
    }
    if tool is not None:
        presented[Locus.TOOL.value] = tool
    if file_text is not None:
        presented[Locus.FILE.value] = file_text
    if stig is not None:
        presented[Locus.STIG.value] = stig
    return presented


def hash_L(presented: dict[str, str]) -> dict[str, str]:
    return {
        locus: hashlib.sha256(text.encode("utf-8")).hexdigest()
        for locus, text in presented.items()
    }
