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

- 2026-11-06 (night 2, step 3): **`for`, `break`, `continue` (D21).** `for x in xs`, `for i in a until b`,
  `for i in a through b`, each optionally `reversed`; bounds and list evaluated once, the list walked
  as a snapshot, the loop variable read-only, no overflow at the Int limits. `returns()` now knows a
  `while true` with a `break` can fall through. Targeted fixes for `range(n)`, `range(n - 1, -1, -1)`,
  `1 to n` (offers both readings), `0..n`, C-style headers, `for i, x in`, `for x in n`. 19 tests;
  SPEC ~1.8k tokens.

- 2026-11-06 (night 2, step 4): **list trial rerun with `for` in the spec**
  (`2026-11-06-1203-lists-haiku`, `-1204-lists-sonnet`): **both 11/11 first try** (was Haiku 11/11,
  Sonnet 9/11). Final programs are **18% shorter** (Haiku 242 -> 197 non-comment lines, Sonnet
  226 -> 185); the biggest drops are counting loops (fib-list 27 -> 12, join 16 -> 11). Each
  model wrote 11 `for` loops (`until` 5, `reversed` 1; `through` and `break` unused) and kept 5-6
  `while`s, all of them while-shaped: a sieve stepping by `p`, the two-pointer merge, the
  insertion-sort shift. A step option would have saved only the sieve, so "use `while` for other
  steps" stays. **Nobody wrote `range(`, `to` or `..`**, so those diagnostics remain a safety net.
  Sonnet named the arguments in every `example` line this time, including the `contains`/`join`
  calls it missed before, so the SPEC sentence added in step 2 worked.

- 2026-11-06 (night 2, step 5): **structs (D22).** `struct Point` / `x: Int` lines /
  `end struct Point`; `Point(x: 1, y: 2)` with D4's naming rule; `p.x`, `p.x = v` one level deep;
  values with copy-on-write (a struct is a `cl_list` with one slot per field, descriptor `R<n>`
  into a `cl_recs` table); `==` and `print` (`Point(x: 1, y: 2)`). Fields can be structs and lists,
  and a type may name a struct declared later (the parser pre-scans struct names); `x: Node` inside
  `Node` is `recursive-struct` with the `List[Node]` fix. Habit fixes: `class`/`record`/`type`,
  `var` on a field, trailing `,`, `Point(1, 2)`, `Point { x: 1 }`, `new`, missing fields (named,
  with the given values filled in), `xs.length`, `a.b.c = v` / `ps[i].x = v` / `p.items[0] = v`.
  A line that is only `}` now closes the innermost block with `closer-kind` (helps every block, not
  just structs). 21 tests; SPEC ~2.1k tokens.

- 2026-11-06 (night 2, step 6): **struct trial** (`--set structs`, 11 tasks baiting methods,
  positional construction, nested updates, mutation through a parameter, aliasing;
  `2026-11-06-1500-structs-haiku`, `-1502-structs-sonnet`): **both 10/11 first try, 11/11 after one
  fix**, and the miss is the same task for both: `scores`, where both wrote
  `ps[i].score = ps[i].score + 5` (Haiku three times, Sonnet inside a loop), although SPEC names
  that exact case as not allowed. All four errors across both runs are `nested-assign`. Both
  recovered from the fix in one round. Everything else held: `segment` copied SPEC's worked example
  (`var s = seg.start` / `s.x = 0` / `seg.start = s`) nearly verbatim on the first try; `bank`
  returned a new account rather than mutating its parameter; `rect` used plain functions, no
  methods; `copy`, `tree`, `book` (print format) and `by-age` passed. So a full worked example is
  followed, a parenthetical "the same for `ps[i].x`" isn't, and the habit is strongest exactly
  where structs are most used (a list of records). The fix text also has two flaws: it leaves
  `ps[i]` in the right-hand side (`item.score = ps[i].score + 5`), and applied literally three
  times it would declare `var item` three times, which no-shadowing rejects.

