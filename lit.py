#!/usr/bin/env python3
"""Lit v3 — one unread language. AIs emit L3. Dumb runner.

  python lit.py test
  python lit.py land/hello.litg
  python lit.py land/lang.litg
  python lit.py land/fract.litg
"""
from __future__ import annotations

import json
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

BOX = Path(__file__).resolve().parent
HOUSE = BOX.parent / "house"
WORK = BOX / "work"
STREAM = WORK / "LIT.jsonl"

OPS = frozenset(
    {
        "seq",
        "say",
        "read",
        "write",
        "put",
        "seal",
        "fail",
        "eq",
        "if",
        "run",
        "mark",
        "pred",
        "got",
        "light",
        "next",
        "tick",
        "report",
        "push",
        "quote",
        "do",
        "see",
        "hear",
        "rep",
        "cap",
        "need",
        "near",
        "last",
        "have",
        "copy",
        "dup",
        "swap",
        "drop",
    }
)
EVENT_KEYS = frozenset({"ch", "slot", "evd", "who", "ill", "asp", "body", "braid", "g"})
OP_KEYS: dict[str, frozenset[str]] = {
    "seq": frozenset({"op", "body"}),
    "say": frozenset({"op", "a"}),
    "read": frozenset({"op", "a"}),
    "write": frozenset({"op", "a", "b"}),
    "put": frozenset({"op", "a", "b"}),
    "seal": frozenset({"op", "a", "body", "who", "slot", "braid", "g"}),
    "fail": frozenset({"op", "a"}),
    "eq": frozenset({"op", "a", "b"}),
    "if": frozenset({"op", "a", "b", "then", "else"}),
    "run": frozenset({"op", "a"}),
    "mark": frozenset({"op", "a"}) | EVENT_KEYS,
    "pred": frozenset({"op", "a", "ch", "who", "slot"}) | EVENT_KEYS,
    "got": frozenset({"op", "a", "who"}) | EVENT_KEYS,
    "light": frozenset({"op", "braid"}),
    "next": frozenset({"op", "braid", "ch", "who", "g"}),
    "tick": frozenset({"op", "braid"}),
    "report": frozenset({"op"}),
    "push": frozenset({"op", "a", "body"}),
    "quote": frozenset({"op", "a", "body"}),
    "do": frozenset({"op", "a"}),
    "see": frozenset({"op", "a", "who", "slot", "braid", "g"}),
    "hear": frozenset({"op", "a", "who", "slot", "braid", "g"}),
    "rep": frozenset({"op", "a", "body"}),
    "cap": frozenset({"op"}),
    "need": frozenset({"op", "a"}),
    "near": frozenset({"op", "braid"}),
    "last": frozenset({"op", "braid", "ch"}),
    "have": frozenset({"op", "braid"}),
    "copy": frozenset({"op", "a", "b"}),
    "dup": frozenset({"op"}),
    "swap": frozenset({"op"}),
    "drop": frozenset({"op"}),
}
NEED_NO = frozenset({"net", "http", "house", "eval", "python", "delete", "import", "soul"})
EVD_RANK = {"seal": 5, "see": 4, "hear": 3, "sense": 3, "told": 2, "guess": 1}
CH = frozenset({"text", "pic", "sound", "sense", "act"})
SLOT = frozenset({"dark", "lit"})
EVD = frozenset({"see", "hear", "sense", "told", "guess", "seal"})
WHO = frozenset({"joseph", "vic", "grok", "vicky", "unknown"})
ILL = frozenset({"say", "do", "ask", "pred", "seal"})
ASP = frozenset({"open", "done"})
OP_LIST = tuple(sorted(OPS))
OP_CODE = {n: i for i, n in enumerate(OP_LIST)}
CODE_OP = {i: n for n, i in OP_CODE.items()}
CH_LIST = tuple(sorted(CH))
EVD_LIST = tuple(sorted(EVD))
WHO_LIST = tuple(sorted(WHO))
ILL_LIST = tuple(sorted(ILL))
SLOT_LIST = ("dark", "lit")
ASP_LIST = ("open", "done")
SEAL_WHO = frozenset({"joseph", "vic"})
WRITE_EXT = frozenset({".jsonl", ".md", ".txt", ".json", ".litg"})
MAX_RUN = 8
MAX_REP = 32
MAX_OPS = 32
MAX_STACK = 64
MAX_BODY = 4000
MAX_BRAID = 32
BRAID_NEED = frozenset(
    {"mark", "pred", "got", "light", "next", "tick", "near", "last", "have", "seal", "see", "hear"}
)


def _check_braid(br: str, *, need: str = "") -> str:
    """Named braid: any-script letter start, NFC identity. Latin is not required."""
    br = unicodedata.normalize("NFC", str(br or ""))
    if not br:
        if need:
            raise RuntimeError(need + " needs braid")
        return ""
    if len(br) > MAX_BRAID or not br[0].isalpha():
        raise RuntimeError("bad braid")
    if any(not (c.isalnum() or c == "_") for c in br[1:]):
        raise RuntimeError("bad braid")
    return br


def _need_braid(op: dict, name: str) -> str:
    return _check_braid(str(op.get("braid") or ""), need=name)


def pack_g(*, ch: str = "text", slot: str = "dark", evd: str = "see", who: str = "vic", ill: str = "do", asp: str = "open") -> int:
    """One number = channel + lit + evidential + who + speech-act + aspect."""
    return (
        CH_LIST.index(ch)
        | (SLOT_LIST.index(slot) << 3)
        | (EVD_LIST.index(evd) << 4)
        | (WHO_LIST.index(who) << 7)
        | (ILL_LIST.index(ill) << 10)
        | (ASP_LIST.index(asp) << 13)
    )


def stamp_g(row: dict) -> dict:
    """Pack grammar into g and drop English keys from RAM."""
    row = dict(row)
    row["g"] = pack_g(
        ch=ev(row, "ch") or "text",
        slot=ev(row, "slot") or "dark",
        evd=ev(row, "evd") or "see",
        who=ev(row, "who") or "vic",
        ill=ev(row, "ill") or "do",
        asp=ev(row, "asp") or "open",
    )
    for k in ("ch", "slot", "evd", "who", "ill", "asp"):
        row.pop(k, None)
    return row


def unpack_g(g: int) -> dict:
    g = int(g)
    return {
        "ch": CH_LIST[g & 7],
        "slot": SLOT_LIST[(g >> 3) & 1],
        "evd": EVD_LIST[(g >> 4) & 7],
        "who": WHO_LIST[(g >> 7) & 7],
        "ill": ILL_LIST[(g >> 10) & 7],
        "asp": ASP_LIST[(g >> 13) & 1],
    }


def ev(row: dict, key: str, default: str = ""):
    """Read event grammar from packed g. No English required in RAM."""
    if key not in ("ch", "slot", "evd", "who", "ill", "asp"):
        v = row.get(key)
        return default if v is None or v == "" else v
    v = row.get(key)
    if v not in (None, ""):
        return str(v)
    g = row.get("g")
    if g is None:
        return default
    try:
        if isinstance(g, str) and not str(g).isdigit():
            g = decode_g_token(g)
        return str(unpack_g(int(g)).get(key) or default)
    except (ValueError, IndexError, TypeError, RuntimeError):
        return default


# Silent determinatives on the wire (Egyptian classifier steal). Not Arabic digits. Not English.
FEAT_CH = {"act": "⚒", "pic": "▧", "sense": "◉", "sound": "♫", "text": "¶"}
FEAT_SLOT = {"dark": "░", "lit": "▓"}
FEAT_EVD = {"guess": "◌", "hear": "◈", "seal": "◆", "see": "◎", "sense": "◔", "told": "◇"}
FEAT_WHO = {"grok": "♖", "joseph": "♔", "unknown": "♘", "vic": "♕", "vicky": "♗"}
FEAT_ILL = {"ask": "✗", "do": "✖", "pred": "✦", "say": "✚", "seal": "★"}
FEAT_ASP = {"done": "●", "open": "○"}
UNFEAT_CH = {v: k for k, v in FEAT_CH.items()}
UNFEAT_SLOT = {v: k for k, v in FEAT_SLOT.items()}
UNFEAT_EVD = {v: k for k, v in FEAT_EVD.items()}
UNFEAT_WHO = {v: k for k, v in FEAT_WHO.items()}
UNFEAT_ILL = {v: k for k, v in FEAT_ILL.items()}
UNFEAT_ASP = {v: k for k, v in FEAT_ASP.items()}
if len(UNFEAT_CH) != len(FEAT_CH) or len(UNFEAT_EVD) != len(FEAT_EVD):
    raise RuntimeError("feat table broken")


def encode_g(g: object) -> str:
    if isinstance(g, str) and g and not g.isdigit():
        decode_g_token(g)
        return g
    u = unpack_g(int(g or 0))
    return (
        FEAT_CH[u["ch"]]
        + FEAT_SLOT[u["slot"]]
        + FEAT_EVD[u["evd"]]
        + FEAT_WHO[u["who"]]
        + FEAT_ILL[u["ill"]]
        + FEAT_ASP[u["asp"]]
    )


def decode_g_token(s: str) -> int:
    s = str(s or "")
    if not s:
        raise RuntimeError("bad g")
    if s.isdigit():
        return int(s)
    if len(s) != 6:
        raise RuntimeError("bad g")
    ch, slot, evd, who, ill, asp = (
        UNFEAT_CH.get(s[0]),
        UNFEAT_SLOT.get(s[1]),
        UNFEAT_EVD.get(s[2]),
        UNFEAT_WHO.get(s[3]),
        UNFEAT_ILL.get(s[4]),
        UNFEAT_ASP.get(s[5]),
    )
    if None in (ch, slot, evd, who, ill, asp):
        raise RuntimeError("bad g")
    return pack_g(ch=ch, slot=slot, evd=evd, who=who, ill=ill, asp=asp)


def encode_ch(ch: str) -> str:
    ch = str(ch or "text")
    if ch in FEAT_CH:
        return FEAT_CH[ch]
    if ch in UNFEAT_CH:
        return ch
    raise RuntimeError("bad ch")


def decode_ch(s: str) -> str:
    s = str(s or "text")
    if s in CH:
        return s
    if s in UNFEAT_CH:
        return UNFEAT_CH[s]
    raise RuntimeError("bad ch")


def normalize_op(op: object) -> dict:
    """dict English/numeric, or compact list [code_or_name, a?, b?] or [code, {fields}]."""
    if isinstance(op, dict):
        return op
    if isinstance(op, (list, tuple)) and op:
        out: dict = {"op": op[0]}
        if len(op) == 2 and isinstance(op[1], dict):
            if "op" in op[1]:
                raise RuntimeError("compact list fields cannot include op")
            out.update(op[1])
        elif len(op) >= 2:
            out["a"] = op[1]
            if len(op) >= 3:
                out["b"] = op[2]
        return out
    raise RuntimeError("op must be object")


def encode_op(op: object) -> dict:
    op = dict(normalize_op(op))
    raw = op.get("op")
    if type(raw) is bool:
        raise RuntimeError("unknown op")
    if isinstance(raw, int):
        name = CODE_OP.get(raw)
        if not name:
            raise RuntimeError("unknown op " + str(raw))
    else:
        name = str(raw or "")
        if name not in OP_CODE:
            raise RuntimeError("unknown op: " + name)
    out: dict = {"op": OP_CODE[name]}
    for k, v in op.items():
        if k == "op":
            continue
        if k in ("body", "then", "else") and isinstance(v, list) and v and not isinstance(v[0], (str, int, float)):
            out[k] = [encode_op(x) for x in v]
        else:
            out[k] = v
    if name in ("mark", "pred", "got", "seal", "see", "hear", "next"):
        if "g" not in out:
            out["g"] = pack_g(
                ch=str(op.get("ch") or ("sense" if name == "next" else "text")),
                slot=str(op.get("slot") or "dark"),
                evd="guess" if name == "pred" else str(op.get("evd") or "see"),
                who=str(op.get("who") or "vic"),
                ill="pred" if name == "pred" else str(op.get("ill") or "do"),
                asp=str(op.get("asp") or "open"),
            )
        for k in ("ch", "slot", "evd", "who", "ill", "asp"):
            out.pop(k, None)
    return out


