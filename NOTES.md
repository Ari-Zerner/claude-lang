# Working notes: state and next step

Read this first when picking the project up cold. IDEA.md is the brief; DESIGN.md has the
design and its decisions (D1...).

## Log
- 2026-11-05 (night 1, step 1): wrote DESIGN.md with design principles, decisions D1-D12 and
  open questions. No code yet.
- 2026-11-05 (night 1, step 2): first working compiler, `clc.py` (~1000 lines, Python -> C ->
  gcc). It covers Int/Bool, `let`/`var`, assignment, `if`/`else if`/`else`, `while`, `return`,
  `print`, calls with named arguments, `uses io` effect checking, examples run on every build
  (D8), named closers with recovery (D2), D6 precedence errors, word error codes (D14),
  other-language hints (D15), checked overflow and division (D16), and `--json` diagnostics.
  `tests/run.py`: 8 tests (2 running programs, 6 error files), all passing. Builds take ~0.15 s.
  Added DESIGN D13-D17 and a README.

## Next step
Candidates, roughly in order:
1. Write `SPEC.md` (D11) now, while the language is small: the whole language in under ~4k
   tokens, written to be pasted into a prompt. Then test it: give a fresh `claude -p` only
   SPEC.md and a small task, and see what it gets wrong. Those mistakes are the best design
   input there is (cheap: one headless run, Sonnet is fine).
2. Holes (D9).
3. Strings, then lists (decide memory management first: see the open question).
4. A formatter (D12).

Known gaps: no `break`; `%` follows C (the sign of the result follows the dividend), which isn't
written down yet; the `.cl` extension clashes with OpenCL, so the name is still provisional.

## Repo
Public: https://github.com/Ari-Zerner/claude-lang (Ari, 2026-11-05). Push after each commit.

## How to build/test
`python3 tests/run.py`; under the box's memory cap:
`systemd-run --scope -q -p MemoryMax=400M -- python3 tests/run.py`.
