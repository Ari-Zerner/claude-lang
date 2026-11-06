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
- 2026-11-05 (night 1, step 6): decided bigger-program trials are premature, since without strings
  or data structures a 100-line program mostly measures what's missing. Added **strings (D18)**:
  `String`, double-quoted literals with escapes, `{expr}` interpolation, which also replaces
  concatenation (no string `+`), `==`/`!=`, and `print` of strings. Examples that compare strings
  report both values. Hints for `'single quotes'`, `str`, `"a" + b`, nested strings and bad
  escapes. Strings are never freed yet. SPEC.md is now ~1.4k tokens; 13 tests. The table trial
  task now has an exact answer, and Haiku and Sonnet both got it on the first try.

- 2026-11-06 (night 2, step 1): **lists (D19)**. `List[T]` (nests), `[...]` literals, `xs[i]`
  (0-based, bounds-checked with the length and last index in the message), `length` (lists and
  strings, in characters), `append(list:, item:)` returning a new list, `repeat(item:, times:)`,
  `xs[i] = v` on a `var`, `==`, and `print`/interpolation showing `[1, "a"]`-style values. Value
  semantics via copy-on-write with a share count (never freed yet); `xs = append(list: xs, ...)`
  compiles to an in-place push, so 1M appends + 1M sets take 0.27 s. Failing list examples show
  both lists. Targeted errors for the habits: `xs.append(4)`, `append(xs, 4)` alone on a line,
  `len`, `xs[-1]`, `[0] * n`, `xs + [4]`, `list[int]`/`Vec<Int>`/`Int[]`, `grid[i][j] = v`,
  `1.5`. Also D20: a line with a lexical error reports only that error. 17 tests.
  SPEC.md ~1.7k tokens.

- 2026-11-06 (night 2, step 2): **list trial** (`--set lists`, 11 tasks, several baiting other
  languages' habits: last item, joining lists, a nested change, mutating a copy). Two harness
  fixes first: the prompt now says to print bare output (5 "failures" were correct programs that
  printed labels), and `extract()` takes the block with `fn main` (Sonnet's first reply had a stub
  block ahead of the real one). Clean result: **Haiku 11/11 first try; Sonnet 9/11 first try,
  11/11 after one fix.** Findings:
  - **No habit leaked.** Nobody wrote a method, list `+`, `xs[-1]` or `grid[i][j] = v`: last items
    were `xs[length(xs) - 1]`, the grid change was done one level at a time, `doubled` copied with
    `var ys = xs` before changing it, and join was an append loop. The spec's Lists section works
    as written, so the habit diagnostics are a safety net that hasn't been needed yet.
  - **Sonnet's two misses were unnamed two-argument calls** (`contains([1, 2, 3], 2)`,
    `join([1, 2], [3, 4, 5])`), fixed in one round from the `fix:` line. In `dedupe` it named the
    arguments in the body but not in the `example` lines, so examples seem to read as test notation.
    SPEC now says examples name arguments like any other call. D4 stays: the cost is one round.
  - **The cost is loop boilerplate.** Every list loop is `var i = 0` / `while i < length(xs)` /
    `i = i + 1`, and "is x in the list" uses a `seen` flag or an early `return` from a helper,
    since there's no `break`. Nobody forgot the increment, but it's the most repeated pattern by far.

## Next step
1. **`for` and `break`.** Proposal to settle in DESIGN first: `for x in xs ... end for` over items;
   `for i in 0 until n` (exclusive) and `for i in 1 through n` (inclusive), never a bare `to`, whose
   inclusiveness differs between languages; `break` and maybe `continue`. Then rerun the list trial
   and compare line counts.
3. Records (structs), then bigger-program trials, a wrong-but-compiles trial, holes (D9), the
   formatter (D12). Parsing (`parse_int(s) -> Result`) needs D7's Result.

Known gaps: no `break`/`for`; no list concatenation; nothing is freed; the `.cl` extension
clashes with OpenCL, so the name is still provisional.

## Repo
Public: https://github.com/Ari-Zerner/claude-lang (Ari, 2026-11-05). Push after each commit.

## How to build/test
`python3 tests/run.py`; under the box's memory cap:
`systemd-run --scope -q -p MemoryMax=400M -- python3 tests/run.py`.