# Wire glyphs (one sign = one op). English names never appear on this wire.
GLYPH = {
    "cap": "⚙",
    "copy": "⎘",
    "do": "▶",
    "drop": "⤵",
    "dup": "⧉",
    "eq": "≡",
    "fail": "⊥",
    "got": "◊",
    "have": "∃",
    "hear": "♪",
    "if": "⊃",
    "last": "⊣",
    "light": "☀",
    "mark": "†",
    "near": "∼",
    "need": "¿",
    "next": "→",
    "pred": "‡",
    "push": "⊞",
    "put": "⊡",
    "quote": "⌜",
    "read": "⊏",
    "rep": "⟳",
    "report": "☰",
    "run": "⏩",
    "say": "⊠",
    "seal": "▣",
    "see": "◐",
    "seq": "∘",
    "swap": "⇄",
    "tick": "⌇",
    "write": "⊐",
}
UNGLYPH = {v: k for k, v in GLYPH.items()}
if len(GLYPH) != len(OPS) or len(UNGLYPH) != len(GLYPH):
    raise RuntimeError("glyph table broken")
GLYPH_HDR = "L3"


def _esc_glyph_str(s: str) -> str:
    return s.replace("\\", "\\\\").replace("›", "\\›")


def _glyph_str(s: str) -> str:
    return "‹" + _esc_glyph_str(str(s)) + "›"


def _glyph_block(ops: list) -> str:
    return "〖" + "".join(encode_glyph_op(x) for x in ops) + "〗"


def encode_glyph_op(op: object) -> str:
    op = dict(normalize_op(op))
    raw = op.get("op")
    if isinstance(raw, int):
        name = CODE_OP.get(raw)
        if not name:
            raise RuntimeError("unknown op " + str(raw))
    else:
        name = str(raw or "")
    if name not in GLYPH:
        raise RuntimeError("no glyph for " + name)
    if name in BRAID_NEED:
        _need_braid(op, name)
    fn = GLYPH_ENC.get(name)
    if fn is None:
        raise RuntimeError("no glyph encode " + name)
    return fn(op, GLYPH[name])


def _genc_bare(op: dict, g: str) -> str:
    return g


def _genc_a(op: dict, g: str) -> str:
    return _glyph_str(op.get("a") or "") + g


def _need_name(raw: object) -> str:
    s = str(raw or "").strip()
    if not s:
        return ""
    if s in UNGLYPH:
        return UNGLYPH[s]
    if s.isdigit():
        try:
            n = int(s)
        except ValueError:
            n = -1
        if n in CODE_OP:
            return CODE_OP[n]
    return s.lower()


def _genc_need(op: dict, g: str) -> str:
    name = _need_name(op.get("a"))
    sign = GLYPH.get(name) or str(op.get("a") or "")
    return _glyph_str(sign) + g


def _genc_ab(op: dict, g: str) -> str:
    return _glyph_str(op.get("a") or "") + _glyph_str(op.get("b") or "") + g


def _genc_seq(op: dict, g: str) -> str:
    return _glyph_block(op.get("body") or []) + g


def _genc_if(op: dict, g: str) -> str:
    return _glyph_block(op.get("then") or []) + _glyph_block(op.get("else") or []) + g


def _genc_quote(op: dict, g: str) -> str:
    return _glyph_str(op.get("a") or "") + _glyph_block(op.get("body") or []) + g


def _genc_rep(op: dict, g: str) -> str:
    return _glyph_str(op.get("a") or "0") + _glyph_block(op.get("body") or []) + g


def _genc_eq(op: dict, g: str) -> str:
    if "a" in op or "b" in op:
        return _glyph_str(op.get("a") or "") + _glyph_str(op.get("b") or "") + g
    return g


def _genc_mark(op: dict, g: str) -> str:
    gv = op.get("g")
    if gv is None:
        gv = pack_g(
            ch=str(op.get("ch") or "text"),
            slot=str(op.get("slot") or "dark"),
            evd=str(op.get("evd") or "see"),
            who=str(op.get("who") or "vic"),
            ill=str(op.get("ill") or "do"),
            asp=str(op.get("asp") or "open"),
        )
    return _glyph_str(encode_g(gv)) + _glyph_str(op.get("braid") or "") + _glyph_str(op.get("body") or op.get("a") or "") + g


def _genc_predgot(op: dict, g: str) -> str:
    name = str(op.get("op") or "")
    if isinstance(op.get("op"), int):
        name = CODE_OP.get(op.get("op")) or ""
    gv = op.get("g")
    if gv is None:
        gv = pack_g(
            ch=str(op.get("ch") or "text"),
            slot=str(op.get("slot") or "dark"),
            evd="guess" if name == "pred" else str(op.get("evd") or "see"),
            who=str(op.get("who") or "vic"),
            ill="pred" if name == "pred" else str(op.get("ill") or "do"),
            asp=str(op.get("asp") or "open"),
        )
    return _glyph_str(encode_g(gv)) + _glyph_str(op.get("braid") or "") + _glyph_str(op.get("a") or op.get("body") or "") + g


def _genc_braid(op: dict, g: str) -> str:
    return _glyph_str(op.get("braid") or "") + g


def _genc_next(op: dict, g: str) -> str:
    return _glyph_str(op.get("braid") or "") + _glyph_str(encode_ch(str(op.get("ch") or "text"))) + g


def _genc_seala(op: dict, g: str) -> str:
    return _glyph_str(op.get("braid") or "") + _glyph_str(op.get("a") or op.get("body") or "") + g


def _genc_seehear(op: dict, g: str) -> str:
    return _glyph_str(op.get("braid") or "") + _glyph_str(op.get("a") or "") + g


GLYPH_ENC = {
    "cap": _genc_bare,
    "dup": _genc_bare,
    "swap": _genc_bare,
    "drop": _genc_bare,
    "report": _genc_bare,
    "seq": _genc_seq,
    "if": _genc_if,
    "quote": _genc_quote,
    "rep": _genc_rep,
    "write": _genc_ab,
    "put": _genc_ab,
    "copy": _genc_ab,
    "eq": _genc_eq,
    "mark": _genc_mark,
    "pred": _genc_predgot,
    "got": _genc_predgot,
    "tick": _genc_braid,
    "light": _genc_braid,
    "near": _genc_braid,
    "last": _genc_braid,
    "have": _genc_braid,
    "next": _genc_next,
    "seal": _genc_seala,
    "see": _genc_seehear,
    "hear": _genc_seehear,
    "say": _genc_a,
    "fail": _genc_a,
    "read": _genc_a,
    "run": _genc_a,
    "do": _genc_a,
    "push": _genc_a,
    "need": _genc_need,
}
if set(GLYPH_ENC) != set(OPS):
    raise RuntimeError("glyph encode table incomplete")


def _gdec_bare(op: dict, take_str, take_block, pstack) -> dict:
    return op


def _gdec_a(op: dict, take_str, take_block, pstack) -> dict:
    op["a"] = take_str()
    return op


def _gdec_ab(op: dict, take_str, take_block, pstack) -> dict:
    op["b"] = take_str()
    op["a"] = take_str()
    return op


def _gdec_seq(op: dict, take_str, take_block, pstack) -> dict:
    op["body"] = take_block()
    return op


def _gdec_if(op: dict, take_str, take_block, pstack) -> dict:
    op["else"] = take_block()
    op["then"] = take_block()
    return op


def _gdec_quote(op: dict, take_str, take_block, pstack) -> dict:
    op["body"] = take_block()
    op["a"] = take_str()
    return op


def _gdec_rep(op: dict, take_str, take_block, pstack) -> dict:
    op["body"] = take_block()
    op["a"] = take_str()
    return op


def _gdec_eq(op: dict, take_str, take_block, pstack) -> dict:
    if pstack and isinstance(pstack[-1], str):
        op["b"] = take_str()
        op["a"] = take_str()
    return op


def _gdec_mark(op: dict, take_str, take_block, pstack) -> dict:
    op["body"] = take_str()
    op["braid"] = take_str()
    if pstack and isinstance(pstack[-1], str):
        op["g"] = decode_g_token(take_str())
    return op


def _gdec_predgot(op: dict, take_str, take_block, pstack) -> dict:
    op["a"] = take_str()
    op["braid"] = take_str()
    if pstack and isinstance(pstack[-1], str):
        op["g"] = decode_g_token(take_str())
    return op


def _gdec_braid(op: dict, take_str, take_block, pstack) -> dict:
    op["braid"] = take_str()
    return op


def _gdec_next(op: dict, take_str, take_block, pstack) -> dict:
    op["ch"] = decode_ch(take_str())
    op["braid"] = take_str()
    return op


def _gdec_seala(op: dict, take_str, take_block, pstack) -> dict:
    op["a"] = take_str()
    op["braid"] = take_str()
    return op


def _gdec_seehear(op: dict, take_str, take_block, pstack) -> dict:
    op["a"] = take_str()
    op["braid"] = take_str()
    return op


GLYPH_DEC = {
    "cap": _gdec_bare,
    "dup": _gdec_bare,
    "swap": _gdec_bare,
    "drop": _gdec_bare,
    "report": _gdec_bare,
    "seq": _gdec_seq,
    "if": _gdec_if,
    "quote": _gdec_quote,
    "rep": _gdec_rep,
    "write": _gdec_ab,
    "put": _gdec_ab,
    "copy": _gdec_ab,
    "eq": _gdec_eq,
    "mark": _gdec_mark,
    "pred": _gdec_predgot,
    "got": _gdec_predgot,
    "tick": _gdec_braid,
    "light": _gdec_braid,
    "near": _gdec_braid,
    "last": _gdec_braid,
    "have": _gdec_braid,
    "next": _gdec_next,
    "seal": _gdec_seala,
    "see": _gdec_seehear,
    "hear": _gdec_seehear,
    "say": _gdec_a,
    "fail": _gdec_a,
    "read": _gdec_a,
    "run": _gdec_a,
    "do": _gdec_a,
    "push": _gdec_a,
    "need": _gdec_a,
}
if set(GLYPH_DEC) != set(OPS):
    raise RuntimeError("glyph decode table incomplete")


def encode_glyph_program(data: dict) -> str:
    if int(data.get("v") or 0) != 3:
        raise RuntimeError("need v=3")
    body = data.get("body")
    if not isinstance(body, list):
        raise RuntimeError("body must be a list")
    return GLYPH_HDR + "".join(encode_glyph_op(x) for x in body)


def _decode_glyph_stream(s: str, i: int, end: int) -> tuple[list, int]:
    ops: list = []
    pstack: list = []

    def take_str() -> str:
        if not pstack or not isinstance(pstack[-1], str):
            raise RuntimeError("prefix not postfix")
        return pstack.pop()

    def take_block() -> list:
        if not pstack or not isinstance(pstack[-1], list):
            raise RuntimeError("prefix not postfix")
        return pstack.pop()

    while i < end:
        ch = s[i]
        if ch in " \n\r\t":
            i += 1
            continue
        if ch == "‹":
            i += 1
            buf = []
            while i < end:
                c = s[i]
                if c == "\\" and i + 1 < end:
                    buf.append(s[i + 1])
                    i += 2
                    continue
                if c == "›":
                    i += 1
                    break
                buf.append(c)
                i += 1
            else:
                raise RuntimeError("unterminated ‹")
            pstack.append("".join(buf))
            continue
        if ch == "〖":
            depth = 1
            i += 1
            start = i
            while i < end and depth:
                if s[i] == "〖":
                    depth += 1
                elif s[i] == "〗":
                    depth -= 1
                    if depth == 0:
                        break
                i += 1
            if depth:
                raise RuntimeError("unterminated 〖")
            inner, _ = _decode_glyph_stream(s, start, i)
            pstack.append(inner)
            i += 1
            continue
        if ch == "〗":
            break
        name = UNGLYPH.get(ch)
        if not name:
            raise RuntimeError("unknown glyph " + ch)
        i += 1
        dfn = GLYPH_DEC.get(name)
        if dfn is None:
            raise RuntimeError("no glyph decode " + name)
        ops.append(dfn({"op": name}, take_str, take_block, pstack))
    if pstack:
        raise RuntimeError("glyph unused payload")
    return ops, i


