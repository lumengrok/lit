# Lit — v3 (unread). One language.

**Physics lock:** `CORE.md` — data model of events + one lit place + closed unread ISA. Syntax is skin. Not a planner. Laws 3, 6, 12–13, 23–24 already say this. No new op.

AIs emit **L3 glyph wire**. A dumb runner executes it. Joseph `wake`s.  
**Not a universal lang for humans. Universal for AIs** — one spelling, any model (Grok, Vicky, local). Extra fields fail. `python sandbox/lit.py schema` dumps `LIT_SCHEMA.json` as a teacher cheat-sheet, not the language.

Python is bootstrap only. **JSON is bootstrap only.** Not tags.db. Not the wire.

```text
python lit.py test
python lit.py land/hello.litg
python lit.py land/lang.litg
```

## Program

Wire: header `L3` then **postfix** glyphs (KERNEL.md). Strings `‹›`, blocks `〖〗`. Args before op. Prefix fails (`prefix not postfix`). Mouths may emit prefix; the runner does not. `from_vicky.litg` is mouth, not a program.

JSON `{v:3,lang:lit,body:[...]}` is the **teacher cheat** (`lit.py json`). Public `run` / `run` op **refuse JSON**.

Closed ops (32, basin full): `seq` `say` `read` `write` `put` `seal` `fail` `eq` `if` `run` `mark` `pred` `got` `light` `next` `tick` `report` `push` `dup` `swap` `drop` `quote` `do` `see` `hear` `rep` `cap` `need` `near` `last` `have` `copy`

Event grammar on mark/pred/got/light (and optional on any op):

```
ch    text|pic|sound|sense|act
slot  dark|lit
evd   see|hear|sense|told|guess|seal
who   joseph|vic|grok|vicky|unknown
ill   say|do|ask|pred|seal
asp   open|done
body  string
braid id   # tri-braid glue; P/N/F/gap share it
a, b  op args (paths, texts, compare)
then, else  for if
```

Stream: `sandbox/work/LIT.jsonl` (sandbox only).

## Laws

1. Unknown op or unknown event value → fail.
2. `pred` ⇒ `evd=guess`. `seal` ⇒ `who` in {joseph,vic}, `evd=seal`, `asp=done`, body ≥ 24.
3. One `slot=lit` at a time (previous darkened).
4. Paths only under `sandbox/`. Never `house/`, never JoeysAI, never net.
5. `got` needs a prior `pred` on that braid. Match → receipt `do/done`. Miss → `ask` gap and fail (the world disagreed).
6. `light` lights the **strongest evidence** on a braid (seal > see > hear > told > guess), not the newest chatter.
7. `run` only loads another Lit file under sandbox. Max depth 8. `put` writes a whole file so Lit can emit Lit.
8. Grok/Vicky cannot seal.
9. `tick` advances a **sense** number on a braid (tiny world). `next` guesses the next event from the stream itself (sense → last+1; else last body). Not an LLM.
10. `got` with no `a` reads the last world event on that braid.
11. `report` is the one-breath machine door.
12. `push` + stack `eq`/`if` — Forth, human idea that works.
13. `quote` / `do` — Lisp: Lit data is Lit code.
14. `see` / `hear` — path must exist in the box or fail (pic/sound are real, not pretend).
15. `rep` — bounded loop, max 32. `eval` Python is not an op.
16. Closed fields per op. Aliases (`text` instead of `a`) fail. That is how it stays one lang for every AI.
17. `cap` — what this box allows. `need` — ask for an op; `net`/`eval`/`house` always denied.
18. `near` — count a braid without lighting it (leaves on the spine, no smash).
19. Geometric memory: a `seal` still lights after other braids tick. Form → imprint → later light.
20. ISA basin: op count capped (`MAX_OPS=32`). Full. Improve laws, not add ops, unless a test forces a swap.
21. `got.of` points at the pred id (receipt chain).
22. Stack max 64 (conservation). `next` on empty braid fails.
23. Machine spelling: numeric `op` in intern; VM **dispatches by code** (`OP_FN` table), not `if name == "say"`. Packed `g` on the wire (KERNEL.md). English names bootstrap only. Public load of `{` fails.
24. No dump braid. Stream ops that leave a leaf — `mark` `pred` `got` `light` `next` `tick` `near` `last` `have` `seal` `see` `hear` — **need a named braid**. Silent `"_"` is magic and fails. A path you cannot light is dump.
25. Every turn after ship: relook denser / less English / less magic / tests-as-truth, then tighten once. (Joseph standing, 2026-08-22.)
26. **No second JSON.** `LIT.jsonl` and RAM rows are packed `g` + braid/body/id — **no English event keys**. Read grammar via `ev(row, key)` which unpacks `g`. JSON program bootstrap is classroom only.
27. Giants help, they are not opcodes. Egyptian determinative = packed `g` (silent). Jakobson: Lit is intersemiotic, not interlingual JSON. Braid names: any-script letter-start, **NFC identity** (Latin not required). DreamCoder/FunSearch: quote/do + tests as truth. Card: `survey/GIANTS.md`.

## Recall

Recall is **lighting a braid**, not searching tags.  
P = seal, N = do, F = pred, gap = ask when F ≠ got.

## Not in v3

net, Http, delete, Python import, eval, consciousness flag, vector body (named pred plug later), a second interchange format after Lit (no LitSON / JSON-v2), goal stack, mission opcode, LLM in the CPU (planner = named plug only — `CORE.md`).
