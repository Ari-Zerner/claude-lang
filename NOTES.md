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

- 2026-11-07 (night 3, wrap-up): parked D24 (c), the big-trial rerun, for next night; the window
  ended before it. Night 3 in all: D23 (assignment through any path) and the trial rerun that it
  fixed, the `--set big` trial, D24 designed and parts (a) and (b) built. 26 tests pass.

- 2026-11-08 (night 4, step 1): **D24 (c), the big-trial rerun** (`2026-11-08-1001-big-haiku`,
  `-1002-big-sonnet`): **both 4/4 first try**, no compile errors at all. Against `2026-11-07`:
  - **Sentinels: 6 functions -> 2; `Option` finds: 0 -> 4** (Haiku's `find_item`, `find_spend`,
    `exit_to`; Sonnet's `move -> Option[Room]`). The two left: Haiku's league `indexOf` looks up
    names that are always there (an `Option` would force a dead `case None`, and `-1` still traps if
    wrong), and Sonnet's orders `indexOf` serves as both must-find and maybe-find via `if ni < 0`.
  - **Unpack cost:** 1-2 lines more than `if ni < 0 / else / end if`; no unpacking mistakes.
    So the one-line forms (`if let`, `value_or`) aren't wanted yet.
  - **New pressure, `match` to a value:** Sonnet's adventure (3 enums: Room, Dir, Cmd) has four
    functions shaped `var s = ""` / `match r` / `case Hall` / `s = "Hall"` ... / `return s`
    (`roomName`, `dirName`, `itemsOf`, `setItems`; ~54 lines), though SPEC's own example returns
    from each arm. `roomName` was also unneeded, since `print(Hall)` already prints `Hall`.
    Haiku's adventure used Ints for rooms and one `Command` enum, and wrote none of these.
  - **Missing map type:** Sonnet's `World` has one field per room (`hall`, `library`, ...) plus
    `itemsOf`/`setItems` to pick one by enum; Haiku used `List[List[String]]` indexed by room Int.
    Adventure grew 123 -> 192 lines for Sonnet. Pressure for `Map[K, V]` or enum-indexed lists.
  - **Fragile-but-correct:** Sonnet's league again hand-translated team names to indexes, and
    sorted on a packed key, `pts * 10000 + (gd + 100) * 100 + gf`: right here, wrong once a team
    scores 100 goals. That's the "right on the given input, wrong on others" bug the
    wrong-but-runs trial should look for, and the kind of thing a contract would catch.
  - Line counts swing more between runs than between language versions (Haiku orders 51 -> 70
    because it added structs; Sonnet's 62 -> 52 with parallel lists), so per-feature line savings
    need the same program written twice, not two fresh runs.

- 2026-11-08 (night 4, step 2): **hidden-input trial, claude-lang vs Python** (`trials/hidden.py`;
  `2026-11-08-1104-hidden-cl-haiku`, `-1106-hidden-py-haiku`). 12 function tasks (rotate with
  negative/large k, second largest as `Option`, a grid spread with edge neighbours, window sums,
  merging ranges, lower bound, digit sum of negatives, run lengths, days until warmer, bracket
  balance, max subarray with all-negative inputs, median rounding toward negative infinity), each
  with one shown example, one fix round on it in either language, then 6-10 hidden inputs graded
  ok / wrong (silent) / error (stopped). `--selftest` checks every expected value round-trips
  through the real compiler. **Haiku: 94/94 hidden inputs right in both languages**, 0 wrong,
  0 errors. Ari's prediction holds: on familiar problems with clear specs there are no wrong
  answers for claude-lang to stop, so this task set can't separate the languages either.
  - **Cost:** claude-lang functions are ~2.7x longer (275 non-example lines vs Python's 102):
    no built-in sort (Haiku wrote insertion sort twice), no slicing, `sum`, `max` or `abs`.
  - **Examples:** Haiku wrote 78 `example` lines unprompted, many on exactly the hidden edge cases
    (`median(xs: [-1, -2]) == -2`). The Python prompt said "no tests" (so nothing runs on import),
    which is a bias: a fairer Python arm would allow doctests and run them.
  - **A real trap, interpolation by default (D18):** `balanced` wrote `"{"` five times; in
    claude-lang that starts an interpolation. Fixed in one round from the diagnostic, but each such
    line got two errors and the first is wrong (`unclosed-string`: "no closing `\"`", though there
    is one); only the second (`unclosed-interpolation`, "write `\{`") is right. Python's f-strings
    are opt-in, so this trap is ours alone.
  - Haiku got floor rounding right in claude-lang without `//` (sign-adjusted halves, overflow-safe
    too), with examples on the negative cases.

- 2026-11-08 (night 4, step 3): **the `"{"` trap, fixed in the language (D25).** First the
  diagnostic: an unclosed `{` now gets one error at the brace with the escaped string as the fix
  (`"\{x"`), not also a false "no closing quote", and the lexer keeps going, so `c == "{" or c == "}"`
  no longer reads as a nested string. A SPEC sentence ("a literal brace is always escaped") didn't
  help: a Haiku rerun of `balanced` (`2026-11-08-1202-hidden-cl-haiku`) wrote `"{"` again, five
  times. So D25: a `{` right before the closing quote is a literal brace (it can't start an
  interpolation; nothing follows it), and the SPEC sentence is gone. Rerun
  (`-1204-hidden-cl-haiku`): first try, 9/9 hidden. New test `err/braces.cl`, D25 cases in
  `ok/strings.cl`; 27 tests.

- 2026-11-08 (night 4, step 4): **rule-dense hidden-input trial** (`--set rules`: parking fee with a
  grace period and a daily cap, adding days across leap years, tax brackets rounded per part,
  ranking with two tie rules, a darts bust rule, an elevator sweep, an instant-runoff count with
  tie-breaking, greedy change from a limited supply; 77 hidden inputs, mostly on rule boundaries).
  Python may now write doctests, which run before the shown example like a build step (failures go
  back for the one fix). `2026-11-08-1303-hidden-rules-cl-haiku`, `-1306-hidden-rules-py-haiku`:
  **Haiku 77/77 in both languages again.** Findings:
  - **Every fix round (3, across both languages) was a wrong test, not wrong code:** a claude-lang
    `example` claiming 146097 days before 1-1-1 is 1-1-1; Python doctests expecting candidate 0 where
    2 holds the only counting ballot, and `[1, 1, 0, 0]` (35) as change for 40. Each time the model
    fixed the test and kept the right code. The model's own wrong expectation is a real cost of
    self-checks, and the risk is a model "fixing" right code to match a wrong test.
  - **With doctests allowed, Python wrote as many checks as claude-lang** (85 doctests vs 93
    examples). So the step-2 gap in examples was the prompt, not the language.
  - **Conclusion so far:** single functions of up to ~90 lines with clear rules give Haiku no bugs to
    catch in either language, so claude-lang's run-time traps, exhaustive `match` and value semantics
    have nothing to stop at this scale. If they pay, it's at a scale or in a kind of work these trials
    don't reach. The best candidate is **changing an existing program** (add an enum variant, a rule,
    a field): exhaustive `match` points at every place a new variant must be handled, where a Python
    `if`/`elif` chain falls through silently, and the hidden inputs become regression tests.

- 2026-11-08 (night 4, step 5): **Lean-direct baseline** (`trials/leanbase.py`; Ari's "is this buying
  Claude anything over just writing in Lean directly?"). Six tasks: write a Lean 4 core function and
  prove fixed theorem statements (sum formula; isqrt's two bounds; list max is >= every item and is
  one of them; insertion sort is sorted and a permutation; tax and parking fee are monotone, fee
  bounded). The harness restates each theorem (a weakened statement fails), rejects `sorry`/axioms/
  `native_decide` via `#print axioms`, and pins behaviour with hidden `#eval`s; two fix rounds.
  - **No hints** (`2026-11-08-1403-leanbase-haiku`, `-1407-...-sonnet`): **Haiku 5/6 (4 first try),
    Sonnet 5/6 (4 first try).** Proofs are real: isqrt via a search function and three lemmas,
    insertion sort sorted + `Perm`, tax monotone by `unfold tax; omega`. Each failure was a
    **Mathlib name in core Lean**, repeated through both fix rounds: Haiku's `split_ifs` (core has
    `split`; Lean says only "unknown tactic", not which or what to use), Sonnet's
    `Nat.strong_induction_on` ("Unknown constant").
  - **With a 6-line "core is not Mathlib" note** (`--hints`; `-1411-leanbase-hints-haiku`,
    `-1416-...-sonnet`, isqrt only): **Haiku 6/6 (3 first try), Sonnet's isqrt first try.** Every
    task proved by both models. Haiku's tax took 2 fixes this time on "maximum recursion depth has
    been reached", which doesn't say what recursed.
  - Lean's quiet defaults helped here: Haiku's tax is 4 lines because `Nat` subtraction stops at 0
    (`min income 40000 - 10000` is 0 below 10000, `- 500` never goes negative). The hidden evals
    confirm it's right.
  - Lean took 1.5-10 s per check (23 s once, cold, under memory pressure).
  - **What it means for claude-lang:** for small functions, proved Lean is within reach of both
    models today, and the main obstacle is a name table that fits in a paragraph. So "Claude can't
    write proofs" isn't a gap claude-lang needs to fill at this scale. What's left for it: the error
    quality (a named fix where Lean says "unknown tactic"), one small spec instead of Lean's churning
    library, and contracts that automation closes without a written proof (`omega` closed tax in one
    line). A thought for Ari: compile claude-lang to Lean rather than C, so the program that runs is
    the one that's proved.

- 2026-11-08 (night 4, step 6): **hard Lean tasks, where Lean-direct might break** (`--set hard
  --hints`; `2026-11-08-1501-leanbase-hard-hints-haiku`, `-1506-...-sonnet`): a `for` loop with
  `let mut` proved equal to a `map`/`sum` spec, binary search's lower-bound property on an `Array`
  (statement with `xs[i]` bounds proofs), Euclid's gcd (`Nat.gcd` forbidden, so well-founded
  recursion and divisibility by hand), and run-length encode/decode round trip. `must`/`forbid`
  regexes keep the loop a loop. **All 8 proved:** Haiku loop 2 fixes, bsearch 2 fixes, gcd 1, rle
  first try; Sonnet loop 1 fix, **bsearch first try (86 lines)**, gcd 1, rle first try. Both binary
  searches really halve (`termination_by hi - lo`). Neither model used `mvcgen`/`vcgen`: both proved
  the loop by induction on a generalized accumulator, with `simp` unfolding the `for`. **Half the
  fix rounds (3 of 6) were again Mathlib names not in the note** (`Dvd.dvd.mul_right`, twice;
  `not_lt.mp`); the rest were ordinary unsolved goals. So across 20 task runs, everything proved
  within two fixes once core names were hinted, and names remain the single biggest cause of failed
  attempts.

- 2026-11-08 (night 4, wrap-up): D24 (c) closed (big-trial rerun: sentinels 6 -> 2); hidden-input
  trials against Python (`trials/hidden.py`, basic and rules sets: Haiku 171/171 in both languages,
  so no wrong answers to separate them); D25 (`"{"` is a literal brace) after the bracket task tripped
  on it; Lean-direct baseline (`trials/leanbase.py`, basic and hard sets): both models proved
  everything within two fixes once core-vs-Mathlib names were hinted. The verification direction is
  now a question for Ari (see Next step 1).

- 2026-11-08 (day, Ari in #claude-lang: "No opinion, make a judgement call" on night 4's question):
  **D26: claude-lang compiles to Lean 4**, so the program that runs is the one that's proved;
  no error layer over Lean-direct, and no Lean model beside the C backend. Reasons and plan in
  DESIGN.md D26. A hand-written spike (`trials/lean/backend_spike.lean`) checked the parts that could
  have sunk it: Lean's bundled `leanc` builds a native binary on the box (lean -c 1.4-7 s, leanc -O1
  1.5-5 s, both noisy under load); Arrays update in place (1M push + 1M set: 0.05 s at -O1);
  a `clTrap` (kernel: `default`; run time: flush, `runtime error: ...`, exit 70) stops the program
  where Lean's own `panic!` prints and carries on (the spike's "not reached" line printed). Two Lean
  gotchas on the way: a trap whose match arms all return `default` gets compiled away (the result
  must flow out of the IO), and `implemented_by` needs both functions in `Type` (universe mismatch).
  A contract (`tax` nonnegative) closed with `split`/`omega`, nothing hand-proved.