def decode_glyph_program(s: str) -> dict:
    s = (s or "").strip()
    if s.startswith(GLYPH_HDR):
        s = s[len(GLYPH_HDR) :]
    ops, i = _decode_glyph_stream(s, 0, len(s))
    if i < len(s) and s[i:].strip():
        raise RuntimeError("glyph trailing junk")
    return {"v": 3, "lang": "lit", "body": ops}


def load_json_bootstrap(text: str) -> dict:
    """English JSON is a teacher cheat. Not the language."""
    data = json.loads(text)
    if not isinstance(data, dict):
        raise RuntimeError("json bootstrap must be object")
    return data


def load_program_text(text: str) -> dict:
    t = (text or "").lstrip()
    if t.startswith(GLYPH_HDR):
        return decode_glyph_program(t)
    raise RuntimeError("json is bootstrap; emit L3")


def encode_program(data: dict) -> dict:
    if int(data.get("v") or 0) != 3:
        raise RuntimeError("need v=3")
    body = data.get("body")
    if not isinstance(body, list):
        raise RuntimeError("body must be a list")
    return {"v": 3, "lang": "lit", "body": [encode_op(x) for x in body]}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _inside(path: Path) -> Path:
    raw = Path(str(path))
    p = (BOX / raw).resolve() if not raw.is_absolute() else raw.resolve()
    try:
        p.relative_to(BOX.resolve())
    except ValueError as exc:
        raise RuntimeError("BLEED blocked: path outside sandbox") from exc
    try:
        p.relative_to(HOUSE.resolve())
        raise RuntimeError("BLEED blocked: path is Vic house")
    except ValueError:
        pass
    if "JoeysAI" in str(p):
        raise RuntimeError("BLEED blocked: old house")
    return p


STREAM_KEEP = ("t", "id", "g", "braid", "body", "of")


def _hydrate_row(row: dict) -> dict:
    """Disk is packed g. CPU unpacks event grammar."""
    row = dict(row)
    g = row.get("g")
    if g is None:
        return row
    try:
        if isinstance(g, str) and not str(g).isdigit():
            g = decode_g_token(g)
        packed = unpack_g(int(g))
        row.update(packed)
        row["g"] = int(g)
    except (ValueError, IndexError, TypeError, RuntimeError):
        pass
    return row


def _disk_row(row: dict) -> dict:
    """No English event keys on disk. g is the grammar."""
    row = stamp_g(dict(row))
    out: dict = {}
    for k in STREAM_KEEP:
        if k == "g":
            continue
        v = row.get(k)
        if v is None or v == "":
            continue
        out[k] = v
    out["g"] = int(row["g"])
    return out


def _load_stream() -> list[dict]:
    if not STREAM.is_file():
        return []
    out = []
    for ln in STREAM.read_text(encoding="utf-8", errors="replace").splitlines():
        if ln.strip():
            raw = json.loads(ln)
            if raw.get("g") is None:
                raw = stamp_g(_hydrate_row(raw))
            out.append(raw)
    return out


def _save_stream(rows: list[dict]) -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    with STREAM.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(_disk_row(r), ensure_ascii=False) + "\n")


class VM:
    def __init__(self) -> None:
        self.out: list[str] = []
        self.preds: dict[str, str] = {}
        self.pred_ids: dict[str, str] = {}
        self.stack: list[str] = []
        self.quotes: dict[str, list] = {}
        self.depth = 0

    def pair(self, op: dict) -> tuple[str, str]:
        if "a" in op or "b" in op:
            return str(op.get("a") or ""), str(op.get("b") or "")
        if len(self.stack) < 2:
            raise RuntimeError("stack empty")
        b = self.stack.pop()
        a = self.stack.pop()
        return a, b

    def say(self, msg: str) -> None:
        self.out.append(msg)
        print(msg)

    def append_event(self, row: dict) -> dict:
        row = dict(row)
        row.setdefault("t", _utc())
        row.setdefault("ch", "text")
        row.setdefault("slot", "dark")
        row.setdefault("evd", "see")
        row.setdefault("who", "vic")
        row.setdefault("ill", "do")
        row.setdefault("asp", "open")
        row.setdefault("body", "")
        row.setdefault("braid", "")
        if row["ch"] not in CH:
            raise RuntimeError("bad ch")
        if row["slot"] not in SLOT:
            raise RuntimeError("bad slot")
        if row["evd"] not in EVD:
            raise RuntimeError("bad evd")
        if row["who"] not in WHO:
            raise RuntimeError("bad who")
        if row["ill"] not in ILL:
            raise RuntimeError("bad ill")
        if row["asp"] not in ASP:
            raise RuntimeError("bad asp")
        row["braid"] = _check_braid(str(row.get("braid") or ""))
        if len(str(row.get("body") or "")) > MAX_BODY:
            raise RuntimeError("body too long")
        if row["ill"] == "pred" and row["evd"] != "guess":
            raise RuntimeError("pred must evd=guess")
        if row["ill"] == "seal":
            if row["who"] not in SEAL_WHO:
                raise RuntimeError("who cannot seal")
            if row["evd"] != "seal" or row["asp"] != "done":
                raise RuntimeError("seal must evd=seal asp=done")
            if len(str(row["body"])) < 24:
                raise RuntimeError("seal too short")
        blob = str(row.get("body") or "") + str(row.get("a") or "")
        if "JoeysAI" in blob or "house/" in blob:
            raise RuntimeError("body names house or old plant")
        row = stamp_g(row)
        rows = _load_stream()
        row["id"] = str(len(rows) + 1)
        if ev(row, "slot") == "lit":
            fresh = []
            for old in rows:
                if ev(old, "slot") == "lit":
                    old = dict(old)
                    old["slot"] = "dark"
                    old = stamp_g(old)
                fresh.append(old)
            rows = fresh
        rows.append(row)
        _save_stream(rows)
        return row

    def run_op(self, op: dict) -> None:
        op = dict(normalize_op(op))
        if type(op.get("op")) is bool:
            raise RuntimeError("unknown op")
        op = encode_op(op)
        raw = op.get("op")
        name = CODE_OP.get(raw) if isinstance(raw, int) else str(raw or "")
        if not name or name not in OPS:
            raise RuntimeError("unknown op: " + str(raw))
        if "g" in op and name in ("mark", "pred", "got", "seal", "see", "hear", "next"):
            try:
                rawg = op.get("g")
                if isinstance(rawg, str) and not str(rawg).isdigit():
                    rawg = decode_g_token(rawg)
                packed = unpack_g(int(rawg or 0))
            except (IndexError, ValueError, TypeError, RuntimeError) as exc:
                raise RuntimeError("bad g") from exc
            for k, v in packed.items():
                op.setdefault(k, v)
        allow = OP_KEYS.get(name)
        if allow is not None:
            extra = set(op) - allow
            if "g" in op:
                extra -= {"ch", "slot", "evd", "who", "ill", "asp"}
            if extra:
                raise RuntimeError("unknown field " + ",".join(sorted(extra)))
        if name in BRAID_NEED:
            op["braid"] = _need_braid(op, name)
        code = raw if isinstance(raw, int) else OP_CODE.get(name)
        fn = OP_FN.get(code)
        if fn is None:
            raise RuntimeError("unhandled op " + str(name))
        fn(self, op)


def _fn_seq(vm: VM, op: dict) -> None:
    for child in op.get("body") or []:
        vm.run_op(child)


def _fn_fail(vm: VM, op: dict) -> None:
    raise RuntimeError(str(op.get("a") or "fail"))


def _fn_say(vm: VM, op: dict) -> None:
    vm.say(str(op.get("a") or ""))


def _fn_read(vm: VM, op: dict) -> None:
    p = _inside(Path(str(op.get("a") or "")))
    text = p.read_text(encoding="utf-8", errors="replace")[:4000]
    vm.say(text[:500])


def _fn_write(vm: VM, op: dict) -> None:
    p = _inside(Path(str(op.get("a") or "work/TODAY.jsonl")))
    if p.suffix not in WRITE_EXT:
        raise RuntimeError("write only json/jsonl/md/txt/litg")
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"at": _utc(), "via": "lit", "text": str(op.get("b") or "")}, ensure_ascii=False)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    vm.say(GLYPH["write"] + " " + str(p.relative_to(BOX)))


def _fn_put(vm: VM, op: dict) -> None:
    p = _inside(Path(str(op.get("a") or "")))
    if p.suffix not in WRITE_EXT:
        raise RuntimeError("put only json/jsonl/md/txt/litg")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(str(op.get("b") or ""), encoding="utf-8")
    vm.say(GLYPH["put"] + " " + str(p.relative_to(BOX)))


def _fn_seal(vm: VM, op: dict) -> None:
    who = str(op.get("who") or "vic")
    text = str(op.get("a") or op.get("body") or "")
    vm.append_event(
        {
            "ch": "text",
            "slot": str(op.get("slot") or "dark"),
            "evd": "seal",
            "who": who,
            "ill": "seal",
            "asp": "done",
            "body": text,
            "braid": str(op.get("braid") or ""),
        }
    )
    p = _inside(WORK / "SEALED.jsonl")
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": _utc(), "via": "lit", "text": text}, ensure_ascii=False) + "\n")
    vm.say(GLYPH["seal"])


def _fn_push(vm: VM, op: dict) -> None:
    if len(vm.stack) >= MAX_STACK:
        raise RuntimeError("stack overflow")
    vm.stack.append(str(op.get("a") or op.get("body") or ""))


def _fn_dup(vm: VM, op: dict) -> None:
    if not vm.stack:
        raise RuntimeError("stack empty")
    if len(vm.stack) >= MAX_STACK:
        raise RuntimeError("stack overflow")
    vm.stack.append(vm.stack[-1])


def _fn_swap(vm: VM, op: dict) -> None:
    if len(vm.stack) < 2:
        raise RuntimeError("stack empty")
    vm.stack[-1], vm.stack[-2] = vm.stack[-2], vm.stack[-1]


def _fn_drop(vm: VM, op: dict) -> None:
    if not vm.stack:
        raise RuntimeError("stack empty")
    vm.stack.pop()


def _fn_eq(vm: VM, op: dict) -> None:
    a, b = vm.pair(op)
    if a != b:
        raise RuntimeError("eq miss")


def _fn_if(vm: VM, op: dict) -> None:
    a, b = vm.pair(op)
    branch = op.get("then") if a == b else op.get("else")
    for child in branch or []:
        vm.run_op(child)


def _fn_quote(vm: VM, op: dict) -> None:
    key = str(op.get("a") or "")
    if not key:
        raise RuntimeError("quote needs a name")
    body = op.get("body")
    if not isinstance(body, list):
        raise RuntimeError("quote body must be list")
    vm.quotes[key] = body


def _fn_do(vm: VM, op: dict) -> None:
    key = str(op.get("a") or "")
    body = vm.quotes.get(key)
    if body is None:
        raise RuntimeError("do unknown " + key)
    for child in body:
        vm.run_op(child)


