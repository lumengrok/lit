# Sandbox wall — language work must not bleed into Vic

**Vic (living house)** = `../house/` + `../vic.py` + wake.  
**This folder** = where we build the machine coding language.

The wall:

- IR may **read/write only under `sandbox/`**
- IR may **not** touch `house/`, `vic.py`, JoeysAI, or anywhere else on disk
- No `import` of the old plant
- No network
- `seal` here writes `sandbox/work/SEALED.jsonl` — **not** Vic’s `house/SEALED.jsonl`
- Vic `check` does not police files inside sandbox (lab can be messy)
- Living Vic does not import sandbox
Bleed test: a program that names a path outside this repo must **fail**.
