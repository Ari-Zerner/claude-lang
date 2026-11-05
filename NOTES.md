# Working notes: state and next step

Read this first when picking the project up cold. IDEA.md is the brief; DESIGN.md has the
design and its decisions (D1...).

## Log
- 2026-11-05 (night 1, step 1): wrote DESIGN.md with design principles, decisions D1-D12 and
  open questions. No code yet.
- 2026-11-05 (night 1, step 2): first working compiler, `clc.py` (~1300 lines, Python -> C ->
  gcc). It covers Int/Bool, `let`/`var`, assignment, `if`/`else if`/`else`, `while`, `return`,
  `print`, calls with named arguments, `uses io` effect checking, examples run on every build
  (D8), named closers with recovery (D2), D6 precedence errors, word error codes (D14),
  other-language hints (D15), checked overflow and division (D16), and `--json` diagnostics.
  `tests/run.py`: 8 tests (2 running programs, 6 error files), all passing. Builds take ~0.15 s.
  Added DESIGN D13-D17 and a README.
- 2026-11-05 (night 1, step 3): wrote SPEC.md (~1.2k tokens, well under D11's 4k budget; every
  complete program in it is now a test). Built `trials/trial.py`: it gives a fresh headless
  `claude -p` (no tools) only SPEC.md and a task, compiles the answer, and on failure hands back
  the diagnostics for one fix. First run (Sonnet, 6 small numeric tasks): **6/6 compiled and
  printed the right answer on the first try**, and Sonnet wrote `example` lines in nearly every
  function unprompted (26 lines across 6 programs). Results in `trials/results/`. That's
  encouraging, but the tasks were too easy to find weaknesses, and the fix path never ran.
- 2026-11-05 (night 1, step 4): harder trial set (`--set hard`: early exit with no `break`,
  mutual recursion, a 3-parameter function, a printing helper, coin change with no lists, a table
  that can't be printed on one line). **Sonnet and Haiku both got all 7 checkable tasks right on
  the first try**, so across three runs it's 20/20, with zero compile errors. Observations:
  - Missing `break`: both used a `found` flag in the loop condition. It works, but it's verbose.
  - Missing strings: Sonnet noticed the table can't go on one line, said so in a comment and
    printed one number per line. Neither invented string syntax, so the spec's line "if it isn't
    described here, it doesn't exist" works.
  - Missing lists: Haiku did coin change with four nested loops.
  - Models name single arguments too (`divisors(t: triangular(n: n))`), which the spec allows.
- 2026-11-05 (night 1, step 5): fix-loop trial (`trials/fixloop.py`): 11 typical mistakes planted
  in correct programs (swapped or unnamed arguments, a lost `end if`, `&&`, shadowing,
  `not (n % i)`, a missing `uses io`, `let` for a variable, `elif`, an off-by-one caught by an
  example, a missing return type). **Haiku and Sonnet fixed all 11 in one go, with either the full
  diagnostics or only their first lines (44/44).** So for mistakes this local, the message line
  alone is enough; the source line and `fix:` didn't make a measurable difference.
  The lost-`end if` case was a trap: the compiler's `fix:` said to put `end if` above `end while`,
  which would have looped forever. Both models ignored it and used the indentation. The compiler
  now does the same: a missing closer's fix points at the first line that goes back to the
  opener's indentation ("add `end if` above line 11 (`i = i + 1`)"). Indentation is still not
  significant; it's just evidence for the hint. `elif` now gets a concrete fix line too.
  `tests/run.py` supports `# fix-mentions:` lines; 10 tests.

## Next step
The trials keep coming back perfect, so small programs aren't where the hard part is. Next:
1. **Bigger programs** (~100+ lines, several interacting functions, written over more than one
   step), where locality (D2, D4, D17) should matter more, and the error rate is high enough to
   learn from. Also, a *wrong-but-compiles* trial: does a model given a program with a subtle
   logic bug and a failing `example` find it?
2. Language: strings and printing without a newline are the most-felt gap (the table task);
   `break` second. Probably strings first, which forces the memory-management decision.
3. Holes (D9) and the formatter (D12).

Known gaps: no `break`; the `.cl` extension clashes with OpenCL, so the name is still provisional.

## Repo
Public: https://github.com/Ari-Zerner/claude-lang (Ari, 2026-11-05). Push after each commit.

## How to build/test
`python3 tests/run.py`; under the box's memory cap:
`systemd-run --scope -q -p MemoryMax=400M -- python3 tests/run.py`.