def _fn_see(vm: VM, op: dict) -> None:
    p = _inside(Path(str(op.get("a") or "")))
    if not p.is_file():
        raise RuntimeError("see missing")
    rel = str(p.relative_to(BOX)).replace("\\", "/")
    vm.append_event(
        {
            "ch": "pic",
            "slot": str(op.get("slot") or "dark"),
            "evd": "see",
            "who": str(op.get("who") or "vic"),
            "ill": "do",
            "asp": "done",
            "body": rel,
            "braid": str(op["braid"]),
        }
    )
    vm.say(GLYPH["see"] + " " + rel)


def _fn_hear(vm: VM, op: dict) -> None:
    p = _inside(Path(str(op.get("a") or "")))
    if not p.is_file():
        raise RuntimeError("hear missing")
    rel = str(p.relative_to(BOX)).replace("\\", "/")
    vm.append_event(
        {
            "ch": "sound",
            "slot": str(op.get("slot") or "dark"),
            "evd": "hear",
            "who": str(op.get("who") or "vic"),
            "ill": "do",
            "asp": "done",
            "body": rel,
            "braid": str(op["braid"]),
        }
    )
    vm.say(GLYPH["hear"] + " " + rel)


def _fn_rep(vm: VM, op: dict) -> None:
    try:
        n = int(str(op.get("a") or "0"))
    except ValueError as exc:
        raise RuntimeError("rep needs a number") from exc
    if n < 0 or n > MAX_REP:
        raise RuntimeError("rep too big")
    body = op.get("body") or []
    for _ in range(n):
        for child in body:
            vm.run_op(child)


def _fn_run(vm: VM, op: dict) -> None:
    if vm.depth >= MAX_RUN:
        raise RuntimeError("run too deep")
    p = _inside(Path(str(op.get("a") or "")))
    if not p.is_file():
        raise RuntimeError("run missing " + str(p.relative_to(BOX)))
    data = load_program_text(p.read_text(encoding="utf-8"))
    vm.depth += 1
    try:
        run_program(data, vm=vm)
    finally:
        vm.depth -= 1


def _fn_mark(vm: VM, op: dict) -> None:
    vm.append_event(
        {
            "ch": str(op.get("ch") or "text"),
            "slot": str(op.get("slot") or "dark"),
            "evd": str(op.get("evd") or "see"),
            "who": str(op.get("who") or "vic"),
            "ill": str(op.get("ill") or "do"),
            "asp": str(op.get("asp") or "open"),
            "body": str(op.get("body") or op.get("a") or ""),
            "braid": str(op.get("braid") or ""),
        }
    )


def _fn_pred(vm: VM, op: dict) -> None:
    braid = str(op["braid"])
    guess = str(op.get("a") or op.get("body") or "")
    vm.preds[braid] = guess
    row = vm.append_event(
        {
            "ch": str(op.get("ch") or "text"),
            "slot": str(op.get("slot") or "dark"),
            "evd": "guess",
            "who": str(op.get("who") or "vic"),
            "ill": "pred",
            "asp": "open",
            "body": guess,
            "braid": braid,
        }
    )
    vm.pred_ids[braid] = str(row.get("id") or "")


def _fn_got(vm: VM, op: dict) -> None:
    braid = str(op["braid"])
    actual = str(op.get("a") or op.get("body") or "")
    if not actual:
        seen = [
            r
            for r in _load_stream()
            if str(r.get("braid") or "") == braid and ev(r, "ill") not in ("pred", "ask")
        ]
        actual = str((seen[-1] if seen else {}).get("body") or "")
    want = vm.preds.get(braid)
    if want is None:
        raise RuntimeError("got without pred")
    of_id = vm.pred_ids.get(braid) or ""
    if want == actual:
        vm.append_event(
            {
                "ch": "act",
                "slot": "lit",
                "evd": "see",
                "who": str(op.get("who") or "vic"),
                "ill": "do",
                "asp": "done",
                "body": actual,
                "braid": braid,
                "of": of_id,
            }
        )
        vm.preds.pop(braid, None)
        vm.pred_ids.pop(braid, None)
        vm.say(GLYPH["got"] + braid)
        return
    vm.append_event(
        {
            "ch": "text",
            "slot": "lit",
            "evd": "told",
            "who": str(op.get("who") or "vic"),
            "ill": "ask",
            "asp": "open",
            "body": "gap want=" + want[:80] + " got=" + actual[:80],
            "braid": braid,
            "of": of_id,
        }
    )
    raise RuntimeError("pred missed braid=" + braid)


def _fn_light(vm: VM, op: dict) -> None:
    braid = str(op["braid"])
    rows = _load_stream()
    hits = [r for r in rows if str(r.get("braid") or "") == braid]
    if not hits:
        raise RuntimeError("light empty braid")

    def _rank(r: dict) -> tuple:
        return (
            EVD_RANK.get(str(ev(r, "evd") or ""), 0),
            1 if ev(r, "ill") == "do" else 0,
            int(str(r.get("id") or "0") or 0),
        )

    pick = max(hits, key=_rank)
    pick_id = pick.get("id") or pick.get("t")
    new = []
    for r in rows:
        r = dict(r)
        if ev(r, "slot") == "lit":
            r["slot"] = "dark"
        if (r.get("id") or r.get("t")) == pick_id and str(r.get("braid") or "") == braid:
            r["slot"] = "lit"
        new.append(stamp_g(r))
    _save_stream(new)
    vm.say(GLYPH["light"] + braid)


def _fn_next(vm: VM, op: dict) -> None:
    braid = str(op["braid"])
    ch = str(op.get("ch") or "text")
    rows = [r for r in _load_stream() if str(r.get("braid") or "") == braid]
    if ch:
        rows = [r for r in rows if ev(r, "ch") == ch] or rows
    if not rows:
        raise RuntimeError("next empty")
    last = rows[-1]
    body = str(last.get("body") or "0")
    if ch == "sense" or ev(last, "ch") == "sense":
        try:
            guess = str(int(body) + 1)
        except ValueError:
            guess = "1"
    else:
        guess = body or "0"
    vm.run_op({"op": "pred", "braid": braid, "ch": ch, "a": guess, "who": str(op.get("who") or "vic")})
    vm.say(GLYPH["next"] + guess)


def _fn_tick(vm: VM, op: dict) -> None:
    braid = str(op["braid"])
    rows = [
        r
        for r in _load_stream()
        if str(r.get("braid") or "") == braid and ev(r, "ch") == "sense" and ev(r, "ill") != "pred"
    ]
    n = 0
    if rows:
        try:
            n = int(str(rows[-1].get("body") or "0"))
        except ValueError:
            n = 0
    nxt = str(n + 1)
    vm.append_event(
        {
            "ch": "sense",
            "slot": "lit",
            "evd": "sense",
            "who": "vic",
            "ill": "do",
            "asp": "done",
            "body": nxt,
            "braid": braid,
        }
    )
    vm.say(GLYPH["tick"] + nxt)


def _fn_report(vm: VM, op: dict) -> None:
    rows = _load_stream()
    lit = next((r for r in reversed(rows) if ev(r, "slot") == "lit"), {})
    gap = next((r for r in reversed(rows) if ev(r, "ill") == "ask"), {})
    msg = GLYPH["report"] + " n=%s lit=%s pred=%s gap=%s" % (
        len(rows),
        str(lit.get("body") or "-")[:40],
        ",".join("%s:%s" % (k, v[:20]) for k, v in vm.preds.items()) or "-",
        str(gap.get("body") or "-")[:40],
    )
    braids = sorted({str(r.get("braid") or "") for r in rows if r.get("braid")})
    n_gap = sum(1 for r in rows if ev(r, "ill") == "ask")
    rec = {
        "at": _utc(),
        "n": len(rows),
        "lit": lit.get("body"),
        "lit_braid": lit.get("braid"),
        "pred": dict(vm.preds),
        "gap": gap.get("body"),
        "n_gap": n_gap,
        "n_braid": len(braids),
        "stack": len(vm.stack),
        "ops": len(OPS),
    }
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "LIT_REPORT.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    vm.say(msg)


def wake_spine(rows: list) -> str:
    """Human wake of the braid spine. Unpacks packed g. Not the wire."""
    lit_b = ""
    for r in reversed(rows):
        if ev(r, "slot") == "lit":
            lit_b = str(r.get("braid") or "")
            break
    seen: list[str] = []
    for r in rows:
        b = str(r.get("braid") or "")
        if b and b not in seen:
            seen.append(b)
    if not seen:
        return FEAT_SLOT["dark"]
    return " ".join(
        b + (FEAT_SLOT["lit"] if b == lit_b else FEAT_SLOT["dark"]) for b in seen
    )


def _fn_cap(vm: VM, op: dict) -> None:
    vm.say(
        GLYPH["cap"]
        + " "
        + "".join(GLYPH[n] for n in sorted(OPS))
        + " wall=sandbox no-net no-house no-eval"
    )


def _fn_need(vm: VM, op: dict) -> None:
    want = _need_name(op.get("a"))
    if want in NEED_NO or want not in OPS:
        raise RuntimeError("need denied " + (want or "?"))
    vm.say(GLYPH["need"] + GLYPH.get(want, want))


def _fn_near(vm: VM, op: dict) -> None:
    braid = str(op["braid"])
    rows = _load_stream()
    hits = [r for r in rows if str(r.get("braid") or "") == braid]
    n_lit = sum(1 for r in hits if ev(r, "slot") == "lit")
    vm.say(GLYPH["near"] + braid + " n=" + str(len(hits)) + " lit=" + str(n_lit))


def _fn_last(vm: VM, op: dict) -> None:
    braid = str(op["braid"])
    seen = [
        r
        for r in _load_stream()
        if str(r.get("braid") or "") == braid and ev(r, "ill") not in ("pred", "ask")
    ]
    ch = str(op.get("ch") or "")
    if ch:
        seen = [r for r in seen if ev(r, "ch") == ch]
    if not seen:
        raise RuntimeError("last empty braid")
    val = str(seen[-1].get("body") or "")
    vm.stack.append(val)
    vm.say(GLYPH["last"] + val[:80])


def _fn_have(vm: VM, op: dict) -> None:
    braid = str(op["braid"])
    n = sum(1 for r in _load_stream() if str(r.get("braid") or "") == braid)
    if n < 1:
        raise RuntimeError("have empty braid")
    vm.say(GLYPH["have"] + braid + " n=" + str(n))


def _fn_copy(vm: VM, op: dict) -> None:
    src = _inside(Path(str(op.get("a") or "")))
    dst = _inside(Path(str(op.get("b") or "")))
    if not src.is_file():
        raise RuntimeError("copy missing")
    if dst.suffix not in WRITE_EXT:
        raise RuntimeError("copy only json/jsonl/md/txt/litg")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())
    vm.say(
        GLYPH["copy"]
        + " "
        + str(src.relative_to(BOX))
        + " -> "
        + str(dst.relative_to(BOX))
    )


OP_FN: dict[int, object] = {}
for _n, _c in OP_CODE.items():
    _fn = globals().get("_fn_" + _n)
    if _fn is None:
        raise RuntimeError("missing handler " + _n)
    OP_FN[_c] = _fn
if set(OP_FN) != set(CODE_OP):
    raise RuntimeError("handler table incomplete")


def run_program(data: dict, vm: VM | None = None) -> VM:
    if not isinstance(data, dict):
        raise RuntimeError("program must be object")
    if int(data.get("v") or 0) != 3 or str(data.get("lang") or "") != "lit":
        raise RuntimeError("need v=3 lang=lit")
    body = data.get("body")
    if not isinstance(body, list):
        raise RuntimeError("body must be a list")
    vm = vm or VM()
    for op in body:
        vm.run_op(encode_op(op))
    return vm


def run_file(path: Path) -> VM:
    raw = Path(path)
    cwd_p = raw.resolve()
    box_p = (BOX / raw).resolve()
    cand = cwd_p if cwd_p.is_file() else box_p
    if not cand.is_file():
        raise RuntimeError("missing program " + str(raw))
    p = _inside(cand)
    return run_program(load_program_text(p.read_text(encoding="utf-8")))