- 2026-11-09 (night 5, step 1): **D26 stage 1, the Lean backend runs.** `cl_lean.py` (~360 lines) emits Lean 4
  from the checked AST; `clc.py --backend lean` elaborates it with `lean -c` and links with the bundled `leanc`
  (found next to the real `lean` binary; it isn't on PATH). Covers Int/Bool/String, functions, `if`/`while`/
  `for` over numbers (all four forms; reversed counts an offset up from 0 so `continue` needs no step),
  `print`, interpolation, `length` of a string, and examples. **Examples are `#eval`s that print the C binary's
  own EXRUN/EXFAIL protocol**, not `#guard`s: `#guard` only says "false", and this way `example_diags` (factored
  out of `run_examples`) serves both backends, so failing-example messages are byte-identical. A trap inside an
  example exits `lean` with 70, which maps to `example-crashed` the same way. Functions go out callees first
  (Tarjan SCCs); recursive groups are `mutual partial def` for now (examples don't count as calls, or every
  function looked recursive). `clTrap` needs `never_extract`, or a constant trap could be hoisted to start-up.
  `tests/run.py --backend lean [names]` runs the suite on Lean, skipping what it can't emit yet (clc exits 3):
  **19 pass, 0 fail, 9 skipped** (lists, structs, enums). New `tests/ok/core.cl` covers stage 1 without lists
  and prints identically on both backends; a division-by-zero trap matches too (same message, exit 70).
  **D27: `/` and `%` are Euclidean** (`%` never negative), Lean's own and what `omega` handles; the C runtime
  and SPEC.md follow. A build is ~9 s on Lean vs ~0.2 s on C (box under swap), the suite 32 s vs 7 s.
  Known gaps: an io call on the right of `and`/`or` is lifted with `(← ...)` and so runs even when the left
  side decides (fixed in step 4); `let _ = pure_call()` may be dropped by Lean's compiler (harmless unless it traps or loops).

- 2026-11-09 (night 5, step 2): **D26 stage 2a, lists on the Lean backend.** `List[T]` is `Array T`;
  `xs[i]` (`clGet`), `xs[i] = v` (`clSet`) and deeper paths like `grid[i][j] = v` (`clModify` per level, which
  takes the row out first so it stays unshared; value first, then indexes, then the walk, as in C), `append`
  (`push`), `repeat`, `length`, list literals, `==` on lists, and `for x in xs` (`.reverse` for `reversed`;
  Lean's `for` holds the array it started with, which is D21's snapshot). Printing goes through a `ClShow`
  class giving claude-lang's formats (strings quoted with the language's escapes inside lists); its method is
  `fmt`, since `show` is a Lean keyword. **`tests/run.py --backend lean`: 24 pass, 0 fail, 4 skipped** (the
  four that need structs or enums). All four index/`repeat` trap messages match C's byte for byte, and so do
  nested updates and a list changed inside its own reversed loop. **Speed:** 1M appends + 1M updates in place,
  0.17 s vs C's 0.04 s while values stay small; Lean's `Int` is a scalar only up to about 2^31 and a heap
  bignum beyond, so the same loops summing to 10^12 took 0.48 s (the price of unbounded `Int`, D26). Not the
  range loop: a Nat range measured the same.

