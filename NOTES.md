# Working notes: state and next step

Read this first when picking the project up cold. IDEA.md is the brief; DESIGN.md has the
design and its decisions (D1...).

## Log
- 2026-11-05 (night 1, step 1): wrote DESIGN.md with design principles, decisions D1-D12 and
  open questions. No code yet.

## Next step
Write the smallest end-to-end compiler (`clc.py`): lexer, parser and C emitter for Int-only
functions, `if`/`end if`, `return`, `print`, calls with named arguments, plus the
named-closer check (D2) and diagnostics in the D10 format. Goal: `gcd` from DESIGN.md compiles and
runs. Then examples-as-tests (D8).

## Repo
Public: https://github.com/Ari-Zerner/claude-lang (Ari, 2026-11-05). Push after each commit.

## How to build/test (once there is code)
Run under a memory cap: `systemd-run --scope -q -p MemoryMax=400M -- python3 clc.py ...`.