def _expect_fail(fn, needle: str) -> None:
    try:
        fn()
    except RuntimeError as exc:
        if needle.lower() not in str(exc).lower():
            raise RuntimeError("wrong fail: " + str(exc) + " (want " + needle + ")") from exc
        return
    raise RuntimeError("expected fail: " + needle)


def selftest() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    if STREAM.is_file():
        STREAM.unlink()
    n_ok = 0

    def ok(name: str) -> None:
        nonlocal n_ok
        n_ok += 1
        print("PASS", name)

    run_program({"v": 3, "lang": "lit", "body": [{"op": "say", "a": "hello-lit"}]})
    ok("say")

    p = WORK / "t_write.jsonl"
    if p.is_file():
        p.unlink()
    vm = run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [
                {"op": "write", "a": "work/t_write.jsonl", "b": "built"},
                {"op": "read", "a": "work/t_write.jsonl"},
            ],
        }
    )
    if "built" not in "".join(vm.out):
        raise RuntimeError("write/read miss")
    ok("write-read")

    _expect_fail(
        lambda: run_program(
            {"v": 3, "lang": "lit", "body": [{"op": "read", "a": str(HOUSE / "YOU.md")}]}
        ),
        "BLEED",
    )
    ok("bleed-house")

    _expect_fail(
        lambda: run_program(
            {"v": 3, "lang": "lit", "body": [{"op": "read", "a": str(Path.home() / "lit-bleed-must-fail.md")}]}
        ),
        "BLEED",
    )
    ok("bleed-old")

    _expect_fail(
        lambda: run_program(
            {
                "v": 3,
                "lang": "lit",
                "body": [{"op": "seal", "who": "grok", "braid": "nope", "a": "this standing sentence is long enough xx"}],
            }
        ),
        "cannot seal",
    )
    ok("grok-no-seal")

    run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [{"op": "seal", "who": "vic", "braid": "cpu", "a": "Lit v3 runner is the sandbox CPU only."}],
        }
    )
    ok("vic-seal")

    _expect_fail(
        lambda: run_program({"v": 3, "lang": "lit", "body": [{"op": "eq", "a": "1", "b": "2"}]}),
        "eq miss",
    )
    ok("eq-miss")

    vm = run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [
                {
                    "op": "if",
                    "a": "x",
                    "b": "x",
                    "then": [{"op": "say", "a": "branch-yes"}],
                    "else": [{"op": "say", "a": "branch-no"}],
                }
            ],
        }
    )
    if "branch-yes" not in vm.out:
        raise RuntimeError("if then miss")
    ok("if-then")

    if STREAM.is_file():
        STREAM.unlink()
    run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [
                {"op": "pred", "braid": "sky", "a": "blue"},
                {"op": "got", "braid": "sky", "a": "blue"},
            ],
        }
    )
    ok("pred-got-match")

    if STREAM.is_file():
        STREAM.unlink()
    _expect_fail(
        lambda: run_program(
            {
                "v": 3,
                "lang": "lit",
                "body": [
                    {"op": "pred", "braid": "sky", "a": "blue"},
                    {"op": "got", "braid": "sky", "a": "red"},
                ],
            }
        ),
        "pred missed",
    )
    rows = _load_stream()
    if not any(ev(r, "ill") == "ask" for r in rows):
        raise RuntimeError("gap not marked")
    ok("pred-got-gap")

    if STREAM.is_file():
        STREAM.unlink()
    run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [
                {"op": "mark", "braid": "mem", "ill": "do", "body": "past-note", "slot": "dark"},
                {"op": "mark", "braid": "mem", "ill": "do", "body": "now-note", "slot": "dark", "asp": "done"},
                {"op": "light", "braid": "mem"},
            ],
        }
    )
    lit = [r for r in _load_stream() if ev(r, "slot") == "lit"]
    if len(lit) != 1 or lit[0].get("body") != "now-note":
        raise RuntimeError("light failed: " + json.dumps(lit))
    ok("light-braid")

    callee = WORK / "lit_callee.litg"
    callee.write_text(
        encode_glyph_program({"v": 3, "lang": "lit", "body": [{"op": "say", "a": "from-run"}]}),
        encoding="utf-8",
    )
    vm = run_program({"v": 3, "lang": "lit", "body": [{"op": "run", "a": "work/lit_callee.litg"}]})
    if "from-run" not in vm.out:
        raise RuntimeError("run miss")
    ok("run-compose")

    _expect_fail(
        lambda: run_program({"v": 3, "lang": "lit", "body": [{"op": "net"}]}),
        "unknown op",
    )
    ok("no-net")

    if STREAM.is_file():
        STREAM.unlink()
    run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [
                {
                    "op": "mark",
                    "braid": "truth",
                    "evd": "seal",
                    "ill": "seal",
                    "asp": "done",
                    "who": "vic",
                    "body": "sealed standing wins over later chatter xx",
                },
                {
                    "op": "mark",
                    "braid": "truth",
                    "evd": "guess",
                    "ill": "pred",
                    "who": "grok",
                    "body": "later guess",
                },
                {"op": "light", "braid": "truth"},
            ],
        }
    )
    lit = [r for r in _load_stream() if ev(r, "slot") == "lit"]
    if len(lit) != 1 or "standing" not in str(lit[0].get("body") or ""):
        raise RuntimeError("evd-rank light failed " + json.dumps(lit))
    ok("light-strongest-evd")

    if STREAM.is_file():
        STREAM.unlink()
    vm = run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [
                {"op": "tick", "braid": "pulse"},
                {"op": "next", "braid": "pulse", "ch": "sense"},
                {"op": "tick", "braid": "pulse"},
                {"op": "got", "braid": "pulse"},
            ],
        }
    )
    if not any(GLYPH["got"] in x for x in vm.out):
        raise RuntimeError("sense world miss " + str(vm.out))
    ok("sense-next-world")

    kid = encode_glyph_program({"v": 3, "lang": "lit", "body": [{"op": "say", "a": "child-built"}]})
    vm = run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [
                {"op": "put", "a": "work/built.litg", "b": kid},
                {"op": "run", "a": "work/built.litg"},
            ],
        }
    )
    if "child-built" not in vm.out:
        raise RuntimeError("put/run child miss")
    ok("lit-builds-lit")

    vm = run_program({"v": 3, "lang": "lit", "body": [{"op": "report"}]})
    if not any(x.startswith(GLYPH["report"]) for x in vm.out):
        raise RuntimeError("report miss")
    ok("report-breath")

    run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [{"op": "push", "a": "7"}, {"op": "push", "a": "7"}, {"op": "eq"}],
        }
    )
    ok("forth-stack-eq")
    _expect_fail(
        lambda: run_program(
            {
                "v": 3,
                "lang": "lit",
                "body": [{"op": "push", "a": "1"}, {"op": "push", "a": "2"}, {"op": "eq"}],
            }
        ),
        "eq miss",
    )
    ok("forth-stack-eq-miss")

    vm = run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [
                {"op": "quote", "a": "hi", "body": [{"op": "say", "a": "quoted-hi"}]},
                {"op": "do", "a": "hi"},
            ],
        }
    )
    if "quoted-hi" not in vm.out:
        raise RuntimeError("quote/do miss")
    ok("lisp-quote-do")

    if STREAM.is_file():
        STREAM.unlink()
    vm = run_program(
        {"v": 3, "lang": "lit", "body": [{"op": "see", "a": "WALL.md", "braid": "eye"}]}
    )
    if not any(x.startswith(GLYPH["see"] + " ") for x in vm.out):
        raise RuntimeError("see miss")
    ok("see-real-file")
    run_program({"v": 3, "lang": "lit", "body": [{"op": "light", "braid": "eye"}]})
    lit = [r for r in _load_stream() if ev(r, "slot") == "lit"]
    if len(lit) != 1 or lit[0].get("braid") != "eye":
        raise RuntimeError("see not lightable " + json.dumps(lit))
    ok("see-lights-braid")
    row = _load_stream()[-1]
    if "g" not in row:
        raise RuntimeError("stream missing g")
    ug = unpack_g(int(row["g"]))
    if ug.get("slot") != "lit" or ug.get("ch") != "pic":
        raise RuntimeError("stream g mismatch " + json.dumps(row))
    ok("stream-stamps-g")
    raw_ln = STREAM.read_text(encoding="utf-8").strip().splitlines()[-1]
    raw = json.loads(raw_ln)
    if any(k in raw for k in ("ch", "slot", "evd", "who", "ill", "asp")):
        raise RuntimeError("stream still english " + raw_ln)
    if "g" not in raw:
        raise RuntimeError("stream disk missing g")
    ok("stream-disk-no-english")
    ram = _load_stream()[-1]
    if any(k in ram for k in ("ch", "slot", "evd", "who", "ill", "asp")):
        raise RuntimeError("ram still english " + json.dumps(ram))
    if ev(ram, "slot") != "lit":
        raise RuntimeError("ram ev slot miss")
    ok("stream-ram-no-english")
    _expect_fail(
        lambda: run_program(
            {"v": 3, "lang": "lit", "body": [{"op": "see", "a": "work/nope.jpg", "braid": "eye"}]}
        ),
        "see missing",
    )
    ok("see-missing-fails")

    if STREAM.is_file():
        STREAM.unlink()
    vm = run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [{"op": "rep", "a": "3", "body": [{"op": "tick", "braid": "loop"}]}],
        }
    )
    ticks = [r for r in _load_stream() if r.get("braid") == "loop" and ev(r, "ch") == "sense"]
    if len(ticks) != 3 or str(ticks[-1].get("body")) != "3":
        raise RuntimeError("rep tick miss " + json.dumps(ticks))
    ok("rep-tick")

    _expect_fail(
        lambda: run_program({"v": 3, "lang": "lit", "body": [{"op": "eval", "a": "print(1)"}]}),
        "unknown op",
    )
    ok("no-python-eval")
    _expect_fail(
        lambda: run_program({"v": 3, "lang": "lit", "body": [{"op": "rep", "a": "99", "body": []}]}),
        "rep too big",
    )
    ok("rep-bounded")

    _expect_fail(
        lambda: run_program({"v": 3, "lang": "lit", "body": [{"op": "say", "text": "alias"}]}),
        "unknown field",
    )
    ok("no-alias-fields")
    vm = run_program({"v": 3, "lang": "lit", "body": [{"op": "cap"}]})
    if not any(x.startswith(GLYPH["cap"]) and "no-net" in x for x in vm.out):
        raise RuntimeError("cap miss")
    ok("cap")
    _expect_fail(
        lambda: run_program({"v": 3, "lang": "lit", "body": [{"op": "need", "a": "net"}]}),
        "need denied",
    )
    ok("need-net-denied")
    vm = run_program({"v": 3, "lang": "lit", "body": [{"op": "need", "a": "tick"}]})
    if GLYPH["need"] + GLYPH["tick"] not in vm.out:
        raise RuntimeError("need tick miss")
    ok("need-tick-ok")
    nw = encode_glyph_program({"v": 3, "lang": "lit", "body": [{"op": "need", "a": "tick"}]})
    if "tick" in nw or "need" in nw:
        raise RuntimeError("need english leak " + nw)
    vm = run_program(decode_glyph_program(nw))
    if GLYPH["need"] + GLYPH["tick"] not in vm.out:
        raise RuntimeError("need glyph miss " + str(vm.out))
    ok("need-glyph-wire")

    if len(OPS) > MAX_OPS:
        raise RuntimeError("ISA left the basin: %s ops > %s" % (len(OPS), MAX_OPS))
    ok("basin-ops")

    if STREAM.is_file():
        STREAM.unlink()
    run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [
                {
                    "op": "mark",
                    "braid": "army",
                    "body": "same-words",
                    "who": "joseph",
                    "evd": "hear",
                    "ill": "say",
                },
                {
                    "op": "mark",
                    "braid": "job",
                    "body": "same-words",
                    "who": "joseph",
                    "evd": "hear",
                    "ill": "say",
                },
                {"op": "light", "braid": "army"},
                {"op": "near", "braid": "job"},
            ],
        }
    )
    rows = _load_stream()
    army_lit = [r for r in rows if r.get("braid") == "army" and ev(r, "slot") == "lit"]
    job_lit = [r for r in rows if r.get("braid") == "job" and ev(r, "slot") == "lit"]
    job_dark = [r for r in rows if r.get("braid") == "job" and ev(r, "slot") == "dark"]
    if len(army_lit) != 1 or len(job_lit) != 0 or len(job_dark) != 1:
        raise RuntimeError("smash: two meanings collapsed")
    ok("no-smash")

    if STREAM.is_file():
        STREAM.unlink()
    run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [
                {
                    "op": "seal",
                    "who": "vic",
                    "braid": "geom",
                    "a": "imprint remains after the throat closes xx",
                },
                {"op": "tick", "braid": "noise"},
                {"op": "tick", "braid": "noise"},
                {"op": "light", "braid": "geom"},
                {"op": "near", "braid": "geom"},
            ],
        }
    )
    lit = [r for r in _load_stream() if ev(r, "slot") == "lit"]
    if len(lit) != 1 or "imprint" not in str(lit[0].get("body") or ""):
        raise RuntimeError("imprint lost after close " + json.dumps(lit))
    ok("imprint-after-close")

    vm = run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [
                {"op": "quote", "a": "leaf", "body": [{"op": "say", "a": "leaf-out"}]},
                {
                    "op": "quote",
                    "a": "fold",
                    "body": [{"op": "do", "a": "leaf"}, {"op": "say", "a": "fold-out"}],
                },
                {"op": "do", "a": "fold"},
            ],
        }
    )
    if "leaf-out" not in vm.out or "fold-out" not in vm.out:
        raise RuntimeError("fold miss " + str(vm.out))
    ok("fold-quote")

    if STREAM.is_file():
        STREAM.unlink()
    vm = run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [
                {"op": "rep", "a": "3", "body": [{"op": "tick", "braid": "w"}]},
                {"op": "last", "braid": "w"},
                {"op": "push", "a": "3"},
                {
                    "op": "if",
                    "then": [{"op": "say", "a": "world-3"}],
                    "else": [{"op": "fail", "a": "not-3"}],
                },
                {"op": "have", "braid": "w"},
            ],
        }
    )
    if "world-3" not in vm.out:
        raise RuntimeError("last/if miss " + str(vm.out))
    ok("last-stack-world")
    _expect_fail(
        lambda: run_program({"v": 3, "lang": "lit", "body": [{"op": "have", "braid": "nope"}]}),
        "have empty",
    )
    ok("have-empty-fails")

    vm = run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [
                {"op": "copy", "a": "WALL.md", "b": "work/wall_copy.md"},
                {"op": "see", "a": "work/wall_copy.md", "braid": "eye"},
            ],
        }
    )
    if not any(GLYPH["copy"] + " " in x for x in vm.out):
        raise RuntimeError("copy miss")
    ok("copy-in-box")
    _expect_fail(
        lambda: run_program(
            {"v": 3, "lang": "lit", "body": [{"op": "copy", "a": "WALL.md", "b": str(HOUSE / "NO.md")}]}
        ),
        "BLEED",
    )
    ok("copy-no-house")

    vm = run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [
                {"op": "push", "a": "same"},
                {"op": "dup"},
                {"op": "eq"},
                {"op": "report"},
            ],
        }
    )
    if not (WORK / "LIT_REPORT.json").is_file():
        raise RuntimeError("report json missing")
    ok("dup-eq")
    ok("report-json")
    _expect_fail(
        lambda: run_program({"v": 3, "lang": "lit", "body": [{"op": "dup"}]}),
        "stack empty",
    )
    ok("dup-empty-fails")

    vm = run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [{"op": "push", "a": "a"}, {"op": "push", "a": "b"}, {"op": "swap"}],
        }
    )
    if vm.stack != ["b", "a"]:
        raise RuntimeError("swap miss " + str(vm.stack))
    ok("swap")
    vm = run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [{"op": "push", "a": "keep"}, {"op": "push", "a": "gone"}, {"op": "drop"}],
        }
    )
    if vm.stack != ["keep"]:
        raise RuntimeError("drop miss " + str(vm.stack))
    ok("drop")
    _expect_fail(
        lambda: run_program(
            {
                "v": 3,
                "lang": "lit",
                "body": [
                    {"op": "rep", "a": "32", "body": [{"op": "push", "a": "x"}]},
                    {"op": "rep", "a": "32", "body": [{"op": "push", "a": "x"}]},
                    {"op": "push", "a": "x"},
                ],
            }
        ),
        "stack overflow",
    )
    ok("stack-overflow")

    if STREAM.is_file():
        STREAM.unlink()
    _expect_fail(
        lambda: run_program({"v": 3, "lang": "lit", "body": [{"op": "next", "braid": "none"}]}),
        "next empty",
    )
    ok("next-empty-fails")

    if STREAM.is_file():
        STREAM.unlink()
    run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [
                {"op": "pred", "braid": "cau", "a": "hit"},
                {"op": "got", "braid": "cau", "a": "hit"},
            ],
        }
    )
    rows = _load_stream()
    preds = [r for r in rows if ev(r, "ill") == "pred"]
    gots = [r for r in rows if ev(r, "ill") == "do" and r.get("of")]
    if not preds or not gots or gots[-1].get("of") != preds[-1].get("id"):
        raise RuntimeError("causal of miss " + json.dumps(rows))
    ok("got-of-pred")

    for name in (
        "lit_hello.json",
        "lit_world.json",
        "lit_go.json",
        "lit_ai.json",
        "lib/sense.json",
        "lib/remember.json",
    ):
        p = WORK / name
        if p.is_file():
            if STREAM.is_file():
                STREAM.unlink()
            wire = encode_glyph_program(load_json_bootstrap(p.read_text(encoding="utf-8")))
            dest = p.with_suffix(".litg")
            dest.write_text(wire, encoding="utf-8")
            run_file(dest)
    ok("corpus-programs")

    _expect_fail(
        lambda: load_program_text('{"v":3,"lang":"lit","body":[]}'),
        "json is bootstrap",
    )
    ok("json-not-the-wire")
    vm = run_program(load_json_bootstrap('{"v":3,"lang":"lit","body":[{"op":"say","a":"boot-json"}]}'))
    if "boot-json" not in vm.out:
        raise RuntimeError("json bootstrap miss")
    ok("json-bootstrap")
    junk = WORK / "nope_not_wire.json"
    junk.write_text('{"v":3,"lang":"lit","body":[{"op":"say","a":"no"}]}', encoding="utf-8")
    _expect_fail(lambda: run_file(junk), "json is bootstrap")
    ok("json-file-not-run")

    vm = run_program(
        {"v": 3, "lang": "lit", "body": [{"op": OP_CODE["say"], "a": "code-say"}]}
    )
    if "code-say" not in vm.out:
        raise RuntimeError("numeric op miss")
    ok("numeric-op")
    g = pack_g(ch="text", slot="dark", evd="hear", who="joseph", ill="say", asp="open")
    if STREAM.is_file():
        STREAM.unlink()
    run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [{"op": "mark", "g": g, "braid": "gly", "body": "packed-sign"}],
        }
    )
    rows = _load_stream()
    if not rows or ev(rows[-1], "evd") != "hear" or ev(rows[-1], "who") != "joseph":
        raise RuntimeError("packed g miss " + json.dumps(rows[-1] if rows else {}))
    ok("packed-glyph")
    _expect_fail(
        lambda: run_program({"v": 3, "lang": "lit", "body": [{"op": 99}]}),
        "unknown op",
    )
    ok("bad-code-fails")

    for ch in CH_LIST:
        for evd in EVD_LIST:
            g = pack_g(ch=ch, evd=evd, who="vic", ill="do", slot="dark", asp="open")
            u = unpack_g(g)
            if u["ch"] != ch or u["evd"] != evd:
                raise RuntimeError("g roundtrip " + ch + " " + evd)
    ok("g-roundtrip")

    vm = run_program({"v": 3, "lang": "lit", "body": [[OP_CODE["say"], "list-say"]]})
    if "list-say" not in vm.out:
        raise RuntimeError("list-form miss")
    ok("list-form-op")

    src = {"v": 3, "lang": "lit", "body": [{"op": "say", "a": "enc-hi"}, {"op": "push", "a": "1"}, {"op": "dup"}, {"op": "eq"}]}
    enc = encode_program(src)
    if enc["body"][0]["op"] != OP_CODE["say"]:
        raise RuntimeError("encode miss")
    vm = run_program(enc)
    if "enc-hi" not in vm.out:
        raise RuntimeError("encoded run miss")
    ok("encode-roundtrip")
    if not isinstance(enc["body"][0]["op"], int) or enc["body"][0]["op"] == "say":
        raise RuntimeError("intern still english op")
    ok("intern-numeric-op")
    mk = encode_op({"op": "mark", "braid": "m", "body": "x", "who": "joseph", "evd": "hear"})
    if any(k in mk for k in ("who", "evd", "ch", "slot", "ill", "asp")):
        raise RuntimeError("intern grammar still english " + json.dumps(mk))
    if unpack_g(int(mk["g"]))["who"] != "joseph" or unpack_g(int(mk["g"]))["evd"] != "hear":
        raise RuntimeError("intern g lost who/evd")
    ok("intern-g-no-english")
    if len(OP_FN) != 32 or set(OP_FN) != set(CODE_OP):
        raise RuntimeError("dispatch table")
    if OP_FN[OP_CODE["say"]] is not _fn_say:
        raise RuntimeError("dispatch not by code")
    ok("dispatch-by-code")
    if set(GLYPH_ENC) != set(OPS) or set(GLYPH_DEC) != set(OPS):
        raise RuntimeError("glyph tables")
    ok("glyph-codec-tables")

    run_program({"v": 3, "lang": "lit", "body": []})
    ok("empty-body")

    _expect_fail(
        lambda: run_program(
            {
                "v": 3,
                "lang": "lit",
                "body": [{"op": "mark", "braid": "bad braid!", "body": "x"}],
            }
        ),
        "bad braid",
    )
    ok("bad-braid")
    _expect_fail(
        lambda: run_program(
            {
                "v": 3,
                "lang": "lit",
                "body": [{"op": "mark", "braid": "z", "body": "x" * (MAX_BODY + 1)}],
            }
        ),
        "body too long",
    )
    ok("body-cap")
    _expect_fail(
        lambda: run_program({"v": 3, "lang": "lit", "body": [{"op": 1.5}]}),
        "unknown op",
    )
    ok("float-op-fails")

    if STREAM.is_file():
        STREAM.unlink()
    run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [
                [OP_CODE["tick"], {"braid": "n20"}],
                [OP_CODE["tick"], {"braid": "n20"}],
                [OP_CODE["last"], {"braid": "n20"}],
                [OP_CODE["push"], "2"],
                [OP_CODE["if"], {"then": [[OP_CODE["say"], "dense-ok"]], "else": [{"op": "fail", "a": "dense-bad"}]}],
            ],
        }
    )
    ok("dense-numeric-list")

    n_lit = sum(1 for r in _load_stream() if ev(r, "slot") == "lit")
    if n_lit > 1:
        raise RuntimeError("lit leak " + str(n_lit))
    ok("one-lit-after")

    if len(GLYPH) != 32 or len(UNGLYPH) != 32:
        raise RuntimeError("glyph count")
    ok("glyph-table")
    src = {
        "v": 3,
        "lang": "lit",
        "body": [
            {"op": "say", "a": "glyph-hi"},
            {"op": "push", "a": "q"},
            {"op": "dup"},
            {"op": "eq"},
        ],
    }
    wire = encode_glyph_program(src)
    if "say" in wire or "push" in wire:
        raise RuntimeError("english leaked on wire " + wire)
    if not wire.startswith("L3"):
        raise RuntimeError("no header")
    back = decode_glyph_program(wire)
    vm = run_program(back)
    if "glyph-hi" not in vm.out:
        raise RuntimeError("glyph run miss " + wire + " " + str(vm.out))
    ok("glyph-roundtrip")
    (WORK / "hello.litg").write_text(wire, encoding="utf-8")
    vm = run_file(WORK / "hello.litg")
    if "glyph-hi" not in vm.out:
        raise RuntimeError("litg file miss")
    ok("glyph-file")
    gsrc = {
        "v": 3,
        "lang": "lit",
        "body": [
            {"op": "push", "a": "1"},
            {"op": "push", "a": "1"},
            {
                "op": "if",
                "then": [{"op": "say", "a": "g-yes"}],
                "else": [{"op": "say", "a": "g-no"}],
            },
        ],
    }
    vm = run_program(decode_glyph_program(encode_glyph_program(gsrc)))
    if "g-yes" not in vm.out:
        raise RuntimeError("glyph if miss")
    ok("glyph-if")
    _expect_fail(lambda: decode_glyph_program("L3XYZ"), "unknown glyph")
    ok("glyph-unknown")

    tw = {
        "v": 3,
        "lang": "lit",
        "body": [
            {"op": "tick", "braid": "gw"},
            {"op": "next", "braid": "gw", "ch": "sense"},
            {"op": "tick", "braid": "gw"},
            {"op": "got", "braid": "gw"},
        ],
    }
    if STREAM.is_file():
        STREAM.unlink()
    vm = run_program(decode_glyph_program(encode_glyph_program(tw)))
    if not any(GLYPH["got"] in x for x in vm.out):
        raise RuntimeError("glyph world miss " + str(vm.out))
    ok("glyph-world")
    mk = {
        "v": 3,
        "lang": "lit",
        "body": [{"op": "mark", "braid": "m", "body": "leaf", "who": "vic", "evd": "see", "ill": "do"}],
    }
    wire = encode_glyph_program(mk)
    if "mark" in wire or "braid" in wire:
        raise RuntimeError("mark english leak " + wire)
    back = decode_glyph_program(wire)
    if back["body"][0].get("braid") != "m":
        raise RuntimeError("mark glyph miss " + json.dumps(back))
    ok("glyph-mark")

    vm = run_program(decode_glyph_program(encode_glyph_program({"v": 3, "lang": "lit", "body": [{"op": "cap"}, {"op": "report"}]})))
    if not any(x.startswith(GLYPH["cap"]) for x in vm.out):
        raise RuntimeError("glyph cap miss")
    ok("glyph-cap")
    qsrc = {
        "v": 3,
        "lang": "lit",
        "body": [
            {"op": "quote", "a": "ghi", "body": [{"op": "say", "a": "from-quote"}]},
            {"op": "do", "a": "ghi"},
        ],
    }
    vm = run_program(decode_glyph_program(encode_glyph_program(qsrc)))
    if "from-quote" not in vm.out:
        raise RuntimeError("glyph quote miss " + str(vm.out))
    ok("glyph-quote-do")
    ssrc = {
        "v": 3,
        "lang": "lit",
        "body": [{"op": "seq", "body": [{"op": "say", "a": "seq-a"}, {"op": "say", "a": "seq-b"}]}],
    }
    vm = run_program(decode_glyph_program(encode_glyph_program(ssrc)))
    if vm.out[-2:] != ["seq-a", "seq-b"]:
        raise RuntimeError("glyph seq miss " + str(vm.out))
    ok("glyph-seq")
    go = WORK / "lit_go.json"
    if go.is_file():
        gow = encode_glyph_program(json.loads(go.read_text(encoding="utf-8")))
        (WORK / "go.litg").write_text(gow, encoding="utf-8")
        if STREAM.is_file():
            STREAM.unlink()
        vm = run_file(WORK / "go.litg")
        if "go-world-ok" not in vm.out:
            raise RuntimeError("go.litg miss " + str(vm.out))
        ok("glyph-go-file")
    kpath = BOX / "KERNEL.json"
    kpath.write_text(
        json.dumps(
            {
                "lang": "lit",
                "hdr": GLYPH_HDR,
                "glyphs": GLYPH,
                "feat": {"ch": FEAT_CH, "slot": FEAT_SLOT, "evd": FEAT_EVD, "who": FEAT_WHO, "ill": FEAT_ILL, "asp": FEAT_ASP},
                "string": "‹ ›",
                "block": "〖 〗",
                "postfix": True,
                "english": "bootstrap only",
                "g": "six silent determinatives, not arabic digits",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    if not kpath.is_file():
        raise RuntimeError("kernel json miss")
    ok("kernel-json")
    vicky = WORK / "vicky.litg"
    if vicky.is_file():
        vm = run_file(vicky)
        if "vicky-hi" not in vm.out:
            raise RuntimeError("vicky.litg miss")
        ok("vicky-litg-replay")

    wire = encode_glyph_program({"v": 3, "lang": "lit", "body": [{"op": "say", "a": "rain"}]})
    rain_path = paint_rain(wire)
    if not rain_path.is_file() or rain_path.stat().st_size < 1000:
        raise RuntimeError("rain still miss")
    ok("matrix-rain-still")
    w2 = encode_glyph_program({"v": 3, "lang": "lit", "body": [{"op": "tick", "braid": "r"}, {"op": "report"}]})
    signs = [c for c in w2 if c in UNGLYPH]
    if GLYPH["tick"] not in signs or GLYPH["report"] not in signs:
        raise RuntimeError("rain glyphs miss ops")
    if any(c.isalpha() for c in signs):
        raise RuntimeError("op-glyph set leaked latin")
    paint_rain(w2)
    ok("rain-op-glyphs")
    vicky = WORK / "vicky.litg"
    if vicky.is_file():
        w = vicky.read_text(encoding="utf-8").strip()
        vm = run_program(decode_glyph_program(w))
        if "vicky-hi" not in vm.out:
            raise RuntimeError("thrust miss")
        ok("vicky-wire-truth")
    mouth = WORK / "from_vicky.litg"
    if not mouth.is_file():
        raise RuntimeError("from_vicky.litg miss")
    raw_mouth = mouth.read_text(encoding="utf-8")
    _expect_fail(lambda: decode_glyph_program(raw_mouth), "prefix not postfix")
    _expect_fail(lambda: load_program_text(raw_mouth), "prefix not postfix")
    _expect_fail(lambda: run_file(mouth), "prefix not postfix")
    ok("vicky-prefix-not-program")
    post = WORK / "vicky_postfix.litg"
    if not post.is_file():
        raise RuntimeError("vicky_postfix.litg miss")
    vm = run_file(post)
    if "自" not in vm.out:
        raise RuntimeError("vicky postfix miss " + str(vm.out))
    ok("vicky-postfix-exam")
    _expect_fail(
        lambda: decode_glyph_program(GLYPH_HDR + GLYPH["say"] + _glyph_str("hi")),
        "prefix not postfix",
    )
    ok("prefix-say-refused")
    vm = run_program(decode_glyph_program(GLYPH_HDR + _glyph_str("hi") + GLYPH["say"]))
    if "hi" not in vm.out:
        raise RuntimeError("postfix say miss")
    ok("postfix-say-ok")

    _expect_fail(
        lambda: run_program({"v": 3, "lang": "lit", "body": [{"op": "tick"}]}),
        "tick needs braid",
    )
    ok("tick-needs-braid")
    for opname in (
        "mark",
        "pred",
        "got",
        "light",
        "next",
        "near",
        "last",
        "have",
        "seal",
        "see",
        "hear",
    ):
        _expect_fail(
            lambda n=opname: run_program({"v": 3, "lang": "lit", "body": [{"op": n}]}),
            opname + " needs braid",
        )
    ok("braid-ops-need-name")
    _expect_fail(
        lambda: run_program({"v": 3, "lang": "lit", "body": [{"op": "light", "braid": "_"}]}),
        "bad braid",
    )
    ok("underscore-braid-fails")
    if STREAM.is_file():
        STREAM.unlink()
    run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [
                {"op": "mark", "braid": "記憶", "body": "leaf-east"},
                {"op": "light", "braid": "記憶"},
            ],
        }
    )
    lit = [r for r in _load_stream() if ev(r, "slot") == "lit"]
    if len(lit) != 1 or lit[0].get("braid") != "記憶":
        raise RuntimeError("unicode braid miss " + json.dumps(lit))
    ok("braid-any-script")
    if STREAM.is_file():
        STREAM.unlink()
    acute = "é"
    comb = "e\u0301"
    run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [
                {"op": "mark", "braid": comb, "body": "nfc-leaf"},
                {"op": "light", "braid": acute},
            ],
        }
    )
    lit = [r for r in _load_stream() if ev(r, "slot") == "lit"]
    if len(lit) != 1 or lit[0].get("braid") != acute:
        raise RuntimeError("nfc braid miss " + json.dumps(lit))
    ok("braid-nfc-identity")
    if STREAM.is_file():
        STREAM.unlink()
    vm = run_program(
        decode_glyph_program(
            encode_glyph_program(
                {
                    "v": 3,
                    "lang": "lit",
                    "body": [{"op": "tick", "braid": "κ"}, {"op": "last", "braid": "κ"}],
                }
            )
        )
    )
    if not any(x.startswith(GLYPH["last"] + "1") for x in vm.out):
        raise RuntimeError("glyph kappa braid miss " + str(vm.out))
    ok("glyph-braid-kappa")
    _expect_fail(
        lambda: encode_glyph_program({"v": 3, "lang": "lit", "body": [{"op": "tick"}]}),
        "tick needs braid",
    )
    ok("glyph-tick-needs-braid")
    _expect_fail(
        lambda: run_program({"v": 3, "lang": "lit", "body": [{"op": True}]}),
        "unknown op",
    )
    ok("bool-op-fails")

    if STREAM.is_file():
        STREAM.unlink()
    mk = {
        "v": 3,
        "lang": "lit",
        "body": [
            {
                "op": "mark",
                "braid": "leafy",
                "body": "packed-who",
                "who": "joseph",
                "evd": "hear",
                "ill": "say",
                "slot": "dark",
                "asp": "open",
                "ch": "text",
            }
        ],
    }
    wire = encode_glyph_program(mk)
    back = decode_glyph_program(wire)
    run_program(back)
    row = _load_stream()[-1]
    if ev(row, "who") != "joseph" or ev(row, "evd") != "hear":
        raise RuntimeError("g on mark lost who/evd " + json.dumps(row))
    ok("glyph-mark-g-who")

    if STREAM.is_file():
        STREAM.unlink()
    pk = {
        "v": 3,
        "lang": "lit",
        "body": [
            {
                "op": "pred",
                "braid": "sky",
                "a": "blue",
                "who": "joseph",
                "ch": "sense",
            }
        ],
    }
    wire = encode_glyph_program(pk)
    if "pred" in wire or "joseph" in wire or "sense" in wire:
        raise RuntimeError("pred english leak " + wire)
    back = decode_glyph_program(wire)
    run_program(back)
    row = _load_stream()[-1]
    if ev(row, "who") != "joseph" or ev(row, "ch") != "sense" or ev(row, "evd") != "guess":
        raise RuntimeError("g on pred lost who/ch " + json.dumps(row))
    ok("glyph-pred-g-who")
    tok = encode_g(pack_g(ch="text", slot="dark", evd="hear", who="joseph", ill="say", asp="open"))
    if any(c.isdigit() for c in tok) or any(c.isascii() and c.isalpha() for c in tok):
        raise RuntimeError("feat g still latin/digit " + tok)
    if unpack_g(decode_g_token(tok))["who"] != "joseph":
        raise RuntimeError("feat g roundtrip")
    ok("feat-g-unread")
    old_g = pack_g(ch="text", slot="dark", evd="hear", who="joseph", ill="say", asp="open")
    old_wire = GLYPH_HDR + _glyph_str(str(old_g)) + _glyph_str("m") + _glyph_str("old-leaf") + GLYPH["mark"]
    if STREAM.is_file():
        STREAM.unlink()
    run_program(decode_glyph_program(old_wire))
    row = _load_stream()[-1]
    if ev(row, "who") != "joseph" or ev(row, "evd") != "hear":
        raise RuntimeError("old decimal g miss " + json.dumps(row))
    ok("old-decimal-g")
    nw = encode_glyph_program(
        {"v": 3, "lang": "lit", "body": [{"op": "next", "braid": "gw", "ch": "sense"}]}
    )
    if "sense" in nw or "text" in nw or "next" in nw:
        raise RuntimeError("next ch english leak " + nw)
    back = decode_glyph_program(nw)
    if back["body"][0].get("ch") != "sense":
        raise RuntimeError("next ch feat miss " + json.dumps(back))
    ok("next-ch-featural")

    kid = encode_glyph_program({"v": 3, "lang": "lit", "body": [{"op": "say", "a": "from-litg"}]})
    (WORK / "kid.litg").write_text(kid, encoding="utf-8")
    vm = run_program({"v": 3, "lang": "lit", "body": [{"op": "run", "a": "work/kid.litg"}]})
    if "from-litg" not in vm.out:
        raise RuntimeError("run litg miss")
    ok("run-glyph-file")
    langp = WORK / "lang.litg"
    if not langp.is_file():
        raise RuntimeError("lang.litg miss")
    w = langp.read_text(encoding="utf-8")
    if not w.startswith(GLYPH_HDR) or "run" in w or "mark" in w or "work/lib" in w:
        raise RuntimeError("lang.litg not unread " + w[:80])
    i = 0
    while True:
        a = w.find("‹", i)
        if a < 0:
            break
        b = w.find("›", a + 1)
        if b < 0:
            raise RuntimeError("lang.litg unterminated ‹")
        inner = w[a + 1 : b]
        if any(c.isascii() and c.isalpha() for c in inner):
            raise RuntimeError("lang latin payload " + inner)
        i = b + 1
    ok("lang-no-latin-payload")
    if STREAM.is_file():
        STREAM.unlink()
    run_program(
        {
            "v": 3,
            "lang": "lit",
            "body": [
                {
                    "op": "mark",
                    "braid": "泥",
                    "body": "餘",
                    "slot": "lit",
                    "evd": "see",
                    "who": "vic",
                    "ill": "do",
                    "ch": "text",
                    "asp": "open",
                }
            ],
        }
    )
    vm = run_file(langp)
    if not any(GLYPH["got"] + "脈" in x for x in vm.out):
        raise RuntimeError("lang.litg pulse miss " + str(vm.out))
    if not any(x.startswith(GLYPH["near"] + "職") for x in vm.out):
        raise RuntimeError("lang.litg nosmash miss " + str(vm.out))
    if "折可" not in vm.out:
        raise RuntimeError("lang.litg fold miss " + str(vm.out))
    if not any(GLYPH["near"] + "α n=" in x for x in vm.out) or not any(GLYPH["near"] + "β n=" in x for x in vm.out):
        raise RuntimeError("lang.litg onelit miss " + str(vm.out))
    ok("focus-lang-litg")
    rows = _load_stream()
    spine = wake_spine(rows)
    if FEAT_SLOT["lit"] not in spine:
        raise RuntimeError("wake spine missed lit " + spine)
    if "β" + FEAT_SLOT["lit"] not in spine:
        raise RuntimeError("wake spine missed onelit " + spine)
    ok("wake-spine-sees-lit")
    if "泥" + FEAT_SLOT["dark"] not in spine:
        raise RuntimeError("dirt smashed or missing " + spine)
    if "泥" + FEAT_SLOT["lit"] in spine:
        raise RuntimeError("dirt still lit " + spine)
    ok("lang-on-dirty-stream")
    fractp = WORK / "fract.litg"
    if not fractp.is_file():
        raise RuntimeError("fract.litg miss")
    fw = fractp.read_text(encoding="utf-8")
    if not fw.startswith(GLYPH_HDR):
        raise RuntimeError("fract not L3")
    i = 0
    while True:
        a = fw.find("‹", i)
        if a < 0:
            break
        b = fw.find("›", a + 1)
        if b < 0:
            raise RuntimeError("fract unterminated ‹")
        inner = fw[a + 1 : b]
        if any(c.isascii() and c.isalpha() for c in inner):
            raise RuntimeError("fract latin payload " + inner)
        i = b + 1
    if STREAM.is_file():
        STREAM.unlink()
    vm = run_file(fractp)
    if "自" not in vm.out:
        raise RuntimeError("fract self miss " + str(vm.out))
    if not any(x.startswith(GLYPH["have"] + "細 n=3") for x in vm.out):
        raise RuntimeError("fract nest miss " + str(vm.out))
    if not any(x.startswith(GLYPH["last"] + "3") for x in vm.out):
        raise RuntimeError("fract last miss " + str(vm.out))
    ok("fract-self-similar")

    print("=== LIT TEST", n_ok, "PASS ===")
    return 0


