# claude-lang

A small programming language designed to be good for **Claude** to write, read and fix, rather
than for human developers. It's a for-fun project, built by Claude Code sessions in spare time.

- [IDEA.md](IDEA.md): the brief
- [DESIGN.md](DESIGN.md): what's different about writing code as an LLM, and the decisions
  that follow from it
- [NOTES.md](NOTES.md): current state and next step

```
fn gcd(a: Int, b: Int) -> Int
  example gcd(a: 12, b: 18) == 6
  if b == 0
    return a
  end if
  return gcd(a: b, b: a % b)
end fn gcd

fn main() uses io
  print(gcd(a: 48, b: 36))
end fn main
```

```
python3 clc.py run examples/gcd.cl      # compile (via Lean 4) and run; the examples run as tests
python3 clc.py test FILE                 # just the examples (~2 s)
python3 clc.py check FILE [--json]       # diagnostics only
python3 clc.py run --backend c FILE      # the older C backend: builds in ~0.2 s, but Int is 64-bit there
python3 tests/run.py [--backend c]       # the compiler's own tests
```

Needs Python 3 and Lean 4 (`lean` on PATH, with its bundled `leanc`); the C backend needs gcc. Lean is the
default since 2026-11-09 (DESIGN.md D26), so the program that runs is the one contracts will be proved about.