- 2026-11-09 (night 5, step 3): **D26 stage 2b, structs on the Lean backend.** A struct is a Lean `structure
  T_Name` with fields `v_name` (prefixed, so no field can clash with Lean keywords like `from`/`at`/`show` or
  generated names like `mk`/`rec`), `deriving BEq, Inhabited`, emitted after the structs its fields use. A
  struct that contains itself through a list (`Tree`) is a nested inductive, and deriving handles it. Each gets
  a generated `partial def T_Name.clFmt` printing `Point(x: 1, y: 2)` (one `mutual` block, no type classes
  inside, so formatters of structs in structs just call each other), then a `ClShow` instance. Construction is
  `T_Name.mk` with fields in declared order (`e.order`); `p.x` is a projection; field steps in assignment paths
  are `{ r with v_f := ... }`. **No hand-written in-place helpers needed:** Lean's reset/reuse already updates
  `{ b with items := b.items.set! ... }` in place (probe: 100k updates of a 100k-item field, 0.04 s), and a
  benchmark of 1M updates through `s.board[i]` and `s.cells[i].hits` runs in 0.23 s on both backends.
  **`tests/run.py --backend lean`: 26 pass, 0 fail, 2 skipped** (enums, options). Gap: structs that contain
  each other (A has `List[B]`, B has `List[A]`) raise Unsupported; Lean would need a `mutual` structure.