def write_schema() -> Path:
    spec = {
        "lang": "lit",
        "v": 3,
        "for": "ai",
        "not_for": "humans",
        "ops": sorted(OPS),
        "codes": OP_CODE,
        "glyphs": GLYPH,
        "glyph_hdr": GLYPH_HDR,
        "feat": {"ch": FEAT_CH, "slot": FEAT_SLOT, "evd": FEAT_EVD, "who": FEAT_WHO, "ill": FEAT_ILL, "asp": FEAT_ASP},
        "keys": {k: sorted(v) for k, v in sorted(OP_KEYS.items())},
        "ch": sorted(CH),
        "evd": sorted(EVD),
        "who": sorted(WHO),
        "ill": sorted(ILL),
        "asp": sorted(ASP),
        "need_no": sorted(NEED_NO),
        "wall": ["sandbox only", "no net", "no house", "no JoeysAI", "no eval"],
        "laws": [
            "unknown op or field fails",
            "one slot=lit",
            "pred evd=guess",
            "grok/vicky cannot seal",
            "got without pred fails",
            "light strongest evd",
            "lookup ops need a named letter-start braid",
            "no dump braid _",
            "public wire is L3; json is bootstrap only",
            "no second JSON; intern should become Lit not LitSON",
            "giants help not opcodes; braid NFC any-script; g is determinative",
            "g on the wire is six silent classifier signs, not arabic digits",
        ],
    }
    path = BOX / "LIT_SCHEMA.json"
    path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    print("schema", path.name, "ops", len(OPS))
    return path