- 2026-11-07 (night 3, step 1): **general assignment paths (D23).** `ps[i].score = v`,
  `grid[i][j] = v`, `a.b.c = v`, `p.items[0] = v`: the checker types the target as an ordinary
  expression and needs only the root to be a `var`; codegen computes the value, then the indexes,
  then walks with `cl_list_at` / `cl_rec_at` (each makes its level unique and returns the next
  slot's address) and stores with `cl_list_set` / `cl_rec_set`. `x.path = append(list: x.path, ...)`
  is an in-place push when the path's indexes are names or literals. `nested-assign` is gone;
  `for p in ps` / `p.x = v` is now `assign-to-loop-var` saying `p` is a copy, with the index-loop
  fix. `append(p.items, 4)` alone gets the path fix too. SPEC lost its two "one level at a time"
  lines (~20 words shorter). New test `tests/ok/paths.cl` (copies at every level stay unchanged,
  value-before-walk so no cycles, 100k appends through a path in ~0.1 s); 22 tests. Also fixed
  `build -o NAME` without a slash (examples were run via PATH lookup and failed).
  **Trial rerun** (`2026-11-07-1006-*`): structs `scores` + `segment` and lists `grid`, Haiku and
  Sonnet: **6/6 first try** (the struct trial had both models failing `scores`). Both wrote
  `ps[1].score = ps[1].score + 5` and `s.start.x = 0` directly, so `segment` went from SPEC's
  three-line copy-change-store to one line.

- 2026-11-07 (night 3, step 2): **bigger-program trial** (`--set big`, 4 tasks with exact output:
  `league` standings with three tie-break levels, `orders` with stock and per-customer totals, `life`
  on an 8x10 grid with dead edges, `adventure` with rooms, exits, a locked door and items;
  `2026-11-07-1102-big-haiku`, `-1104-big-sonnet`). **Both 4/4 first try**, 48-130 lines per program
  (`trial.py` now logs non-comment line counts). Findings:
  - **D23 paid off at once:** 31 lines across the 8 programs assign through a deep path
    (`items[ii].stock = items[ii].stock - o.qty`, `ts[h].points = ...`, `nxt[r][c] = ...`,
    `t.rooms[t.room] = rest`, `r.items[i].place = "player"`). Before D23 each was a compile error.
  - **Every program invents a "not found" sentinel:** `-1` from 6 hand-written find/index_of
    functions, `""` from Haiku's exit lookup, `-1` from Sonnet's. It works (a missed check traps
    at `xs[-1]` with a clear message), but it's the C idiom, and it's the clearest pressure yet for
    an optional value (D7's `Result`, or an `Option`) with `match`.
  - **Hand-written helpers:** string join with a separator 4 times (a `first` flag or
    `if line == ""`), list `contains` twice. Candidates for a small built-in set
    (`join(list:, with:)`, `contains(list:, item:)`), weighed against SPEC tokens.
  - **State threading** is how both modelled mutable game state: `w = goTo(w: w, dir: "east")`, the
    function returning an updated copy. Natural with value semantics; no one tried to mutate a parameter.
  - Sonnet hand-translated the league's team names to indexes (`let home = [0, 2, 4, ...]`): correct,
    but brittle. Haiku looked names up.
  - Two programs declared a typed empty variable just to pass `[]` to a constructor, because SPEC
    said "an empty list needs its type written". `[]` already works wherever the type is known, so
    SPEC now says so.

- 2026-11-07 (night 3, step 3): **designed D24** (DESIGN.md): `enum` with payload variants, built-in
  `Option[T]` (`Some`/`None`) and `Result[T, E]` (`Ok`/`Err`), and a `match` statement
  (`case` arms, `end match`, exhaustive, `case _`). Key choices: unqualified variant names; D4
  rules for construction; bindings positional only for one-field variants, by field name
  otherwise (no swapped fields); no implicit wrapping (`return i` -> fix `return Some(i)`); C
  `if` chains so `break` in an arm can't hit a `switch`; values are `cl_list`s with a tag in
  item 0. One-line unpack forms, `match` expressions, `?` and literal patterns wait for trial data.

- 2026-11-07 (night 3, step 4): **built D24 part (a): enums and `match`.** `enum Name` / variant
  lines / `end enum Name` (the struct parser, generalized); `match x` / `case` arms / `end match`;
  keywords `enum`, `match`, `case`. Checker: global variant names, D4 construction (reuses
  `construct`), bare `Look` as a value, exhaustiveness with the missing `case` lines as the fix,
  `unreachable-case` (duplicate or after `case _`), `unknown-variant`, bindings (positional for one
  field, by field name otherwise, `field: name` to rename, `unnamed-bind` for `case Move(a, b)`),
  `returns()`/`breaks()` see through arms, `else`/stray `case`/`Command.Look` habits. Runtime: an
  enum is a `cl_list` with the tag in item 0, descriptor `E<n>` into `cl_enums`; `==`, `print`,
  failing-example output all work. Recursive enums work (`Expr`). New tests `ok/enums.cl`,
  `err/enums.cl`; 24 tests. SPEC has an "Enums and match" section (~1.8k words now, ~2.4k tokens).

- 2026-11-07 (night 3, step 5): **built D24 part (b): `Option[T]` and `Result[T, E]`.** Types parse
  (with fixes for `Optional`, `Maybe`, `Either`, `<...>`); `Some`/`Ok`/`Err` and bare `None` are typed
  from `want` (`needs-type` without it); `match` over them via `variants_of()`, which now drives
  enums too. `wrap_fix()` adds the fix to every type-mismatch site: Option-as-T gets the `match`
  lines, T-as-Option gets `Some(...)` (`return Some(i)` at a return). Habit errors for `null`,
  `if let`, `.unwrap()`, `?`, `=>`, `switch` (recovers as `match`), `default:`, `is None`.
  New tests `ok/options.cl` (find, a digit parser returning Result, a running max in an Option,
  lists of Options, `Some(None)`), `err/options.cl`; 26 tests. SPEC ~1.95k words (~2.6k tokens).
  Known cascade: an `if let` line leaves its body's bound name undefined.

## Next step
1. **Finish D24 (c):** rerun `--set big` (both models) and compare with
   `2026-11-07-1102`/`-1104`: how many sentinels remain, whether find functions return
   `Option`, how many lines each unpack costs, and any new mistakes.
2. Maybe `join` / `contains` built-ins. Then a wrong-but-compiles trial, holes (D9), the
   formatter (D12). Parsing (`parse_int(s) -> Result`) needs D7's Result; enums/`match` with it.

Known gaps: no list concatenation; no string iteration or indexing; nothing is freed; the `.cl`
extension clashes with OpenCL, so the name is still provisional.

## Repo
Public: https://github.com/Ari-Zerner/claude-lang (Ari, 2026-11-05). Push after each commit.

## How to build/test
`python3 tests/run.py`; under the box's memory cap:
`systemd-run --scope -q -p MemoryMax=400M -- python3 tests/run.py`.