- 2026-11-09 (night 5, step 4): **D26 stage 2 done: enums, `Option`/`Result` and `match` on the Lean backend;
  `tests/run.py --backend lean` passes 28/28 with nothing skipped.** Enums are `inductive T_Name` (variants
  `v_Name`, fields `v_field`), declared with the structs in one dependency order; an enum that contains itself
  directly (`Add(left: Expr, right: Expr)`) is an ordinary inductive. `Option[T]` is Lean's `Option`; `Result`
  is a small `ClResult` (`ok value` / `err error`), not `Except`, which has no `BEq`. Formatters for structs and
  enums share one `mutual` block (`Moved(x: 1, y: 2)`, bare `Done`, `Some(3)`, `Err("bad")`). `match` is a
  `do`-block `match` (probe: `break`/`continue` in an arm reach the enclosing loop), binding fields by
  position from `pat.slots` with `_` for the rest; a `match` whose every arm returns now counts as returning,
  so no dead trap follows it. `trials/backends.py` runs every claude-lang program from the trial results
  (165 distinct) through both backends and compares exit code, stdout and stderr.
  Then the **io-lifting gap is fixed**: an io call on the right of `and`/`or` now sits under an `if` with an inner
  `do`, so it runs only when evaluated. Probe first: Lean already places `else if` and `while` condition actions
  correctly, so only `and`/`or` needed it. `tests/ok/io-order.cl` pins all three on both backends.
  **Corpus check** (`trials/backends.py`, report `trials/results/2026-11-09-1336-backends.md`): of the 165
  distinct claude-lang programs in the trial results, the current front end accepts 127, and **all 127 behave
  identically on both backends** (exit code, stdout and stderr; 126 clean runs and one failing example), with
  nothing unsupported. **But Lean took 1618 s in total vs C's 68 s: median 12.7 s per program** (min 5.5 s;
  niced, on a swapping box) against ~0.5 s.