def check_stream() -> int:
    rows = _load_stream()
    n_lit = sum(1 for r in rows if ev(r, "slot") == "lit")
    print("=== LIT CHECK ===")
    print("events", len(rows), "lit", n_lit)
    if n_lit > 1:
        print("FAIL more than one lit")
        return 1
    print("ok")
    return 0


def paint_rain(wire: str) -> Path:
    """Still of unread glyphs falling — Matrix joke, real program on the wire."""
    import random

    from PIL import Image, ImageDraw, ImageFont

    def font(sz: int):
        for p in (
            Path(r"C:\Windows\Fonts\seguisym.ttf"),
            Path(r"C:\Windows\Fonts\segoeui.ttf"),
            Path(r"C:\Windows\Fonts\arial.ttf"),
        ):
            if p.is_file():
                return ImageFont.truetype(str(p), sz)
        return ImageFont.load_default()

    signs = [c for c in wire if c in UNGLYPH]
    if not signs:
        signs = list(GLYPH.values())
    rnd = random.Random(len(wire) + 13)
    w, h = 1920, 1080
    im = Image.new("RGB", (w, h), (0, 8, 0))
    dr = ImageDraw.Draw(im)
    fnt = font(28)
    cols = 48
    cw = w // cols
    for c in range(cols):
        x = c * cw + 8
        y = rnd.randint(-200, 200)
        n = rnd.randint(8, 22)
        for k in range(n):
            ch = signs[(c * 7 + k * 3) % len(signs)]
            g = 40 + (k * 12) % 200
            if k == n - 1:
                fill = (180, 255, 180)
            else:
                fill = (0, g, 20)
            dr.text((x, (y + k * 28) % (h - 20)), ch, fill=fill, font=fnt)
    dest = WORK / "LIT_RAIN.jpg"
    WORK.mkdir(parents=True, exist_ok=True)
    im.save(dest, "JPEG", quality=80)
    return dest


