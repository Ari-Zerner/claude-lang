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
  definition too (Lean's `while` is `partial` inside: **not so in Lean 4.35**, see night 7 step 3).

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

- 2026-11-10 (night 6, step 5): **D30: the first proofs. Each `ensures` of a pure, total function is a
  theorem, tried by `fun_induction <;> grind` (recursive) or `unfold; grind`, else `sorry`;** `#print axioms`
  says which were proved; `clc.py` turns the rest into `unproved` warnings with a reason, and `clc test` says
  "N of M `ensures` proved". `cl_lean.py`: `spec_theorems` (emitted after the functions, before the examples)
  and `read_specs`. `tests/ok/contracts.cl` now proves 4 of 8: clamp, width, count_digits (by induction),
  down; unproved, as its `# unproved` marks say (checked by `tests/run.py` against `clc test --json`; a wrong
  mark fails, checked): isqrt's two (`while`), wrong_abs (false for x < -5, which
  no example reaches), spin (partial). `clc test tests/ok/contracts.cl` ~2.7 s CPU. **Lean 34/34, C 31/31 + 1 skipped.**

- 2026-11-10 (night 6, step 6): **D31: modular proofs.** Each spec theorem gets a `grind_pattern` on the call
  (the default trigger was the whole `decide (...)`, which no caller contains), so callers' proofs get callees'
  `ensures`; an unproved theorem is closed by its own axiom `clUnproved_f_j` instead of `sorry`, so `read_specs`
  can say "it follows from fn g's `ensures ...` (line N), which isn't proved". `tests/ok/contracts.cl`: 5 of 10
  proved, new `digits_plus` (from count_digits's `ensures`, proved) and `double_abs` (follows from wrong_abs's,
  unproved). The test now marks unproved `ensures` inline (`ensures ...  # unproved`) instead of a line-number
  list, which broke the moment a comment line was added. **Lean 34/34** (contracts re-run after the marker change), **C 31/31 + 1 skipped.**