- 2026-11-09 (night 5, step 5): **where a Lean build's time goes, and two cuts.** Measured on the adventure
  program (205 lines) and `tests/ok/enums.cl`: elaboration (`lean -c`) ~2-4.6 s wall but **~1.5 s CPU**, with
  a 477 MB peak RSS that's mostly Init's ~95 MB of memory-mapped `.olean` files; C compile at `-O1` ~1.3-2.7 s
  (`-O0` saves ~1 s but runs 2.5x slower, so not worth it); **static link 3.5-4.3 s**, because `leanc` links the
  whole Lean compiler library (`libLean`, `libleancpp`) and garbage-collects it. Cuts made in `clc.py`:
  `run` links against Lean's shared runtime (`libleanshared.so` plus `libInit_shared.so`; ~0.6 s, a 58 KB
  binary, same speed once running, +10-15 ms start-up), and `test` skips C entirely (examples need only
  elaboration): **test ~1.8 s, run ~7.5 s**, down from 10-14 s. `build` stays static so its binary works
  without Lean installed. **What's left is mostly this box:** with ~80 MB free, the mapped `.olean` files
  and the 221 MB shared runtime are re-read from disk on most builds, so wall time is 2-3x CPU time (enums:
  4.6 s wall vs 1.5 s CPU in `lean`, 1.2 s vs 0.5 s in the link). Elsewhere a Lean build would be ~3 s of CPU.
  The 400 MB cap isn't the cause (capped and uncapped measured the same). The prelude is 86 KB of every
  program's ~180-210 KB of generated C, so compiling it once into a cached module would save ~40% of the C
  compile and its elaboration: worth doing, but small next to the I/O. The Lean test suite takes ~150 s (C: 8 s).