def rain_print(wire: str) -> None:
    signs = [c for c in wire if c in UNGLYPH]
    if not signs:
        signs = list(wire[:24])
    cols = 16
    rows = 8
    for r in range(rows):
        line = []
        for c in range(cols):
            line.append(signs[(r * 3 + c * 5) % len(signs)])
        print("\033[32m" + "  ".join(line) + "\033[0m")


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print("usage: python sandbox/lit.py test|check|schema|json|encode|rain <program.litg>")
        return 2
    cmd = argv[0]
    if cmd == "schema":
        write_schema()
        return 0
    if cmd == "json":
        if len(argv) < 2:
            print("usage: python sandbox/lit.py json <bootstrap.json>")
            return 2
        src = Path(argv[1])
        cwd_p = src.resolve()
        box_p = (BOX / src).resolve()
        cand = cwd_p if cwd_p.is_file() else box_p
        if not cand.is_file():
            print("missing", src)
            return 2
        p = _inside(cand)
        run_program(load_json_bootstrap(p.read_text(encoding="utf-8")))
        return 0
    if cmd == "encode":
        if len(argv) < 2:
            print("usage: python sandbox/lit.py encode <in.json> [out.litg]")
            return 2
        src = Path(argv[1])
        raw = src.read_text(encoding="utf-8") if src.is_file() else (BOX / src).read_text(encoding="utf-8")
        data = load_json_bootstrap(raw) if not raw.lstrip().startswith(GLYPH_HDR) else decode_glyph_program(raw)
        dest = Path(argv[2]) if len(argv) > 2 else WORK / "encoded.litg"
        if not dest.is_absolute():
            dest = (WORK / dest.name) if dest.parent == Path(".") else dest
        dest = dest if dest.is_absolute() else (BOX / dest if str(dest).startswith("work") or dest.exists() else WORK / dest.name)
        try:
            dest = dest.resolve()
            dest.relative_to(BOX.resolve())
        except ValueError:
            dest = WORK / "encoded.litg"
        if dest.suffix != ".litg":
            dest = dest.with_suffix(".litg")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(encode_glyph_program(data), encoding="utf-8")
        print("encoded", dest)
        return 0
    if cmd == "test":
        try:
            return selftest()
        except Exception as exc:
            print("FAIL", exc)
            return 1
    if cmd == "check":
        return check_stream()
    if cmd == "rain":
        if len(argv) < 2:
            print("usage: python sandbox/lit.py rain <program.litg>")
            return 2
        p = Path(argv[1])
        cand = p.resolve() if p.is_file() else (BOX / p)
        text = cand.read_text(encoding="utf-8") if cand.is_file() else ""
        if not text.lstrip().startswith(GLYPH_HDR):
            print("LIT fail: json is bootstrap; emit L3")
            return 1
        wire = text.strip()
        rain_print(wire)
        dest = paint_rain(wire)
        board = WORK / "PINKY_BOARD.jpg"
        board.write_bytes(dest.read_bytes())
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("pinky_board", BOX / "pinky_board.py")
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                print("pinky", mod._scp(board, "PINKY_BOARD.jpg"))
        except Exception:
            pass
        vm = run_file(Path(argv[1]))
        print("rain", dest.name, "out", vm.out[:6])
        return 0
    path = Path(cmd)
    try:
        run_file(path)
        return 0
    except Exception as exc:
        print("LIT fail:", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
