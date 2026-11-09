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
python3 clc.py run examples/gcd.cl      # compile (via C and gcc) and run; the examples run as tests
python3 clc.py check FILE [--json]       # diagnostics only
python3 tests/run.py                     # the compiler's own tests
python3 clc.py run --backend lean FILE   # the coming Lean 4 backend (DESIGN.md D26; no lists/structs yet)
python3 tests/run.py --backend lean      # the tests through Lean, skipping what it can't emit yet
```

Needs Python 3 and gcc; the Lean backend needs Lean 4 (`lean` on PATH, with its bundled `leanc`).