- 2026-11-09 (night 5, step 6): **D26 stage 3: Lean is the default backend.** `clc.py` defaults to
  `--backend lean`, and `tests/run.py` runs Lean by default (`--backend c` for C; ~185 s vs 8 s). SPEC.md now
  says `Int` is a whole number of any size, and the runtime errors are division by zero, a bad index and
  `repeat` with a negative count. The front end's 64-bit literal check (`int-too-big`) applies only with
  `--backend c`, whose fix line says to drop the flag. New `tests/ok/bigint.cl` (30!, 2^100, Euclidean `/` and
  `%` on a 101-bit number) is marked `# backends: lean`, which `tests/run.py` honors. The trial harnesses
  (`trial.py`, `fixloop.py`, `hidden.py`) pass `--backend c` for fast builds until stage 4 needs Lean. DESIGN
  D26 records stages 1-3 as done. **Lean 30/30, C 29/29.**

- 2026-11-10 (night 6, step 1): **probe for D26 stage 4(a), recursive functions as total `def`s; decided as
  D28, not built yet.** Findings (`trials/lean/termination.lean`): Lean's own search tries only `sizeOf` of each
  parameter, so no `Int` recursion (`fact`, `fib`, `gcd`) proves as a plain `def`; with `termination_by
  n.toNat` and `decreasing_by all_goals (simp_wf; omega)` factorial, fib and a count-up `(hi - lo + 1).toNat`
  all prove. gcd needs `termination_by b.natAbs` and `grind [clMod_bound]` (a prelude lemma: `b = 0` or
  `0 <= clMod a b m < |b|`); binary search with `(lo + hi) / 2` needs `grind [clMod_bound, clDiv]`. Enum
  recursion (`Expr` eval) is structural and proves as a plain `def`. A tree through `List[Tree]`: Lean adds
  `k ∈ t.kids` for `for k in t.kids` by itself, and the proof is `have := Array.sizeOf_lt_of_mem ‹_ ∈ _›;
  have := T_Tree.clSize_v_kids v_t; omega` with a generated lemma `sizeOf r.v_kids < sizeOf r` (`cases r;
  simp; omega`). `f(n)` with base case `n == 0` correctly fails (negative `n` loops). **A try-each-candidate
  command needs `import Lean`, measured at 40-60 s per build here** (1.4 s with only Init), so D28 picks
  measures with a separate probe elaboration instead, read through `#print axioms` (`sorryAx` = failed).