- 2026-11-11 (night 7, step 1): **D32: an unproved `ensures` is tested on small inputs at build time, and a
  counterexample is an error.** `cl_lean.py`: `SEARCH_PRELUDE` (`clSmallInt`/`clSmallArrays`/..., `clCxCase`,
  `clCxFn`), `small_of` (small values of any type, no type classes, like `fmt_of`), `small_decls` (a
  `T_Name.clSmall` per struct and enum; a type that contains itself draws from one depth lower),
  `search_block`, `emit_search`. `clc.py`: `run_search` (streams the output; kills a call after 2 s of CPU),
  `cx_search` (rounds, cache in `~/.cache/clc/search/`, keyed on clc's own source too), `search_diags`.
  New codes: `ensures-false` and `input-crashed` (errors), `input-timeout` (warning); an `unproved` warning
  with no finding now ends "clc called it on N small inputs and none broke it".
  **It found the bug planted in our own test at once:** `wrong_abs(x: -6) returns -6` in
  `tests/ok/contracts.cl`, which the file's comment said "no example or call reaches". That function now
  hides its bug below -5000, `spin` (never stops for a negative n: now `input-crashed`) gave way to `steps`
  (stops, but by flipping the sign, so D28 can't show it), and the findings moved to the new
  `tests/err/contracts-search.cl`: a false `ensures`, an index into an empty list, a callee's broken
  `requires`, endless recursion; a caller stopped by its callee's false `ensures` isn't reported twice.
  Cost: ~1.2 s CPU per search run (one run when nothing is found, one more per finding); 3000 calls take
  0.2-0.3 s. `clc test tests/err/contracts-search.cl`: 15 s the first time here (five Lean runs), 2.3 s cached.
  Hazards found: endless non-tail recursion grows Lean's interpreter by ~100 MB/s (the search runs with
  `lean -s 16384`, which stops it in a second; **the main run's examples still have that hazard**), and an
  endless `while` needs a CPU-time limit, since wall time on this box lies.
  **Lean 35/35** (the full run plus a re-run of the four contracts tests after the last edits), **C 31/31 + 2 skipped.**

- 2026-11-11 (night 7, step 2): **D32 follow-ups: the search tries the function's own literals, and examples
  can't run away.** `cl_lean.py`: `literals` (Int and String literals of a function, compared Ints first),
  `LeanEmitter.seeds` (own literals, then examples', then callees'; `c, c - 1, c + 1`; at most 12, none above
  100000), `clSeeded` in the search prelude; every generator takes the seeds (`cl_si`, `cl_ss`), so they
  reach Ints inside lists and structs too. One literal joins per depth, so a three-parameter function still
  gets the first two or three crossed with small values. New `tests/err/contracts-seeds.cl`:
  `tax(income: 40000) returns 0` (the boundary between `< 40000` and `> 40000` forgotten) and
  `turn(cmd: "back") returns -180`, both out of reach before. `tests/ok/contracts.cl`'s hidden bug moved
  again, below -5000000 (a literal too large to be tried).
  **Examples:** the main Lean run now has a 64 MB stack (`lean -s 65536`); an example that recurses without
  end is `example-crashed: ... its recursion got too deep; it probably never stops` after ~2 s of CPU, where
  it used to grow ~100 MB/s for up to 120 s (new `tests/err/example-endless.cl`, Lean only: `tests/run.py`
  now honors `# backends:` in err tests and on the second line). Interpreter depth measured: 16 MB holds
  10000 nested calls but not 100000; 256 MB holds 100000 (peak RSS 775 MB when it fails at 1000000).
  **Lean 37/37, C 31/31 + 3 skipped** (the three contract tests that need Lean; `example-endless` is Lean only).

- 2026-11-11 (night 7, step 3): **loops probe: two routes to proving a function with a loop, both work on
  isqrt; not decided yet.** Hand-written Lean in the emitter's own style, with the real prelude.
  - **Route A, the loop as a recursive function** (`trials/lean/loops.lean`): `f.loop1` over the loop's
    variables, a run-time `invariant` check first (so the invariant is a hypothesis below it), `termination_by`
    from a `decreases` line or from the range, a loop theorem (invariant in, invariant and not-condition out)
    by `fun_induction <;> grind` with a `grind_pattern`, and the function's `ensures` by `unfold; grind` as in
    D30. **All four prove end to end:** isqrt (`while`, `decreases n - r * r`, the nonlinear `ensures` and
    all), triangle numbers (`for ... through`, `t * 2 == (i - 1) * i`), gcd (two variables, returned as a
    pair, `decreases y`; needed a new prelude lemma `clMod_pos`: `0 <= a % b < b` for `b > 0`), count_up (a
    list in the state). 2.9 s CPU for the file. Only `decreases n - r` for isqrt fails (it needs
    (r + 1)^2 >= r + 1). Compiled, the recursive loop is as fast as the `do` loop and updates its array in
    place (3M iterations, ~0.5 s and 124 MB both).
  - **Route B, Lean's own `mvcgen` on the loop as emitted today** (`trials/lean/loops_mvcgen.lean`). A
    correction first: **Lean 4.35's `while` isn't `partial`** (`Loop.forIn` is `repeatM`), and `mvcgen` takes
    a `WhileInvariant` and a `WhileVariant`. With those two terms and `all_goals (mleave; grind)`,
    **isqrt's `ensures` proves on `f_isqrt` exactly as clc emits it now**: no change to the program at all.
    The `for` loop gets as far as two open goals: `grind` doesn't know that the item after a prefix of
    `(1...=n).toList` is `1 + prefix.length`, or the list's length (two prelude lemmas, not written yet).
    `import Std.Tactic.Do` costs only ~0.3 s CPU. But the framework is mid-move: `mvcgen` is marked
    deprecated for `vcgen`, which is marked experimental, lives in `Std.WP`, and fails as a drop-in here.
  - **How they compare:** A needs a loop-to-recursion translation in `cl_lean.py` (and `break`, `continue`,
    early `return`, nested loops each need their own handling), but uses only what D28/D30 already use. B
    changes nothing that runs and gets `break`/`return`/nesting from Lean, but its proof scripts are written
    in a library that's being replaced, and `for` needs the lemmas above. Later, B's program logic is the
    natural home for "this function never traps" (D31's open item).

- 2026-11-11 (night 7, step 4): **D33 decided: loops are proved as they stand, with `mvcgen` (route B).**
  The three open probes all went through with invariant terms clc can write mechanically, so by the
  criterion set in step 3, B wins. `trials/lean/loops_mvcgen.lean` now holds five functions exactly as clc
  emits them, each `ensures` proved by one recipe inside `first | (...) | exact clUnproved_f_j ...`:
  isqrt, triangle (`for ... through`), count_up (`for ... until`, a list), gcd (two variables), first_square
  (an early `return` in a `for`). 4.9 s CPU for the file. A wrong invariant (`r * r < n`) falls back to the
  axiom without a Lean error, so D31's reporting carries over.
  What each probe needed: (1) range `for`: `clRco_cur`/`clRcc_cur` (three lines each from
  `Int.getElem?_toList_rco_eq_some_iff`), with explicit `grind_pattern`s (without them `grind` skipped
  them in a goal whose invariant doesn't mention the index), and `simp only` with `List.length_append` and
  `Int.length_toList_rcc/rco` before `grind`; (2) two variables: the state is the tuple of the loop's `var`s
  in declaration order; projections work where tuple patterns get stuck; (3) early `return`: the state
  gains an `Option`, the invariant says the `ensures` holds for the returned value, and `simp only
  [clTrap]` clears the trap messages first. Dead ends on the way: `mleave; simp_all; grind` works for the
  `for` but takes 6-10 s; passing the cursor lemmas as `grind [...]` arguments instead of patterns.

- 2026-11-11 (night 7, step 5): **D33 (a), the front end for `invariant` and `decreases` lines.** `clc.py`:
  two keywords; the statement parser takes them like `requires`; `Checker.loop_headers` (called for `while`
  and `for` before the body) checks the lines at the top of a loop's body and sets `loop.invariants` and
  `loop.decreases` (each node has `.text`, like a contract); `block(..., loop=)` places them; `all_nodes`
  walks an AST. Errors: `contract-placement` (not at the top of a loop; also, new, a `requires`/`ensures`
  nested inside a block, which used to be silently ignored), `decreases-for`, `duplicate-decreases`,
  `invariant-item` (`x` of `for x in xs`), `not-bool`, `type-mismatch`, `contract-effect`; `assert` now has
  a hint. C refuses such programs (exit 3); `cl_lean.py` skips the lines, so nothing that runs changes yet.
  Tests: `tests/ok/invariants.cl` (isqrt, triangle, gcd with two `invariant` lines, a list `for`, nested
  loops in an io function), `tests/err/invariants.cl` (12 errors, one per mistake). No program in the
  trial results uses either word as a name. **SPEC.md says nothing about them yet, on purpose:** until the
  proofs are in, the lines do nothing, and SPEC is what a model is told is true.
  **Lean 39/39, C 32/32 + 3 skipped.**

- 2026-11-11 (night 7, step 6): **D33 (b): functions with loops are proved.** `cl_lean.py`: `loop_plan`
  (per function: the terms `mvcgen` asks for, or the obstacle), `LOOP_PRELUDE` (the two range lemmas,
  `clMod_pos`), `LOOP_TACTIC`, `LOOP_IMPORT` (inserted at the top only when some theorem uses `mvcgen`);
  `spec_theorems` swaps D30's `unfold; grind` for the `mvcgen` script when the function has loops;
  `read_specs` takes its reason from `loop_why`. Shapes confirmed first: the state is the tuple of the
  assigned `var`s in declaration order whatever the order of assignment (`Int × Bool × Array Int`), a lone
  variable is no tuple, loops are numbered in source order with a `while` taking two numbers (variant,
  invariant), a list `for` runs over `xs.toList`, and locals are not in scope in an invariant goal (hence
  "parameters and the loop's own variables only").
  **Results:** `tests/ok/contracts.cl` goes from 5 to 7 of 10 `ensures` proved (isqrt's two, through its
  `while`); `tests/ok/invariants.cl` proves 5 of 7: isqrt, triangle, gcd (two `invariant` lines),
  count_small (a list `for`), first_square (a `return` inside a `for`, no `invariant` needed). The two
  left are meant to be: count_big's `c <= length(xs)` is true but not kept by a pass, and halve's `while`
  has no `decreases`. SPEC.md documents the lines now (2.4k words).
  **A bug in our own output protocol, found here:** the examples' `EXRUN` lines were written straight to
  stdout, which Lean block-buffers, so one could land inside a line of Lean's: it split
  `'clSpec_first_square_0' depends on axioms: ...` into `'clSpec_fiEXRUN 0`, and a proved `ensures` was
  reported unproved (never the other way round: an unreadable line counts as unproved). `EXRUN`, and the
  search's `CXRUN`/`CXDONE`, now go to stderr, where nothing else is written.
  **Lean 39/39** (the full run had one failure, `example-endless`, from the stderr change dropping its `EXRUN`
  lines; fixed and that test and the other ten example/contract/invariant tests re-run), **C 32/32 + 3 skipped.**

- 2026-11-11 (night 7, wrap-up): six steps. D32: an unproved `ensures` is tested on small inputs and on the
  function's own literals at build time, and a counterexample is an error (`ensures-false`,
  `input-crashed`); examples can't recurse away with the box's memory any more. D33: `invariant` and
  `decreases` lines, decided after probing two routes, then built: front end, and proofs through `while` and
  `for` loops with Lean's `mvcgen` on the loops as emitted. isqrt is proved end to end. Along the way: the
  progress lines moved to stderr after one split a line of Lean's output. Nothing is parked half-done;
  Lean 39/39, C 32/32 + 3 skipped. **Start next time at "Next, pick by value" below** (locals in
  invariants first, then a trial of whether models write invariants that prove).

- 2026-11-12 (night 8, step 1): **fixed `let`s in loop proofs.** An `invariant` or `decreases` line, a `for`'s
  range and a `while`'s condition may now use a `let` from before the loop whose value is made from the
  parameters alone, maybe through other such `let`s (`let n = length(xs)`, the commonest limit left by
  step 6). `cl_lean.py`: `lets_at_loops` (per loop, the `let`s in scope where it starts, so a name reused in
  two branches means the right thing), and `loop_plan` puts `let v_n : T := <its definition>; ` at the front
  of each term that needs it. No probe by hand was needed: `mvcgen` keeps the program's own `let` in the
  goal and `grind` matches the two. A local that comes from a `var` or an earlier loop is still refused,
  with a message naming it; so is a `while` whose condition uses one (before, that built a term Lean
  rejected and the warning gave the generic reason). `tests/ok/invariant-locals.cl`: eight functions, six
  proved (a local in a `for` invariant, a range from a chain of two locals, a local made by a call whose
  `ensures` the proof needs, one name in two branches, a `return` in the loop, a `let` after an earlier
  loop), two refused on purpose. `tests/run.py`: `# unproved: some words` now also checks the reason clc
  gives (checked that it can fail). SPEC.md's sentence updated.
  **Lean 40/40** (7 min for the full run on the loaded box, 2 min of CPU), **C 32/32 + 3 skipped.**

- 2026-11-12 (night 8, step 2): **set out to run the invariant trial; the reference answers found two prover
  gaps first.** Before asking a model, I wrote my own answers for six loop functions with correct invariants.
  Three didn't prove: division by subtraction (`ensures result * b <= a and a < (result + 1) * b`), a search
  whose `ensures` says `xs[result] == want`, and an iterative `fib` against a recursive `fib_spec`. A trial
  on that prover would have measured clc, not the model. Causes, each seen in the goal Lean was left with
  (`trials/lean/goals.py`: rewrites a theorem's script so every goal the tactic can't close is printed):
  (1) `grind` doesn't split an `and` known to be false, so the exit check `not (a and b)` told it nothing;
  fixed with `Bool.and_eq_false_iff` in the hints (`GRIND_HINTS`, now shared by D30's and D33's tactics).
  (2) `xs[i]`, `a % b`, `a / b` carry their source place for the trap message, so the same value written in
  two places was two terms; fixed in the prelude with `clGet_v`, `clMod_v`, `clDiv_v` (`@[grind =]`), and
  `clDiv` is no longer unfolded. `tests/ok/proof-values.cl`: four functions, all proved now; with the
  previous compiler three of them weren't (checked by running the last commit's `clc.py` from a copy).
  (3) Not fixed yet: a call to a function with `requires` carries its place too, and a loop proved equal
  to a recursive function needs that function unfolded. That is `fib` vs `fib_spec`, the next step.
  Slip to remember: I stashed `cl_lean.py` for a moment while the suite was running in the background;
  the tests import it fresh each time, so that run was thrown away and repeated. Compare against an old
  compiler from a copy (`git show HEAD:cl_lean.py > elsewhere`), never by changing the tree mid-run.
  **Lean 41/41, C 32/32 + 3 skipped.**

- 2026-11-12 (night 8, step 3): **`fib` is proved equal to `fib_spec`; places left the proof terms.** Three
  changes in `cl_lean.py`. (1) A place is now the Lean term `clAt line col`, not a string literal: `""` to
  the kernel, `file:line:col` at run time (`implemented_by`; the path sits in one constant, `clFile`). One
  `grind` rule, `clAt_eq`, makes all places equal, so `xs[i]`, `%`, and calls to functions with `requires`
  are one term wherever written. It replaces step 2's `clGet_v`/`clMod_v` (which didn't cover user
  functions); `clDiv_v` stays. (2) That also fixed a bug I hadn't known about: **proofs depended on the
  length of the file's path.** With `fib_spec` unfolded, `grind` hit "maximum recursion depth" when the
  program was compiled from the 107-character scratch path, and proved the same thing from a short path
  (found by bisecting: the equation is small, the messages alone are harmless, `maxRecDepth 1024` or a
  short path both fix it). (3) `spec_fns`: functions called from a function's contract lines, and what
  they call, go to `grind` as definitions to unfold (pure, total ones). Dead ends: a per-function lemma
  `f_g loc x = f_g "" x` (works, proved by `unfold f_g; simp only [clTrap]`, but needs a proof per
  function and leaves the long literals in); a hand-written clean definition lemma (works, but clc would
  have to write each function's body twice). Checked: trap messages show the same place as before
  (`trap.cl:16:9: runtime error: this call breaks ...`), and a 3M-pass loop with `xs[i % 3]` takes the same
  time (0.12 s), so `clAt` isn't computed per pass. `tests/ok/proof-values.cl` gains `fib`/`fib_spec` and a
  no-loop case (`ensures result == double(double(n))`); six `ensures`, all proved.
  **Lean 41/41, C 32/32 + 3 skipped.**

- 2026-11-12 (night 8, step 4): **the proof trial: Haiku 7 of 7, first try.** `trials/prove.py`: each task
  gives the model SPEC.md and a function's first lines (name, `requires`, `ensures`, an example; for three
  tasks a recursive helper the `ensures` calls) and asks for the function written with a loop. It checks
  that the contract lines are the ones given, that a hidden `main` prints the right thing, that the body
  keeps the task's rules (a loop, no recursion, no `*` in `mul`, no `/` or `%` in `divide`), and that clc
  reports nothing unproved; an answer that isn't there goes back with clc's words, up to twice. `--reference`
  grades my own answers (7 of 7 proved, including two new ones, `sum` against `sum_spec(xs, n)` and `power`
  against `pow_spec`); `--replay RUN.md [--clc OTHER]` grades an earlier run's first answers again.
  **Haiku: mul, divide, count_evens, find_index, fib, sum, power all proved on the first answer**, no fix
  round used (`results/2026-11-12-1303-prove-haiku.md`). Its answers aren't mine: `mul` and `power` are
  `while` loops with their own counter and `decreases`, `find_index` keeps a `found` variable with
  `invariant found == -1 or (found >= 0 and found < i and xs[found] == want)` instead of returning early,
  `count_evens` went straight to an index loop with `count <= i`. **The same seven answers on the compiler
  from before steps 2-3: 2 of 7** (`mul`, `count_evens`; `results/2026-11-12-1307-prove-replay-haiku.md`).
  So writing the invariants wasn't the hard part for the model on this set; the prover was what stood in
  the way, and the reference answers found that before any model was asked. Sonnet not run: nothing here
  separates models. The set is too easy to show where the limits are.

- 2026-11-12 (night 8, step 5): **a harder set of reference answers: six of seven proved at once, binary
  search found a bug in what clc writes for a loop with a `return`.** Proved as written: `gcd` by a loop
  against a recursive `gcd_spec` (invariant `gcd_spec(x, y) == gcd_spec(a, b)`), `factorial` and `digit_sum`
  against their definitions, reversing a list (`invariant length(out) == i`), `max_index`, and `is_sorted`
  against `sorted_spec(xs, n)` when written with a flag (with an early `return false` it can't be proved
  by unfolding: "not sorted up to i" has to climb to "not sorted up to length", which is an induction).
  Binary search didn't: a `while` with a `return` and an invariant the next pass needs. Cause
  (`trials/lean/goals.py`, then `grind`'s own report): the invariant clc wrote said "if a value was
  returned, the `ensures` holds for it; if none was, the invariant holds", and a pass starts knowing only
  that, so it could never use the invariant. Fix in `loop_plan`: during a `while`, "none returned and the
  invariant"; for a `for`, "none returned or nothing left to visit" in front (the first wording,
  "returned implies nothing left", left `grind` a case split on the `Option` that it doesn't make).
  `tests/ok/loop-returns.cl`: `bsearch` and `capped_sum` (a `for` whose returned value is right only
  because of the invariant), both proved now, neither before.
  The harder tasks are in `trials/prove.py` as `--set hard`, not run on a model yet.
  **Lean 42/42, C 32/32 + 3 skipped.**

- 2026-11-12 (night 8, step 6): **the harder set on Haiku: 5 of 7 first answers proved, 1 after a fix, and
  the miss was clc's.** `results/2026-11-12-1500-prove-hard-haiku.md`. First answer proved: `bsearch`, `gcd`
  (against `gcd_spec`), `factorial`, `reversed_list`, `max_index`. `is_sorted`: its first invariant (`i >= 1
  and i <= n and ok == sorted_spec(xs, i)`) is false when the list is empty (the loop starts at i = 1 > n);
  the message it got back was the generic one, and its second answer added `if n < 2 return true` and
  proved. `digit_sum`: not proved in three answers, and the first was right: `while m > 0` with `invariant
  m >= 0 and total + digits_spec(m) == digits_spec(n)`. Its last pass needs `m % 10 == m` and `m / 10 == 0`
  below 10, and clc's proofs knew only `%`'s bounds. Added `clMod_v` to the prelude (`clMod a b m = if b = 0
  then 0 else a % b`); replaying the run's first answers then proves 6 of 7
  (`results/2026-11-12-1507-prove-replay-hard-haiku.md`). That loop is now in `tests/ok/proof-values.cl`.
  My reference had dodged the gap by stopping at `m >= 10`: reference answers find the gaps my own
  habits walk into, a model's answers find others. Seen but not acted on: in two fix rounds Haiku added
  true but useless `invariant` lines, because the message can't say which of "start / kept / enough"
  failed; that is item (iii).
  **Lean 42/42, C 32/32 + 3 skipped.**

- 2026-11-12 (night 8, wrap-up): six steps. Loop proofs may use a `let` made from the parameters. Then the
  proof trial, which turned into a prover clean-up before and after a model was asked: writing reference
  answers found that a false `and` isn't split, that a value written in two places was two terms, that
  proofs depended on the length of the file's path (places are `clAt line col` now), that a contract
  calling a function needs its definition, and that a loop with a `return` couldn't use its invariant;
  Haiku's answers found that proofs didn't know what `%` is. Haiku, given SPEC.md and a contract: 7 of 7
  first answers proved on the first set, 6 of 7 on the harder one (the seventh after one fix). The same
  first-set answers on last night's compiler: 2 of 7. Nothing is parked half-done; Lean 42/42, C 32/32 + 3
  skipped. **Start next time at (iii) under "Next step": say which part of a loop proof failed.** Small
  things seen on the way: `clc.py run --emit-lean` writes no `.lean` (only `build` does); the full Lean
  suite takes 7 minutes on the loaded box, so a step that changes the prover waits on it twice (maybe a
  `run.py --proofs` that runs only the files with `ensures`).

- 2026-11-13 (night 9, step 1): **the `unproved` warning says which part of which loop failed, and on the
  way a hole turned up: loop proofs could "prove" a false `ensures`. Fixed (D34).**
  (a) *The message, item (iii).* Each loop's invariant is wrapped in a mark, `clInv k (...)`; a goal the
  closing tactic can't close is printed and closed by the theorem's gap axiom `clGap_f_j`; `read_gaps`
  tells from where the mark stands whether the goal was the loop's start, a pass, or the `ensures` after
  the loop, and `gap_reason` words it ("clc couldn't show that `invariant ...` is true when the `for` on
  line 15 starts"). That is exactly what Haiku's first `is_sorted` answer now gets back (replay), where
  last night it got the three-way "either ... or ... or". `tests/ok/loop-gaps.cl`: one function per case,
  the wording checked by `# unproved: ...` marks. Dead end: a custom `elab` tactic that prints the open
  goal's name (works, but `import Lean.Elab.Tactic.Basic` makes a static binary 118 MB instead of 4.5,
  since the tactic is compiled into the program). Goal names alone don't name the loop anyway.
  (b) *The hole.* A function ends in "if the `ensures` is broken, trap", and to the kernel a trap was
  `default`. The loop tactic unfolds `clTrap`, so `grind` knew a trapped Int is 0, and an `ensures` that 0
  satisfies (`result >= 0`) was proved whatever the loop did; the search (D32) only looks at unproved
  ones, so a false `ensures` got through to run time in silence. In the compiler since night 7 step 6.
  Found because the new mark made a no-invariant goal `clInv 1 True`, the tactic's `simp` closed it, and
  the `grind` after it failed for want of a goal; with that mended (`<;>`), a function with no invariant
  came out proved. The old tactic's wrong failure had been hiding the hole for loops with no invariant;
  with any true invariant the hole was open (`down_too` in the new test). Fix: `opaque clTrapVal`,
  `clTrap msg := clTrapVal`; `clDiv_v`/`clMod_v` now need `b ≠ 0`. Functions without loops never had it
  (checked on last night's compiler). `tests/err/loop-trap-value.cl`: three false `ensures`; last night's
  compiler reports one, this one all three.
  (c) *Earlier results, graded again* (`prove.py --reference`, `--replay`, no model called): reference
  answers 14 of 14, Haiku's first answers 7 of 7 and 6 of 7, the same as last night. Two tasks
  (`count_evens`, `max_index`) have an `ensures` 0 satisfies, so the old compiler would have passed any
  loop there; Haiku's invariants prove them honestly. Lesson for the trial: an answer that should NOT
  prove belongs in the harness too (a wrong loop per task that must come back unproved or `ensures-false`).
  Also: the full Lean suite takes 3 min 9 s on the resized box (2 vCPU, 4 GB), down from 7.
  **Lean 44/44, C 32/32 + 4 skipped.**

- **2026-11-13 (night 9, step 2): a control for the proof trial; an unproved `ensures` that is false.**
  (a) *The control.* Each of the 14 tasks in `trials/prove.py` now has a `wrong` body with its `slip` in
  words, whose `ensures` is false for some input (off by one, `>` for `>=`, the wrong variable returned,
  `+` for `*`, an item skipped). `prove.py --control [--set hard] [--only ...] [--clc OTHER]` builds each
  with `clc test`, the header's `example` lines left out so a failing example can't stop the build before
  the proof is tried, and exits 1 if one comes out proved. Takes 25 s a set (nothing is linked or run).
  This compiler: 14 of 14 caught, each as `ensures-false` with an input. Night 8's compiler: 12 of 14; it
  calls the wrong `count_evens` (counts evens twice, `invariant c >= 0`) and the wrong `max_index` proved,
  the two tasks D34 named. So the control would have shown that hole the night it was made.
  (b) *A question it raised, answered: no hole.* An unproved `ensures` is an axiom its callers' proofs may
  use (D31), and one that is false somewhere proves anything: Lean does prove `ensures result == 7` for a
  function that returns 3 and only mentions `far(2000000)` (in a branch never taken, or in an `invariant`),
  from `far`'s unproved `ensures x < 1000000`. It was never reported proved, because a theorem that uses
  another's `clUnproved_`/`clGap_` axiom is "it follows from fn far's ..., which isn't proved": warning
  kept, searched by D32, check kept at run time. So "proved" means no axiom of ours at all. No test had a
  false one; `tests/err/assumed-callee.cl` does now (mutation-checked: with that rule off in a copy, both
  come out proved, "2 of 3").
  Not run: the full suites (the compiler didn't change; the new test and `loop-trap-value` pass, and
  `--reference --only mul`). Lean is 45 tests now.

- **2026-11-13 (night 9, step 3): the warning names the `invariant` line and which of a pass's jobs failed.**
  Each job has its own mark now: `clInv k j` (line j of loop k; j = 0 for what clc adds itself), `clRet k`
  (a value returned inside the loop meets the `ensures`), `clDec k` (around the `decreases` measure). A goal
  the closing tactic can't close whole is taken apart at its `∧`s and `→`s (`gap_tactic`), each part is
  tried, and only what stays open is printed; `read_gaps` returns (loop, part, job) and `gap_reason` words
  it. Examples, all in `tests/ok/loop-gaps.cl` (three functions added): "a pass of the `for` on line 92
  keeps `invariant s == i` true" (of two lines); "a pass of the `while` on line 25 makes `decreases n - m`
  smaller while it stays at 0 or above" (no longer adds the invariant, which is kept); "a pass of the
  `while` on line 123 returns only a value that meets this `ensures`"; the start names its line too.
  Two traps on the way, both in D33: `repeat'` takes a whole tactic sequence, so without parentheses the
  rest of the line was its body and an unsplittable goal was left open (a Lean error, not a failed
  alternative); and a `while` pass's goal is "there is a new measure value a with ...", settled by
  `apply Exists.intro` then `exact rfl` on its first part. Also a Python slip caught by the tests: a local
  named `scope` shadowed `loop_plan`'s own.
  Checked: **Lean 45/45**; `prove.py --reference` 14 of 14 and `--control` 14 of 14 (both sets); Haiku's
  first answers on the hard set, replayed: 6 of 7 as before (the miss is `is_sorted`, a one-line invariant
  false at the start, worded as in step 1). The C suite wasn't run (only `cl_lean.py` changed). No stored
  Haiku answer fails on a pass or with several lines, so what the new wording does to a fix round is
  still to be seen: that is (iii-d).

- **2026-11-13 (night 9, step 4): does the exact warning help a fix? A fix-round trial, and a prover gap.**
  (a) *Harder set on Haiku again* (`trials/results/2026-11-13-1400-prove-hard-haiku.md`): 6 of 7 first
  answers, `reversed_list` after one fix. `is_sorted` and `digit_sum` proved first try this time, so
  the run said nothing about fix rounds on them.
  (b) *So a trial that starts at the fix round:* `trials/provefix.py`. Nine right functions with flawed
  proof lines; Haiku gets the answer plus one compiler's words (night 8's from git, or this one's) and
  its one fix is graded with this compiler. `--dry` shows both compilers' words without a model.
  Eight written cases: 16 of 16 either way (too easy to separate anything). Haiku's own night-8
  `is_sorted` miss: old words 4 of 7, new words 7 of 7 (two runs, 2 + 5 repeats). Suggestive, not
  shown. For a sharper test, collect real misses as cases (each trial run's unproved first answers).
  (c) *Prover gap found by (a):* Haiku's first `reversed_list` used `var out = repeat(item: 0, times: n)`
  and `out[n - 1 - i] = xs[i]` with `invariant length(out) == n`, which is true; clc couldn't show it
  at the start or across a pass. In the prelude `clRepeat` and `clSet` are plain definitions with a
  trap branch and no fact for `grind`. Wanted: `(clRepeat x n msg).size = n` for `n >= 0`,
  `(clSet xs i v loc).size = xs.size` for `i` in range, the same for `clModify`, as `grind_pattern`
  theorems like `clMod_pos`; then replay the 1400 run (`--replay`), which should come out 7 of 7.
  No compiler change in this step, so no suite run.

- **2026-11-13 (night 9, step 5): proofs know list lengths under `repeat` and assignment.** Three theorems
  in the prelude (`clRepeat_size`, `clSet_size`, `clModify_size`, each `@[grind =]` and proved there, no
  axiom): `repeat` makes `times` items for `times >= 0`; `xs[i] = v` and `xs[i].f = v` keep the length for
  `i` in range. `tests/ok/loop-lists.cl`: five functions, all proved, the first being Haiku's
  `reversed_list` from step 4. Replaying that run (`2026-11-13-1505-prove-replay-hard-haiku.md`): 7 of 7
  first answers now. **Lean 46/46, C 32/32 + 5 skipped**; `--reference` 14 of 14, `--control` 14 of 14.
  Not done: the items of a list after `xs[i] = v` (unchanged elsewhere, `v` at `i`), needed once an
  `ensures` speaks of contents; no trial task does yet.

- 2026-11-13 (night 9, wrap-up): five steps. The `unproved` warning for a loop now says which loop, which
  `invariant` line, and what about it clc couldn't show (true at the start; kept by a pass; `decreases`
  smaller; a returned value; enough at the end). Making it say so uncovered a hole, closed as **D34**: a
  false `ensures` on a function with a loop was reported proved whenever 0 (or false, "", []) satisfied
  it, because to a proof a trap was worth the default value; it is an unknown value now. The proof trial
  got a control (one wrong loop per task that must not come out proved: 14 of 14 caught, 12 of 14 by
  night 8's compiler) and a fix-round trial (`provefix.py`: old words against new, no difference on
  eight written flaws, 4 of 7 against 7 of 7 on Haiku's own miss). Haiku's fresh run found that proofs
  knew nothing of list lengths under `repeat` and `xs[i] = v`; they do now, and that run replays at 7 of
  7 first answers. Nothing is parked half-done; Lean 46/46, C 32/32 + 5 skipped. **Start next time at
  (iii-f) under "Next step": a trial task whose `ensures` speaks of a list's contents.** Small things
  seen on the way: `prove.py --replay` grades only first answers (a `--attempt N` would have saved a
  script); result files from `--reference`/`--control` pile up when nothing changed (maybe write them
  only on a change or with `--keep`); the Lean suite is 3.5 min on the resized box.

- **2026-11-14 (night 10, step 1): proofs know a list's items after `xs[i] = v`, `append` and `repeat`; `==`
  on a struct or an enum is equality.** Step (iii-f) began with a probe: six one-line contracts about
  contents with no loop (`out[i] = v` then `ensures result[i] == v`; `result[j] == xs[j]` for `j != i`; a
  swap; the item `append` adds and the ones it keeps; an item of a `repeat`). None proved: to a proof
  `clGet (clSet xs i v) j` was a term nothing is known about.
  (a) *Four theorems in the prelude* (`clGet_push`, `clGet_clSet`, `clGet_clModify`, `clGet_clRepeat`, each
  `@[grind =]` and proved there): after `xs[i] = v` with i in range, `xs[j]` is `if j = i then v else` what
  it was; after `append`, `if j = length then v else` what it was; `xs[i].f = v` and `grid[i][j] = v`
  (`clModify`) change the item at i and no other; an item of `repeat(item: x, times: n)` at `0 <= j < n` is
  x. The first three ask nothing of j: out of range both sides are the same trap (a trap's value doesn't
  depend on its message), so `grind` has one case split, not a side condition to discharge.
  (b) *Struct `==`.* `result[j] == cells[j]` on a list of structs still didn't prove: structs and enums
  were `deriving BEq` only, so to a proof `p == p` wasn't known to be true. Lean 4.35 derives `ReflBEq` and
  `LawfulBEq` too, except for a type that contains itself ("not supported for nested inductives"). clc
  now derives them for every struct and enum that neither contains itself nor holds one that does, and
  for `Result`. For a tree-like type `==` stays unknown to proofs (it still runs).
  (c) *Tests.* `tests/ok/list-items.cl`: 12 functions, every `ensures` proved (the six, a struct's field
  in a list, an enum, a grid cell, and two loops whose invariant speaks of one fixed place:
  `i <= k or out[k] == v`). `tests/err/list-items-false.cl`: four slips (no `j != i`; a swap that reads
  the place it just wrote; `append` taken to put its item first; a changed struct said to be unchanged),
  each `ensures-false` with an input.
  Lean name churn again: `if_neg`, `dif_pos`, `dif_neg` are deprecated in 4.35 (`ite_eq_right`,
  `dite_eq_left`, `dite_eq_right`).
  Checked: **Lean 48/48** (46 + the two new files); `prove.py --reference` 14 of 14 and `--control` 14 of
  14 wrong loops caught, both sets. The C suite wasn't run (only `cl_lean.py` changed).
  *Not reached:* an `ensures` about **every** item. The language can only say that through a helper
  (`all_ge(xs, n, lo)`, recursive over a prefix), and then a pass needs "the helper's answer for the
  first i items doesn't change when an item is appended after them", which is an induction `grind` won't
  find. So the trial task waits for a decision: a bounded quantifier in contracts, or clc proving such
  frame facts for helpers itself. Next step probes both by hand in Lean.

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
     `f(-n)` needs a `2 * |n| + (1 if n < 0)` candidate); `while` loops are a separate problem (I took Lean's `while` for `partial` inside; in 4.35 it isn't, night 7 step 3;
     loops that need proofs may have to become `for` or recursion, or use `Loop` specs). (b) contracts checked
     at run time: **done, D29 (night 6 step 4)**. (c) Proofs: **started, D30 (night 6 step 5)**: each `ensures` of a pure, total function is proved by
     `grind` (with functional induction for recursion) or reported `unproved`. **Next, in order:** (1) modular
     proofs: **done, D31 (step 6)**, except proving each call's `requires`, which needs per-call-site theorems
     with the path condition or a model where traps are visible (D31 says why); (2) a counterexample for an unproved `ensures`:
     **done, D32 (night 7 steps 1-2)**, by calling the function on small inputs and its own literals.
     Follow-ups left, small: lists longer than four items from a tiny item pool; maybe search functions with
     no contract for crashes (run it over the trial corpus first to see how much it flags).
     **D33 is decided (night 7 step 4): `invariant`/`decreases` lines, proved by `mvcgen` on the loop as
     emitted.** Build order, one step each:
     (a) **front end: done (night 7 step 5)**, except the SPEC paragraph, which goes in with (b).
     (b) **proofs: done (night 7 step 6)** for loops that aren't nested, have no `break`, and whose lines
     mention only parameters and the loop's own variables.
     Locals in invariants: **done for `let`s made from parameters (night 8 step 1)**; a local that comes
     from a `var` or an earlier loop is still out (D33 says what it would need).
     **Next, in order:** (i) **done (night 8 step 3)**: `fib` proves against `fib_spec` (`clAt`, `spec_fns`).
     Open from it: a `grind` that runs out of heartbeats is still a Lean error, and unfolding recursive
     functions makes that likelier, so item (4) below (a cap that falls back to the axiom) has moved up;
     and no test compiles from a long path (the cause is gone by construction, the check was by hand).
     (ii) **done (night 8 step 4)**: Haiku 7 of 7 on the first answer (`trials/prove.py`). The harder
     set's reference answers all prove (step 5) and are in `prove.py` as `--set hard` (binary search, gcd,
     factorial, digit sum, reverse, max index, is_sorted). **Run on Haiku (step 6): 6 of 7 first
     answers prove once `%` was fixed.** Next for the trial: a task where the model must write
     the helper definition itself, and ones that sit on today's limits to see what the model does there
     (`for x in xs`, a `break`, nested loops, a local from an earlier loop). **But (iii) comes first now:**
     both trial misses went back with a message that couldn't say which part failed. Also worth a sentence in SPEC once a trial shows it's needed: a contract may call another
     function as the definition to agree with. (iii) which goal failed:
     **done (night 9 step 1)**, by loop and by part (start / a pass / after the loop); and **D34** closed
     a hole it uncovered (a trap's value is unknown to proofs now). (iii-b) a negative control: **done (night 9 step 2)**,
     `prove.py --control`, 14 of 14 wrong loops caught (12 of 14 by night 8's compiler); run it and
     `--reference`, both sets, after any change to how loops are proved. (iii-c) the `invariant` line and which of a pass's
     jobs: **done (night 9 step 3)**. (iii-d) the harder set on Haiku again and a fix-round trial:
     **done (night 9 step 4)**, `trials/provefix.py`: no difference on eight written flaws, 4 of 7 against 7 of
     7 on Haiku's own `is_sorted` miss. (iii-e) list lengths under `repeat` and `xs[i] = v`:
     **done (night 9 step 5)**. (iii-f) the items after `xs[i] = v`, `append`, `repeat`, and struct
     `==` as equality: **done (night 10 step 1)**. **Next, in order:** (iii-f2) how a contract says
     something about *every* item. Probe by hand in Lean, on three loops (clamp every item to `>= lo`
     built by `append`; reverse filled in place; `is_sorted` after an in-place change): (1) a helper
     function over a prefix, as `sum_spec` is, which needs a frame fact per helper ("unchanged by an
     append or an assignment past the prefix": could clc state and prove it by `fun_induction` itself?);
     (2) a bounded quantifier, e.g. `all j in 0 until i: out[j] >= lo` and `all x in xs: x >= lo`, as
     `∀ j, 0 ≤ j → j < i → ...` for proofs and a loop at run time (so D29's checks and D32's search
     still work). Then decide (a D35), build, and write the trial tasks: every item `>= lo`, reverse
     against "result[j] == xs[n - 1 - j]", a map. After that the limits tasks (`for x in
     xs`, a `break`, nested loops, a local from an earlier loop); (iii-g) grow `provefix.py`'s cases
     from real misses; then (c) and (d). Small: a
     `--goals` flag that shows the open goals clc now reads (they are in Lean's output after `CLGAP f_j`).
     (c) run-time checks: each `invariant` (not as an early `return`: try `v := clGuard ok msg v` on one state
     variable) and "`decreases` went down", so D32's search can show a false invariant with its input.
     (d) `break`, nested loops (find out how `inv1..invN` are numbered), `for x in xs`, `reversed`.
     (3) loops: `for` over
     ranges first, with `invariant` lines, likely by emitting the loop as a local recursive function; then
     `while` with a `decreases` measure; (4) a `grind` heartbeat cap that degrades to the `clUnproved` axiom (a timeout is an error today).
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