- 2026-11-10 (night 6, step 2): **D28 built: recursive functions are total `def`s when clc finds a measure.**
  `cl_lean.py`: a recursive group gets candidates from its parameters (`candidates`), `emit(probe=True)` writes
  the probe (each candidate as `clT<i>_<name>` plus `#print axioms`), `read_probe` keeps the first candidate
  with no `sorryAx`; `clc.py lean_main` runs the probe only when some function is recursive. The real file
  says `-- terminates (D28), measure ...` or `-- partial: ...` above each recursive group. New
  `tests/ok/recursion.cl` (fact, fib, count-up sum, binary search, index walk, tree through a list field, enum
  eval, mutual even/odd, an io countdown: all total; `down` with base case `n == 0`: partial) has `# total:` /
  `# partial:` lines that `tests/run.py` checks against the generated Lean (it builds with `--emit-lean`
  instead of `run`; a wrong line fails, checked). Existing tests: gcd and enums' eval and structs' tree total;
  core's even/odd partial, correctly (base case `n == 0`). **Lean suite 31/31** (run before the pruning below;
  the five recursive tests pass after it), `recursion` passes on C too. **Probe cost:** recursion.cl's ten
  groups at first had 39 candidates, 8 s CPU (failed `grind` attempts, not their diagnostics: `-verbose` saved
  ~10%); pruned with syntax to 12 (3 fail), **3.1 s CPU**: a measure on `p` needs `p` compared in the body
  and some call passing it something smaller; `q - p` needs the two compared and `p` going up or `q` down;
  `natAbs` needs an argument made with `%` or `/`; the tactic-assisted structural candidate needs a changed
  struct parameter with size lemmas, or a list. gcd's probe is ~1.2 s CPU.

- 2026-11-10 (night 6, step 3): **D28 probe results are cached, and the corpus agrees.** `clc.py probe_lean`
  keeps the probe's `#print axioms` lines in `~/.cache/clc/probe/<sha256 of lean path + probe text>.txt`, so
  rebuilding an unchanged program skips the probe (recursion.cl `test`: 5.9 s CPU cold, 2.8 s warm); a timeout
  isn't cached. **Lean suite 31/31** with pruning and cache. `trials/backends.py --recursive` keeps only
  programs with recursion and says what D28 made of each group (report
  `trials/results/2026-11-10-1207-backends.md`). **Only 6 of the corpus's 127 programs recurse at all**
  (Claude writes loops), all 6 behave the same on both backends, and D28 makes 5 groups total (gcd, two
  trees' sum and depth) and 3 partial: Haiku's even/odd (base case `n == 0`, correctly), coins' `ways`
  (negative `kind` never stops, correctly), and **one miss**: Sonnet's even/odd sends a negative `n` to
  `is_even(-n)`, so it always stops, but the measure needs the sign (`2 * |n| + (1 if n < 0)`); no candidate
  covers a call passing `-p` yet. **So for stage 4 the bigger job is loops, not recursion**: `while` and `for`
  are what Claude writes, and proving anything about a function with a `while` needs it as a total
  definition too (Lean's `while` is `partial` inside).

- 2026-11-10 (night 6, step 4): **D29: `requires`/`ensures`, checked at run time (stage 4(b)).** Parser and
  checker in `clc.py` (keywords `requires`/`ensures`, `HEADER_KINDS`, `in_contract`; new codes
  `contract-placement`, `contract-unit`, `contract-effect`, `contract-main`; the checker stores each contract's
  text on its node as `s.text`); Lean in `cl_lean.py` (`function` wraps the body in one `if` per `requires`
  and takes `cl_loc`; `call` passes the call's location; `ensure_return`; `call_text` formats `f(a: 1)`).
  `down(n)` with `requires n >= 0` is now total (D28 sees the hypothesis). **Fixed on the way:** on Lean an
  example that stopped the program was blamed on the example before it, with no message ("it crashed"):
  `#eval` captures stdout/stderr and Lean evaluated the example's values before `EXRUN`. Now examples are
  thunks to `@[noinline]` `clExShow`/`clExBool`, and `EXRUN` and trap messages are written through
  `clRealOut` to `/dev/stdout`/`/dev/stderr`; a division by zero in an example now reads exactly as on C.
  Tests: `tests/ok/contracts.cl` (isqrt, down, count_digits, a struct parameter, clamp, an io function;
  `# total: down count_digits`), `tests/err/contracts.cl` (the six checker errors),
  `tests/err/contracts-run.cl` (a `requires` broken by an example). SPEC.md documents contracts (2.1k words). **Lean 34/34, C 31/31 + 1 skipped** (contracts need Lean).

## Next step
1. **Formal verification** (Ari, 2026-11-07: "we definitely want proofs, not just fuzzing"; see
   DESIGN.md open questions): contracts (`requires`/`ensures`), build-time counterexample search,
   then proofs. Lean 4 core is the likely backend: Ari OK'd it, it's installed at
   `/root/.local/share/lean/lean-4.35.0-linux/bin/lean` (CACHEDIR.TAG keeps it out of the off-site
   backup; re-downloadable; `lean`/`lake` on PATH via /root/bin symlinks, and this project owns the
   install, so other sessions ask here before upgrading or removing it), and it fits the box (~55 MB anonymous, 3 s per small file; DESIGN.md).
   `trials/lean/` has the measurement files and `probe.sh` (peak anon/file RSS).
   Ari's sanity check (2026-11-07): "is this buying Claude anything over just writing in Lean
   directly?" and "I expect models to get things right in Python as well. Does that undermine
   the whole project? Maybe, but it's just for fun." So, before building the verifier:
   - the **wrong-but-runs trial** (`trials/hidden.py`, `--set basic|rules`) found no wrong answers in
     either language (Haiku 171/171, night 4 steps 2 and 4). Next: a **change trial**: give the model
     a working ~100-line program in each language (e.g. the adventure game, or orders) and a change
     request (a new command or enum variant, a new pricing rule), then grade on hidden regression
     inputs plus the new behaviour. That's where exhaustive `match` and value semantics should matter,
     if anywhere. Sonnet only once a set separates anything.
   - the **Lean-direct baseline** is done (night 4, steps 5-6), and **D26 decides the direction: compile
     claude-lang to Lean 4.** Stage 1 is done (night 5, step 1: `cl_lean.py`, `--backend lean`).
     Stage 2 is done too (night 5, steps 2-4: lists, structs, enums, Option/Result, match). **Next: stage 3,
     Lean becomes the default.** Done (night 5, step 6); C stays as `--backend c` for the trial harnesses.
     **Next: stage 4, contracts**, the point of D26. Bite-sized order: (a) recursive functions as real `def`s,
     not `partial def` (**D28, built night 6 steps 2-3**, with a probe cache; small gap: a sign-flipping call
     `f(-n)` needs a `2 * |n| + (1 if n < 0)` candidate); `while` loops are a separate problem (Lean's `while` is `partial` inside;
     loops that need proofs may have to become `for` or recursion, or use `Loop` specs). (b) contracts checked
     at run time: **done, D29 (night 6 step 4)**. (c) Proofs, **next**: emit `theorem f_spec : requires -> ensures` and try `by unfold;
     omega`, `simp`, `grind`, `decide`; report an unproved goal at the claude-lang line, in claude-lang terms.
     Optional anytime: a precompiled prelude module (saves ~40% of the C compile).
   - a **change trial** (modify an existing program) is still the best place left for exhaustive
     `match` to show, if it shows anywhere (see night 4, step 4).
2. Maybe `join` / `contains` built-ins (both adventure programs wrote `contains` and a join again).
   `match` expressions and a `Map` wait for more than one model wanting them (see night 4, step 1).
3. Then a wrong-but-compiles trial, holes (D9), the
   formatter (D12). `parse_int(s) -> Result[Int, String]` is now possible (Result exists).
4. Small cleanups seen in part (b): the `if let` cascade (bound name undefined) and the extra
   `not-bool` after `if i is None`.

Known gaps: no list concatenation; no string iteration or indexing; nothing is freed; the `.cl`
extension clashes with OpenCL, so the name is still provisional.

## Repo
Public: https://github.com/Ari-Zerner/claude-lang (Ari, 2026-11-05). Push after each commit.

## How to build/test
`python3 tests/run.py`; under the box's memory cap:
`systemd-run --scope -q -p MemoryMax=400M -- python3 tests/run.py`.
