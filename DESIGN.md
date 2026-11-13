# claude-lang: design notes

Working name. A language meant to be good for Claude to write, read and fix, not for a
human typing at a keyboard. Decisions are numbered so later notes can cite them (D1, D2...).
Anything marked *open* is still being decided.

## Who the user is, and what that changes

Claude differs from a human programmer in ways that matter for language design:

1. **It has never seen this language in training.** All it knows about the language is what fits
   in its prompt. → The whole language (spec + stdlib reference) has to fit in a few thousand
   tokens, and it must not lean on conventions from other languages that it would half-remember
   wrongly.
2. **It writes left to right, in one pass, and going back costs a lot.** It can't jump back up to
   fix a brace 200 lines earlier as cheaply as a human with an editor. → Mistakes should be
   local and caught locally: redundant closers, no constructs whose meaning depends on something
   far away.
3. **It types for free but reads at a cost.** Verbosity is cheap to write; ambiguity is expensive
   to resolve. → Explicitness over concision wherever they conflict.
4. **It works in an edit-compile-fix loop driven by compiler output.** → Diagnostics are a
   primary interface, not an afterthought: exact, complete (all errors at once), structured, each
   with a concrete suggested fix.
5. **It is confidently wrong in characteristic ways**: plausible but nonexistent functions,
   off-by-one, wrong argument order, forgotten edge cases. → The language should make those fail
   loudly at compile time: named arguments, no implicit conversions, exhaustive matching, inline
   examples that are run as tests.
6. **It sees the program through a context window, often one function at a time.** → A function
   should be understandable from its own text plus the signatures it calls: no global mutable
   state, no implicit imports, no overloading, effects shown in signatures.
7. **It reads tokens, not characters.** → Keywords are common English words (one token each);
   no sigil soup; nothing where whitespace counts that a tokenizer might blur.

## Decisions

- **D1. Implementation: the compiler is Python 3, and its output is C compiled by gcc.** Both are
  already on the box; there's no build step for the compiler itself, and C output is easy to read
  when debugging. (Possible later: self-host, or emit something else directly.) D26 replaces
  the C output with Lean 4 once the Lean backend passes every test.
- **D2. Blocks end with a named closer:** `fn parse ... end fn parse`, `if ... end if`. It's
  redundant on purpose: a mismatch is reported right where it happens ("`end if` closes the `if`
  on line 12, but the innermost open block is the `loop` on line 15").
- **D3. Static types, required on every function signature, inferred inside bodies.** Signatures
  are the contract Claude reads when it doesn't have the callee's body in context.
- **D4. Arguments are named at the call site whenever there's more than one:**
  `copy(from: a, to: b)`. This kills wrong-argument-order bugs. One-argument calls may be
  positional.
- **D5. No implicit conversions, no operator overloading, no function overloading.** One name
  means one thing.
- **D6. Conventional precedence, except where readers commonly slip.** Arithmetic binds tighter
  than comparison, which binds tighter than `and`/`or`; Claude never gets those wrong, so
  requiring parentheses there would be pure noise. These are errors, with the fix spelled out:
  mixing `and` with `or`; chained comparisons (`a < b < c`); `/` or `%` followed by another
  `*`/`/`/`%` (`a / b * c`); `not` in front of a comparison or arithmetic (`not a == b`).
  (Revised 2026-11-05 while implementing; the first draft required parentheses for every mix.)
- **D7. Errors are values** (`Result[T, E]`) with exhaustive `match`; no exceptions, no null.
  `?`-style early return is *open* (it's concise but hides control flow).
- **D8. Examples are part of the function.** A function may carry `example` lines
  (`example add(a: 2, b: 3) == 5`), and the compiler runs them on every build. Claude writes these
  naturally, and they catch confident-but-wrong code right away.
- **D9. Holes.** `hole` (or `?name`) can stand in for any expression; the compiler reports the
  expected type and the variables in scope there, and won't produce a binary until holes are
  filled. This supports writing a program top-down across several turns.
- **D10. Diagnostics** carry file:line:col, an error code, one-line message, the offending
  source line, and a `fix:` line with concrete replacement text when one exists. A
  `--json` flag gives the same as machine-readable output.
- **D11. The spec is a deliverable with a token budget:** `SPEC.md`, target under ~4k tokens,
  written to be pasted into a prompt. If a feature can't be explained briefly, that counts
  against the feature.
- **D12. One canonical layout,** enforced by a formatter, so there is never a choice to make
  about how to lay code out.

- **D13. One statement per line, no line continuation.** Newlines end statements and there are
  no `;`. Every error is confined to its line, which makes recovery trivial and lets the
  compiler report every error in one pass. Long lines are fine; Claude doesn't mind them.
- **D14. Error codes are words, not numbers** (`closer-mismatch`, `arg-order`), so a code
  means something on its own in a transcript.
- **D15. Hints for other languages' habits.** `&&`, `{`, `;`, `elif`, `def`, `println`, `True`,
  `endif`... each get a targeted "write X instead" rather than a generic syntax error, because
  carrying over another language's habits is the most likely mistake when writing a language
  that isn't in the training data.
- **D16. Runtime errors are checked, never undefined:** integer overflow and division by zero
  stop the program with `file:line:col: runtime error: ...` (exit code 70). With D26, `Int` becomes
  unbounded, so overflow can't happen; division by zero and bad indexes stay traps.
- **D17. Names can't be reused within a function** (no shadowing), and an unused result of a call
  is an error (`let _ = f(x)` discards on purpose). Both are frequent sources of quiet bugs.

- **D18. Strings: `String`, interpolation instead of `+`.** `String` matches `Int`/`Bool`'s
  Swift-style names (and is what Claude writes by default). `"{a}{b}"` covers both formatting and
  concatenation, so `+` keeps exactly one meaning (D5) and there's no `to_string` call to forget.
  Strings are immutable. Memory: **planned value semantics** for every type (assigning or passing
  never creates a shared, mutable alias; Claude reasons badly about aliasing), implemented with
  reference counting and copy-on-write when lists arrive. Immutable values can't form cycles, so
  refcounting would be exact. **v0 never frees strings**, which is fine for short programs.

- **D19. Lists: `List[T]`, value semantics, copy-on-write, 0-based.** (2026-11-06)
  - *Values, not references.* `var ys = xs` copies, and a callee can't change a caller's list.
    Aliasing bugs are exactly the far-away, non-local kind Claude handles worst (point 6), and it
    matches how `Int` and `String` already behave, so there's one rule for every type.
  - *Copy-on-write makes that cheap.* Each list carries a count of the variables and slots that
    may refer to it; mutation copies only when the count is above 1. Arguments are borrowed
    (parameters can't change; storing one anywhere bumps the count), a local returned is moved,
    and `xs = append(list: xs, item: x)` is compiled to an in-place push. 1M appends plus 1M
    `xs[i] = ...` with a function call in between: 0.27 s. Nothing is freed yet, so the count can
    only over-count, which costs an extra copy but is never wrong. Lists can't contain themselves
    (the types forbid it), so real refcounting later will be exact.
  - *`append` returns a list instead of mutating.* That keeps mutation visible at the assignment,
    and the Python habit `append(xs, 4)` on its own line is then an unused result, which D17
    already rejects; the fix says `xs = append(list: xs, item: 4)`. `xs.append(4)` gets the same
    fix from the lexer.
  - *0-based*, because every language Claude knows best is; 1-based would invite systematic
    off-by-one. No negative indexing (`xs[-1]` is a compile error with the `length(xs) - 1` fix),
    and an out-of-range index names the length and the last valid index.
  - *`xs[i] = v`* on a `var`; deeper paths like `grid[i][j] = v` since D23.
  - `List[T]` with square brackets: it's what Claude writes in Python type hints, and `<...>` would
    collide with comparison. `list[int]`, `Vec<Int>`, `Int[]` all get the fix `List[...]`.
  - No list `+` and no `concat` yet; `[0] * n` gets the fix `repeat(item: 0, times: n)`.
- **D20. A line with a lexical error reports only that error.** (2026-11-06) Parser and checker
  errors on the same line are almost always fallout from the bad character (`xs.append(4)` was
  three errors, now one), and the fix-loop trial showed the first message is what gets used.

- **D21. `for` loops count with words: `until` and `through`, never `to` or `..`.** (2026-11-06)
  The list trial's most repeated pattern was the three-line `var i = 0` / `while i < length(xs)` /
  `i = i + 1`. `for x in xs`, `for i in 0 until n` (stops before `n`) and `for i in 1 through n`
  (includes `n`) replace it. Every other range syntax is ambiguous across the languages Claude
  knows: `to` is inclusive in Pascal, Lua and BASIC, `..` is exclusive in Rust and inclusive in
  Kotlin and Ruby, and `range(a, b)` hides its exclusiveness in convention. A word that says
  which is the whole point. `reversed` at the end of the line walks the same numbers or items
  backwards, so a countdown never needs its bounds rewritten (`range(n - 1, -1, -1)`, a classic
  off-by-one, gets the fix `for i in 0 through n - 1 reversed`). Only steps of 1: other steps
  are rare and `while` covers them. Bounds and the list are evaluated once, and the loop walks a
  snapshot of the list (D19), so changing the list inside its own loop is well defined. The loop
  variable can't be assigned (`i = i + 1` in a C-style body is an error, not a silent skip).
  The generated C never steps past a bound, so `through` up to the largest Int can't overflow.
  `break` and `continue` apply to the innermost loop; no labels. `range(...)`, `1 to n`,
  `0..n`, C-style headers and `for i, x in ...` each get a targeted fix.

- **D22. Structs: `struct Name` ... `end struct Name`, made with named fields, values like lists.**
  (2026-11-06)
  - *`struct`, not `record` or `class`.* In C, Go, Rust, Swift and C#, `struct` already means a
    plain aggregate copied by value, which is exactly the semantics here; `class` would promise
    methods, inheritance and shared references. `class`, `record`, `type`, `data` get the fix.
  - *Construction is a call, with D4's rule:* `Point(x: 1, y: 2)`, every field named, in order.
    Positional `Point(1, 2)` is the classic swapped-field bug. It's the form Swift and Kotlin use,
    and calling it a call means there's nothing new to learn; `Point { x: 1, y: 2 }` (Rust, Go)
    and `new Point(...)` get the rewritten call as their fix. No defaults: missing fields are
    named in the error, with the given ones filled in.
  - *Value semantics, the same as lists (D19):* a struct value is a `cl_list` with one slot per
    field, so sharing, copy-on-write and the over-counting rule all carry over unchanged. A
    million `c.n = c.n + i` updates run in place (0.07 s with 100k list-of-struct rewrites).
  - *`p.x = v` on a `var`.* At first only one level deep, like `xs[i] = v`; the struct trial
    showed that cost a fix round, so D23 allows any path.
  - *No methods.* Functions take the struct as a parameter, so there is one way to call
    anything; `p.area()` stays a `method-call` error.
  - A struct can contain itself only through a list (`children: List[Tree]`): with no null, a
    direct `next: Node` could never be made, so it's an error that suggests the list.
  - `print` shows `Point(x: 1, y: 2)`, the way one is made, so output reads back as code.
  - Brace habits recover: a line that is only `}` closes the innermost block, and the error
    names the right closer (`end struct Point`).

- **D23. Assignment goes through any path: `ps[i].score = v`, `grid[i][j] = v`, `a.b.c = v`.**
  (2026-11-07) D19 and D22 started with one level at a time and a three-line rewrite for deeper
  targets. The struct trial's only first-try failure, in both models, was `ps[i].score =
  ps[i].score + 5`, although SPEC named it as not allowed: the habit is strongest exactly where
  records are used most (a list of them), and the rewrite was the longest pattern in the spec.
  Value semantics are unchanged: the root must be a `var`, and the compiled code steps down the
  path making each level unique (copying it only if it's shared), so a copy taken earlier, at any
  level, keeps its old value. Order: the value first, then the indexes left to right, then the
  walk; so `t.kids = append(list: t.kids, item: t)` stores the old `t`, never a cycle.
  `p.items = append(list: p.items, item: x)` grows in place like a variable does (100k appends
  through `big[0].tags` run in well under a second). The next likely habit, `for p in ps` then
  `p.score = ...`, is an error that says `p` is a copy and gives the index loop.

- **D24. Enums with payloads, `Option[T]` and `Result[T, E]`, and `match`.** (2026-11-07; built.) The big trial's clearest signal: every one of 8 programs had a find
  function returning `-1` or `""` for "not found". That's C's idiom, and it's exactly the
  confident-but-wrong territory of point 5: nothing makes the caller check. D7 promised `Result`
  and exhaustive `match`; this is the concrete form.

  ```
  enum Command
    Go(dir: String)
    Take(item: String)
    Look
  end enum Command

  fn find(names: List[String], name: String) -> Option[Int]
    example find(names: ["a", "b"], name: "b") == Some(1)
    example find(names: ["a"], name: "z") == None
    for i in 0 until length(names)
      if names[i] == name
        return Some(i)
      end if
    end for
    return None
  end fn find

  match find(names: names, name: "Bob")
    case Some(i)
      print(i)
    case None
      print("no Bob")
  end match
  ```
  - *`enum`*, because it's what Rust, Swift and TypeScript call it and what Claude will reach for;
    `union`, `variant`, `data`, `type X = A | B` get the fix. A variant has named fields like a
    struct (`Go(dir: String)`) or none (`Look`). Variant names are global, like struct and
    function names (one name, one meaning; D5), so it's `Go(dir: "east")`, not `Command.Go`;
    `Command.Go`, `Command::Go` and `.go` get the fix. A bare variant is a value: `Look`.
  - *Construction follows D4:* one field may be positional (`Some(3)`, `Go("east")`), more must be
    named, in order.
  - *`Option[T]` (`Some(x)` / `None`) and `Result[T, E]` (`Ok(x)` / `Err(e)`) are built in,* the
    only generic enums (no user generics yet). `None` is Python's spelling too, so `return None`
    is already right. `Option` over `Maybe`/`Optional` because Rust's names are the ones that come
    with `Some`; `Optional[int]`, `Option<Int>`, `Maybe`, `Int?`, `T | None` get the fix. A `None`,
    `Ok` or `Err` needs its full type from context, like `[]`: an argument, a field, a `return`, a
    typed `var`.
  - *No null, and no implicit wrapping:* `return i` in a function returning `Option[Int]` is a
    type error with the fix `return Some(i)`. Kotlin and Swift would accept it, but the `Some`
    is what tells a reader the other branch exists. `null`, `nil`, `undefined` get "there's no
    null; a value that may be missing is `Option[T]`".
  - *Using an `Option` as its `T` is the key diagnostic:* `items[find(...)]`, `x + 1` with `x:
    Option[Int]`: "`x` is Option[Int], not Int; unpack it with `match`", with the `match` lines as
    the fix. `x.unwrap()`, `x!`, `x?`, `if let`, `if x is not None` each get a targeted message.
  - *`match` is a statement:* `match <expr>`, then `case <pattern>` lines, each followed by its
    body, then `end match` (D2). Python's `match`/`case` shape, which fits the line-based blocks.
    Arms never fall through and need no `break`; a `break` inside an arm applies to the enclosing
    loop (the C uses an `if` chain, never `switch`, so this can't go wrong). Patterns: a variant;
    a variant with bindings; `case _` (last, matches anything). Bindings: a variant with one field
    binds it positionally (`case Some(i)`); with more, a bare name must be a field's name and binds
    that field (`case Rect(w, h)`, in any order, so fields can't be swapped), and `field: name`
    renames (`case Rect(w: width, h: height)`). Bound names are read-only and new (D17), scoped to
    their arm.
  - *Exhaustive:* every variant needs a `case`, or there's a `case _`. A missing variant is an
    error naming it, with the missing `case` lines as the fix. A duplicate `case`, or one after
    `case _`, is unreachable and an error. `switch`, `when`, `default:`, `case X:` (colon),
    `=>` and `else` inside a `match` get fixes.
  - *`==` and `print`* work like structs: `Some(3) == Some(3)`; prints `Some(3)`, `None`,
    `Go(dir: "east")`, `Look`, so output reads back as code. `x == None` is allowed as a test, but
    using the value still needs `match`.
  - *C representation:* a `cl_list` again, so copy-on-write and sharing carry over unchanged:
    item 0 is the variant's tag, items 1.. its fields. `Option` is the same with tags 0/1.
    Descriptors: `E<n>` indexes a `cl_enums` table (variant names, field names, field
    descriptors), `O` + T for `Option`, `Q` + T + E for `Result`.
  - *Built so far:* enums can be recursive (`Add(left: Expr, right: Expr)`) since every value is
    built bottom-up and never changed in place, so no cycle can form. `case Move(a, b)` (positional
    names that aren't fields) is `unnamed-bind` with the renaming fix `case Move(dx: a, dy: b)`.
    A bound name returned from a function is shared, not moved, since it's borrowed from the
    matched value. `Option`/`Result` tags: `Some`/`Ok` 0, `None`/`Err` 1, value in item 1;
    descriptors `O`+T and `Q`+T+E (`cl_desc_skip` finds E). Habit fixes built: `return i` ->
    `return Some(i)` (and `Ok`/`Err` for a Result), `xs[i]`/`i + 1` with an Option -> the
    `match` lines, `x == 2` -> `Some(2)`, `null`/`nil`/`undefined`, `Optional[T]`/`Option<T>`,
    `if let`, `.unwrap()` and friends, `?`, `=>`, `switch`/`when` (parsed as `match`), `default:`,
    `is None`. `None` with no known type is `needs-type`, like `[]`.
  - *Not decided, waiting for trial data:* a one-line unpack (`if let`-style, a `guard`, a
    `value_or(option:, default:)`), `match` as an expression, `?` for `Result` (D7: it's concise
    but hides control flow), and literal patterns (`case "go"`, `case 0`) for Int and String.
    Plan: build enums and `match`, then `Option`/`Result`, then rerun the big trial and count
    sentinels and the lines each unpack costs.
  - *Trial result (2026-11-08, `--set big` rerun):* both models 4/4 first try, no compile errors.
    Sentinel functions went from 6 to 2 and `Option` find functions from 0 to 4. Of the two left,
    one is a lookup that can't miss (names known to be in the list, where `-1` still traps if
    wrong); the other is Sonnet's `indexOf` doing double duty as a must-find and a maybe-find
    (`if ni < 0`). An unpack costs 1-2 lines more than `if i < 0 ... else`, and no one got one
    wrong. None of the one-line forms is needed yet. The new pressure is **`match` to a value**:
    Sonnet wrote four `var s = ...` / `match` / `s = ...` arms / `return s` functions (~54 lines,
    turning an enum into a name or picking a field per room), although SPEC's own example returns
    from each arm. One model's style, so `match` expressions stay open.

- **D25. A `{` right before a string's closing quote is a literal brace.** (2026-11-08; built.)
  `"{"`, `"set {"`. The hidden-input trial's `balanced` task wrote `"{"` five times in one
  function (bracket tokens), and a rerun did it again after SPEC gained a sentence saying braces
  must be escaped: interpolation by default (D18) makes every `{` special, and Claude's habit from
  every other language is that `"{"` is just a brace. That position can't start an interpolation
  (there is nothing after it), so there's only one reading, and accepting it adds no ambiguity.
  Any other unclosed `{` (`"{x"`, likely a lost `}`) stays an error, now one per brace (it also
  used to report a false "no closing quote"), with the escaped string as the fix
  (`"\{x"`). `\{` still works everywhere; `print` shows braces escaped inside quoted strings
  (`["\{", "\}"]`) so output reads back as code. SPEC doesn't mention the rule: code that relies
  on it just works.

- **D26. claude-lang compiles to Lean 4, so the proved program is the one that runs.** (2026-11-08;
  decided, not built. Night 4 asked Ari: compile to Lean, or an error/automation layer over Claude
  writing Lean directly? Ari: "No opinion, make a judgement call.")
  - *What changes is the backend.* The front end (lexer, parser, checker, every diagnostic and
    habit fix) stays. Codegen emits Lean 4 instead of C, Lean's bundled toolchain builds the binary
    (`lean -c`, then `leanc`, its own clang), and `requires`/`ensures`/`invariant` become theorems
    about those same definitions. The compiler tries the automation itself (`omega`, `grind`,
    `simp`, `decide`, `vcgen` for loops) and reports what it couldn't prove at the claude-lang line,
    in claude-lang terms. Claude doesn't write Lean.
  - *Not an error layer over Lean-direct:* the baseline (night 4) found the main obstacle was
    core-vs-Mathlib names, and a 6-line note already fixes most of that, so a wrapper has little
    left to add. It would also leave claude-lang out of verification, and Lean code that isn't
    proved keeps the quiet defaults point 5 is about (`5 - 7 = 0` on Nat, `x / 0 = 0`, `xs[i]!`
    panics and carries on with `default`). That work isn't wasted: the escape hatch needs it (below).
  - *Not a Lean model beside the C backend:* then the proof is about a translation, and two
    backends can disagree. With one backend, a proved function is the function that runs. Lean's
    compiler and runtime are now trusted for running, as gcc was; the kernel still checks every proof.
  - *The fit is close* (spike: `trials/lean/backend_spike.lean`). Lean's runtime already does D19:
    values are refcounted and updated in place when unshared (1M `push` + 1M `set!` in 0.05 s at
    `-O1`). Structs map to `structure`, enums to `inductive`, `Option`/`Result` to `Option`/`Except`,
    `match` to `match`, `var` and `for` to `do` with `let mut` and `for`. Lean frees memory, which
    closes "nothing is freed". D16's traps are a `clTrap` that the kernel sees as `default` (since D34: as a value nothing is known
    about) and that
    at run time flushes stdout, prints `runtime error: ...` and exits 70, so a trap can't make a
    proof true, and a proof can show one is unreachable. Generated code never uses Lean's own
    `panic!`, which prints and then carries on with `default` (the spike printed "not reached").
  - *`Int` becomes unbounded* (Lean's `Int`, like Python's). Overflow can't happen, so D16's
    overflow trap goes away rather than catching it. Proofs get much easier: `omega` works on `Int`
    directly, while 64-bit arithmetic needs bit-blasting (`bv_decide`), which is weak on
    multiplication (`result * result <= n`). Lean keeps small ints unboxed, so the common case stays
    fast. Division by zero and bad indexes stay traps.
  - *Costs:* a build takes ~3-12 s on this box (lean, then leanc at `-O1`) instead of ~0.15 s.
    `example`s can run during elaboration (`#guard`), before the native step, so a failing example
    comes back in ~2 s. A Lean error in generated code is a compiler bug; the only Lean output a
    user sees is an unproved goal, mapped back. And rewriting the backend will take many nights.
  - *Plan, each stage useful alone:* (1) a Lean backend for Int/Bool/String, functions,
    `if`/`while`/`for`, `print` and examples, run beside C, with `tests/run.py` comparing output;
    (2) lists, structs, enums, `Option`/`Result`, `match`, with print formats identical to C's;
    (3) Lean becomes the default once every test passes, and C retires; (4) `requires`/`ensures`
    checked at run time, then proved by the automation, with `invariant` on loops; (5) the trial
    that answers Ari's sanity check: the Lean-direct baseline's tasks written in claude-lang with
    contracts, compared on success, fix rounds and how much Claude has to write.
  - *Status (2026-11-09, night 5): stages 1-3 done.* Every test and all 127 trial programs behave identically
    on both backends, and Lean is the default. C stays as `--backend c` for the trial harnesses' many builds
    (Lean ~7-10 s per program on this box, C ~0.2 s) and keeps 64-bit `Int`, so literals past 64 bits are an
    error there only. It retires when stage 4 needs every build on Lean.
  - *Escape hatch, open:* when the automation can't close a goal, the first hint is in claude-lang:
    a helper function whose `ensures` states the missing fact, which works as a lemma. A raw Lean
    `proof` block is the last resort, and that's where the name-table error layer goes.

- **D27. `/` and `%` are Euclidean: `%` is never negative.** (2026-11-09, night 5, while writing the Lean
  backend.) `a == b * (a / b) + a % b` with `0 <= a % b < |b|`; for a positive divisor that's Python's `//`
  and `%` (`-7 / 2` is `-4`, `-7 % 2` is `1`). Before this the spec said C's rule (truncate toward zero, `%`
  takes the left side's sign). Reasons:
  - *It removes two quiet bugs* (point 5) that truncation keeps: `n % 2 == 1` is false for negative odd `n`,
    and `(i - 1) % n` to wrap an index gives `-1` at `i == 0`. Claude writes both, from Python habits.
  - *It's Lean's own `/` and `%`* (D26), which `omega` reasons about directly. Truncating division
    (`Int.tdiv`) needs a rewrite lemma first (measured: `omega` fails on `x.tdiv 2 <= x` given `x >= 0`, and
    proves the same goal for `/`), so contracts on code that divides would need more help.
  - It differs from floor division (Python) only for a negative divisor, which is rare: `7 / -2` is `-3`
    and `7 % -2` is `1` (Python: `-4`, `-1`). Division by zero still stops the program (D16).
  - The C backend follows it (a two-line fix after C's `/`), so both backends agree while D26 is underway.
    No test or trial depended on the old rule.

- **D28. A recursive function is a total `def` when the compiler can find why it stops, else `partial`.**
  (2026-11-10, night 6; built.) Only a total `def` can be proved about (D26 stage 4): Lean treats
  a `partial def` as an opaque constant, so no contract on it, or on its callers, can be proved through it.
  - *Lean can't find measures over `Int` by itself.* Its search (GuessLex) tries only `sizeOf` of each
    parameter, which never decreases for `n - 1` on an `Int`. Structural recursion (enums like `Expr`) it
    does find. So clc proposes the candidates: for each `Int` parameter `p`, `p.toNat` and `p.natAbs`; for
    each pair, `(q - p + 1).toNat` (counting up to a bound), with `length` of a list parameter as a bound
    too; plain `def` first when a parameter is a struct, enum or list.
  - *The proof is a fixed tactic:* `simp_wf`, then `omega`, else `grind` with a prelude lemma bounding
    `clMod a b m` by `|b|` (gcd) and `clDiv` unfolded (literal divisors, e.g. binary search's
    `(lo + hi) / 2`); for a recursive struct, a generated `sizeOf r.field < sizeOf r` lemma plus Lean's own
    membership hypothesis from `for x in r.field`.
  - *Choosing needs a separate Lean run.* A command that tries each candidate and keeps the first that
    checks needs a custom elaborator, which needs `import Lean`: measured at 40-60 s per build on this box
    (vs ~1.4 s with only `Init`). So when a program has recursion, clc elaborates a probe file first: the
    program's types and functions, plus every candidate under its own name, and reads `#print axioms` for
    each (a failed proof leaves `sorryAx`). The real file uses the first candidate that checked, or
    `partial`. Programs without recursion skip the probe.
  - *A function that may not stop stays runnable.* `partial` is the honest answer for `f(n)` with base case
    `n == 0` (negative `n` never stops), and the probe gets it right (measured). It matters once the
    function has a contract: then clc can say the proof needs a reason it stops.
  - *Only plausible candidates*, since each failed proof costs ~0.2 s: a measure on `p` needs a comparison of
    `p` in the body (its base case) and a call passing it something smaller; `q - p` needs a comparison of the
    two; `natAbs` needs an argument made with `%` or `/`. That took the test file's ten groups from 39
    candidates (8 s CPU) to 12 (3 s), with the same results.
  - *Results are cached* by the probe's text (`~/.cache/clc/probe/`), so a rebuild of unchanged functions
    and types costs nothing extra.
  - *Recursion is rare in what Claude writes:* 6 of the 127 trial programs. D28 gets 5 of their 8 groups total
    and is right about 2 of the 3 partial ones. Loops are the common case, so they matter more for stage 4.
  - *Not yet:* lexicographic measures (Ackermann), mutual recursion beyond structural or one shared `Int`
    parameter, a sign flip (`f(-n)` for negative `n`), recursion inside a `while` body. Those stay `partial`.

- **D29. Contracts: `requires` and `ensures` lines beside the examples, checked at run time.** (2026-11-10,
  night 6; built. Stage 4(b) of D26; proving them is 4(c).)
  - *Syntax:* `requires <Bool>` over the parameters, `ensures <Bool>` over the parameters and `result`, between
    the `fn` line and the body in any order with `example`s; no io. `result` is a name only inside `ensures`
    (a parameter can't be called `result` there), so the many programs with a `var result` keep working.
    `ensures` on a function that returns nothing is an error: parameters can't change, so there's nothing to
    say. `main` can't have contracts.
  - *A broken `requires` is the caller's mistake, so it's reported at the call:* `file:15:11: runtime error:
    this call breaks `requires n >= 0` of fn down (line 14): down(n: -1)`, with every argument's value. In
    Lean, a function with a `requires` takes the caller's location as a first argument, and each `requires`
    wraps the body, `if cond then <body> else trap`. One check per call, in one place, and inside the body
    the condition is a hypothesis: a termination proof can use it (`down(n)` with base case `n == 0` is
    `partial` alone and total with `requires n >= 0`), and so will stage 4(c)'s proofs.
  - *A broken `ensures` is the function's mistake, so it's reported at the `return` that broke it:*
    `bad_abs(x: -7) returned -7, which breaks `ensures result >= 0` (line 23)`. Each `return e` becomes
    `let cl_result := e`, a check per `ensures`, `return cl_result`.
  - *Examples go through the same calls,* so an example that breaks a `requires` is `example-crashed` with
    that message. (Found while testing: on Lean, an example that stopped the program was blamed on the one
    before it, with no message, because `#eval` captures output and evaluated the example's values before
    printing `EXRUN`. Examples are now thunks and `EXRUN` and trap messages go straight to the real
    stdout/stderr.)
  - *C backend:* refuses contracts (exit 3, "drop `--backend c`"), since C is only kept for the trial
    harnesses' fast builds and retires with stage 4.
  - *Not yet:* contracts that call back into their own function's group (Unsupported), loop `invariant`s,
    `old(...)`-style state (nothing is mutable across a call, so not needed yet), long argument values in
    messages aren't shortened.

- **D30. Each `ensures` is a theorem the compiler tries to prove; an unproved one is a warning.** (2026-11-10,
  night 6; built: the first proofs, stage 4(c) of D26.)
  - *The statement:* for a pure function that D28 made total, each `ensures` becomes `theorem clSpec_f_j
    (params) (one hypothesis per requires) : ensures[result := f(params)]`. The function body still contains
    its run-time checks, so the proof has to show that no check can fail, which is the claim itself.
  - *The proof is fixed automation, never Claude's job:* `first | (fun_induction f args <;> grind [...]) |
    (unfold f; grind [...]) | sorry`, induction only for recursive functions, with D28's `clMod_bound` and
    `clDiv` as hints. Probe (night 6): `unfold; grind` proves clamp's `lo <= result and result <= hi` and a
    struct-field `ensures`; `fun_induction ... <;> grind [clDiv]` proves `count_digits(n) >= 1` and
    `down(n) == 0` for every `n >= 0`. `unfold; simp_all; split; omega` failed where grind worked.
  - *A fallback keeps it to one Lean run.* A failed tactic is an error, but the last alternative always closes
    the goal (first `sorry`, now a per-theorem axiom, D31), so an unprovable `ensures` doesn't stop the build,
    and `#print axioms` says what each theorem leans on. (D28 can't do this: a fallback there would make any
    measure "work".)
  - *An unproved `ensures` is a warning, not an error,* because it's still checked at run time: `unproved` at
    the `ensures` line, with the reason: a `while`/`for` loop (not provable yet), a function D28 left
    `partial`, io, or "the automation didn't find a proof" (which includes a false `ensures` that no example
    reaches, like `wrong_abs` returning `x` for `x < -5`). `clc test` ends with "N of M `ensures` proved".
  - *What the automation needed, found by writing reference answers for a proof trial (2026-11-12, night 8):
    three of six correct answers didn't prove, and the invariants weren't at fault.*
    (1) **A value written twice must be one term.** `xs[i]`, `a / b`, `a % b` and a call to a function with a
    `requires` each carry the place they were written, for the trap's message, so `xs[i]` in the body and
    `xs[result]` in the `ensures` were different terms to `grind`, and so were `fib_spec(i)` in an invariant
    and `fib_spec(n)` in the `ensures`. A place is no part of any value (a trap is the same thing to the kernel
    whatever it would print), so now a place is the term `clAt line col`, which the kernel takes to be `""`
    and the running program computes as `file:line:col` (`implemented_by`, the same device as `clTrap`; a
    place only ever reaches a trap's message). One rule, `clAt line col = ""`, which `grind` always has,
    makes every place the same, and congruence does the rest for every helper and every user function at
    once. A first version (rewrite rules per helper, `clGet xs i loc = clGetV xs i`) lasted an hour: it
    didn't cover user functions.
    (2) **A proof must not depend on how long the file's path is.** With places as string literals holding
    the path, `grind` ran out of recursion depth on the fib proof when the file sat under a 100-character
    directory, and proved it when the path was short. `clAt` takes the path out of every term (it is in one
    constant, `clFile`), so that can't happen again. Compiled, `clAt 6 10` is a closed term that Lean
    computes once: a 3M-pass loop with an index in it runs as fast as before.
    (3) **`grind` doesn't split an `and` that is false.** The check on a function's way out is `not (a and
    b)`, and from that alone `grind` learned nothing about `a` or `b`, so a two-part `ensures` was proved
    only when each part was already known letter for letter (isqrt's is, which is why it passed). One
    library lemma in the hints, `Bool.and_eq_false_iff`, makes the split.
    (4) **A contract that calls a function needs that function's definition.** `ensures result ==
    fib_spec(n)` can only be proved by opening `fib_spec`. So the functions a function's contract lines
    call (`requires`, `ensures`, `invariant`, `decreases`), and those they call, are handed to `grind` to
    unfold (`spec_fns`), when they are pure and total. A callee in the body is not opened: it speaks
    through its own `ensures` (D31). With (1) to (4), an iterative `fib` is proved equal to the recursive
    `fib_spec` from `invariant a == fib_spec(i) and b == fib_spec(i + 1)`. Also `clDiv a b m = a / b` is a
    rule now, in place of unfolding `clDiv` (since D34 only for a divisor that isn't 0).
    (5) **What `%` is, not only its bounds.** A proof knew `0 <= a % b < b` and nothing else, so it couldn't
    use `m % 10 == m` below 10 or `m == 10 * (m / 10) + m % 10`. The rule `clMod a b m = a % b` (first with 0 for a zero divisor;
    since D34 only for a divisor that isn't 0) gives `grind` Lean's `%` to reason with. This one a model found, not a reference answer: Haiku's
    digit-sum loop (`while m > 0`, where mine stopped at `m >= 10` and so never needed it) was right and
    went unproved through two fix rounds.
  - *Not yet:* call-site proofs of `requires` (D31), loops (`invariant`), a heartbeat limit for a slow
    `grind` (a timeout would be an error, not a `sorry`). Counterexamples for a false `ensures` came with D32.

- **D31. Proofs are modular: a function's proved `ensures` is a fact at every call; an unproved one is an
  assumption that's named.** (2026-11-10, night 6; built.)
  - *Callers use callees' contracts, not their bodies:* each spec theorem gets `grind_pattern clSpec_g_j =>
    f_g args`, so any later `grind` that sees a call to `g` gets `g`'s `ensures` (when `g`'s `requires` holds
    there). Without it `grind` picks the whole `decide (...)` conclusion as the trigger, which no caller
    contains (measured: `digits_plus(n) = count_digits(n) + 1 >= 2` failed, and proves with it).
  - *An unproved `ensures` is closed by its own axiom,* `clUnproved_f_j` (the same statement), instead of
    `sorry`. Then `#print axioms` names exactly which unproved contracts a proof leans on, and clc reports
    three outcomes: proved; "it follows from fn g's `ensures ...` (line N), which isn't proved" (only other
    functions' axioms); or not proved (its own axiom). Both unproved kinds are `unproved` warnings and count
    as unproved in "N of M proved", since a false assumption proves anything.
  - *Not yet:* proving each call's `requires`. In this model a trap is just some value to the kernel (D34), so "this call
    never breaks `requires`" isn't a statement about results; it needs either one theorem per call site with
    the path condition, or a model where traps are visible (an `Except`-style result). Until then a callee's
    `requires` is still checked at run time, and a caller's proof can only use the callee's `ensures` where
    it can show the `requires` itself.

- **D32. An unproved `ensures` is tested on small inputs at build time; a counterexample is an error.**
  (2026-11-11, night 7; built.) "Unproved" used to cover two different things, a true `ensures` the
  automation can't reach (every loop, today) and a false one, and only the second is a bug.
  - *What runs:* for each pure function with an unproved `ensures`, clc calls it on every combination of small
    values of its parameters that the `requires` allow, smallest first: Ints 0, 1, -1, ... to ±16, then a few
    usual edges (99, 100, 101, 255, 256, ±1000, ...); lists up to four items long; structs and enums from their
    fields' values; `Option`/`Result` around those. Up to 3000 distinct calls or 1.5 s per function.
  - *The function's own literals are inputs too,* since that's where its branches are: each Int literal `c`
    in the function (and in the functions it calls) goes in as `c`, `c - 1` and `c + 1`, the ones compared
    with something first (`income < 40000`), one literal per depth, up to 12 of them and none above 100000
    (a loop to 1000000007 would only time out); each String literal goes in as it is (`cmd == "north"`).
    Without them `tax(income: 40000) returns 0`, a forgotten boundary, is out of reach; with them it's found
    at depth 1.
  - *The function's own run-time checks are the judge* (D29), so the search file is the program as it runs,
    plus the loops. Three findings:
    - `ensures-false` (error): `` `ensures result >= 0` is false: wrong_abs(x: -6) returns -6 ``.
    - `input-crashed` (error): the call stops the program, e.g. `largest(xs: [])` on `xs[0]`, or
      `digits_twice(n: -1)` breaking a callee's `requires`, or recursion that never ends. The contract claims
      a result for every input the `requires` allow, so the fix is usually a missing `requires`. This is also
      a first, tested stand-in for proving each call's `requires` (D31's "not yet").
    - `input-timeout` (warning): one call used 2 s of CPU. Slow isn't wrong, so the build goes on.
  - *Errors, not warnings,* for the same reason a false `example` is (D8): it's a concrete input on which the
    program contradicts what its author wrote. The message gives the call and the value, which is what a fix
    needs (principle 4). With no finding, the `unproved` warning says how many calls were tried.
  - *A separate Lean run, only when something is unproved,* cached by its text (`~/.cache/clc/search/`). A
    stopped program ends the run, so a finding costs one more run for the functions after it (callers of the
    function with the finding are skipped: they'd stop at the same place); at most five findings per build.
    Measured here: ~1.2 s CPU per run, 3000 calls in 0.2-0.3 s.
  - *Two hazards met on the way:* endless non-tail recursion grows Lean's interpreter stack by ~100 MB a
    second, so the search runs with a 16 MB stack (`lean -s`), where it's "deep recursion" within a second;
    and an endless loop is told from a swapping machine by CPU time, not wall time.
  - *Limits:* it only finds counterexamples made of small values and the program's literals: a boundary the
    code computes (`limit * 2`) rather than writes is missed. Lists longer than four items aren't tried. Io functions and functions with no unproved `ensures` aren't searched (a function with no
    contract at all could be searched for crashes too; not decided).
  - *Examples got the stack limit too:* the main run uses a 64 MB stack, so an `example` that recurses
    without end is `example-crashed` ("its recursion got too deep") in seconds, where it used to grow until
    the 120 s timeout. 64 MB holds between 10000 and 100000 calls inside each other (measured: 16 MB holds
    10000, 256 MB holds 100000), more than an example needs; the built program has no such limit.

- **D33. A loop is proved as it stands, with Lean's verification-condition generator, from `invariant` and
  `decreases` lines.** (2026-11-11, night 7; decided after two probes, then built: the front end, and the
  proofs for `while` and `for` loops that aren't nested and have no `break`.)
  - *The lines:* `invariant <Bool>` and `decreases <Int>` at the top of a loop's body, like `requires` and
    `ensures` at the top of a function's. An invariant holds every time the loop is about to test its
    condition: on entry, after each pass, and when it ends. Several lines mean all of them. A `while` needs
    one `decreases`: an Int that is never negative there and gets smaller on every pass, which is why the
    loop stops. A `for` needs none. In `for i in a until b`, `i` in an invariant is the next index, so
    when the loop ends it is `b` (or `a`, if the range was empty).
  - *The route: nothing that runs changes.* The loop stays the `do` loop clc emits today, and the function's
    `ensures` theorem is proved by `mvcgen` (Std.Do), which turns the function, the invariant and the
    variant into separate goals (holds on entry; kept by a pass, and the measure drops; gives the `ensures`
    at the end), each closed by one fixed tactic (`mleave`, a `simp only` with list and range lengths,
    `grind`). If any goal fails the theorem falls back to its `clUnproved` axiom exactly as in D31, so
    reporting doesn't change. Probe (`trials/lean/loops_mvcgen.lean`): isqrt (`while`, nonlinear
    `ensures`), triangle numbers and a list builder (range `for`), gcd (two loop variables), and a search
    loop with an early `return` are all proved on the functions as emitted now, 4.9 s CPU together.
  - *The other route, tried first:* each loop as a recursive function over its variables, with a loop
    theorem by `fun_induction <;> grind` (`trials/lean/loops.lean`). It also proved everything tried, runs
    as fast, and uses only what D28 and D30 use. It lost because clc would have to translate loops into
    recursion itself, with `break`, `continue`, early `return` and nesting each handled by hand, which is a
    second way to emit every loop and a new place for the program that runs to drift from the one written.
    With `mvcgen` there is nothing new to trust: a wrong invariant term can only make a proof fail.
  - *What clc writes for a loop:* the state is the tuple of the `var`s the loop assigns, in the order they
    were declared, read with projections (`cl_s.1`), not tuple patterns, which get stuck when the state is
    an unknown. `while`: a variant `fun s => (decreases).toNat` and an invariant with two cases, during
    (the invariant) and after (the invariant and not the condition). Range `for`: one invariant over a
    cursor into the range's list, with `i := start + prefix.length`. A `return` inside a loop adds an
    `Option` to the state, and the invariant adds "the `ensures` holds for the value returned". It also
    has to say that **while the loop runs, nothing has been returned yet** (night 8): for a `while`, "none
    returned, and the invariant" during and the two-case form only after; for a `for`, "none returned, or
    nothing is left to visit" (as an `or`: with "returned implies nothing left", `grind` would have had to
    take the `Option` apart, and doesn't). Without that a pass couldn't use the invariant from the pass
    before, since the invariant only speaks when nothing was returned. The night-7 probe missed it because
    its one loop with a `return` needed no invariant. Binary search found it.
  - *What it needed:* two lemmas about a range's list (the item after a prefix is the start plus the
    prefix's length, and lies inside the range) with explicit `grind_pattern`s; `clMod_pos` (`0 <= a % b <
    b` for `b > 0`); unfolding `clTrap` before `grind`, so the long messages are gone (this is what let
    loop proofs see a trap's value, which was `default` then: D34). `import
    Std.Tactic.Do` costs ~0.3 s CPU, and only files with a loop to prove need it.
  - *A function's `requires` are hypotheses of every goal,* so `invariant` lines don't have to repeat them
    (the recursive route would have needed that).
  - *Risk taken knowingly:* in Lean 4.35 `mvcgen` is marked deprecated in favour of `vcgen`, which is marked
    experimental, lives in another library and doesn't work as a drop-in. This project pins its Lean, so it
    matters only on an upgrade, and the terms clc writes come from one place.
  - *Corrected on the way:* NOTES said Lean's `while` is `partial` inside. In 4.35 it isn't (`Loop.forIn` is
    `repeatM`, with invariant and variant rules), which is what makes this route possible.
  - *The front end's rules:* the lines come first in the loop's body, in any order; anywhere else is
    `contract-placement`, with the right word offered when the wrong one is used (`ensures` in a loop,
    `invariant` on a function). They see what's in scope where the loop starts, plus the variable of a
    range `for`; not the item of `for x in xs` (`invariant-item`: there is no item once the loop is over;
    the fix is an index loop), and no io. `decreases` on a `for` is `decreases-for`, a second one
    `duplicate-decreases`. `assert` gets a hint pointing at all three words. The C backend refuses a
    program with these lines, as it does contracts.
  - *What's built (`loop_plan` in `cl_lean.py`):* a function with loops gets the `mvcgen` script instead of
    D30's `unfold; grind` when every loop is one clc can state: not nested, no `break`, not `reversed`, a
    `decreases` on each `while`, a range or list made from parameters, and `invariant`/`decreases` lines
    that mention only parameters, the variables the loop assigns, and fixed `let`s (next point).
    Otherwise the `unproved` warning names the loop and the obstacle (`the while on line 96 has no
    decreases line, so clc can't show that it stops`). When the script runs and fails, it says the
    invariant may not hold at the start, may not be kept, or may not be enough; and when a loop has no
    `invariant` at all, it says that instead. First results: isqrt, triangle numbers, gcd, a counting loop
    over a list and a search loop with a `return` inside are proved in the tests; a loop whose invariant
    is true but not kept by a pass (`c <= length(xs)`, counting matches) correctly stays unproved.
  - *Fixed `let`s (2026-11-12, night 8):* where `mvcgen` asks for an invariant, only the theorem's own
    variables (the parameters) are in scope, so a term can't name a local. But a `let` from before the
    loop whose value is made from the parameters alone, maybe through other such `let`s, means the same
    thing everywhere in the function, so clc restates it at the front of each term that needs it (`let v_n
    : Int := Int.ofNat v_xs.size; ...`) and `grind` sees the same expression on both sides. That covers
    `let n = length(xs)` before a loop, the commonest case, in `invariant` and `decreases` lines, a `for`'s
    range and a `while`'s condition. Which `let` a name means is read from the loop's own scope, since two
    branches may each have a `let goal`. A wrong restatement could only make a proof fail. Still out: a
    local that depends on a `var` or on an earlier loop's result (`let m = t` after a loop that counts
    `t`); the warning names the variable and says why. That one needs the invariant to be stated where the
    earlier loop's final state is in scope, which `mvcgen`'s `inv` goals don't offer.
  - *First trial (2026-11-12, night 8, `trials/prove.py`):* given only SPEC.md and a function's contract,
    Haiku wrote loops with invariants that clc proved for 7 of 7 functions on its first answer (multiply
    by adding, divide by subtracting, count evens, find an index, and `fib`, `sum` and `power` each against a
    recursive definition). On the compiler as it was a day earlier the same answers proved 2 of 7: the
    gaps were in the automation (D30's night-8 point), not in the invariants. A harder set (binary
    search, gcd, factorial and digit sum against definitions, reversing a list, index of the largest
    item, `is_sorted` against a definition): 5 of 7 on the first answer and `is_sorted` after one fix
    (its invariant was false for an empty list, and Haiku found that from the generic message). The
    seventh, digit sum, was a correct answer clc couldn't prove (D30 night-8 point, 5); with that fixed,
    its first answer proves, so 6 of 7 first answers. (Graded again after D34 closed a hole in loop
    proofs: the same numbers.)
  - *The warning says which part failed (2026-11-13, night 9).* An invariant has three jobs: be true when
    the loop starts, be kept by a pass, and say enough once the loop is over. The warning used to list all
    three as possibilities, and in two fix rounds Haiku answered it by adding true but useless `invariant`
    lines. Now each loop's invariant is wrapped in a mark, `clInv k (...)`, which means just the invariant
    (the closing tactic unfolds it). A goal that tactic can't close is printed (`trace_state`) and closed
    by the theorem's own gap axiom, `clGap_f_j : ∀ p, p`, so the other goals are still tried, `#print
    axioms` still shows the theorem isn't proved, and a caller that leans on it is reported as in D31. clc
    reads each printed goal: the mark of loop k in what's to be shown and not in what's known is that
    loop's start; in both, a pass; only in what's known, the `ensures` after that loop. The warning names
    the loop and the part: "clc couldn't show that `invariant c == i and c >= 1` is true when the `for` on
    line 11 starts", "that a pass of the `while` on line 23 keeps `invariant m >= 0` true and makes
    `decreases n - m` smaller while it stays at 0 or above", "that this `ensures` follows from what is true
    when the `for` on line 36 ends" (`tests/ok/loop-gaps.cl` has one function per case). Not split yet:
    which of a pass's jobs failed (the invariant, the `decreases`, a value returned inside the loop), and
    which line when a loop has several.
    *Tried first and dropped:* a small custom tactic that reads the open goal's name and writes it to
    stderr, so the theorem could keep falling back to its plain `clUnproved` axiom. It worked, but it needs
    `import Lean.Elab.Tactic.Basic`, the tactic is then compiled into the program, and a statically linked
    binary went from 4.5 MB to 118 MB (840 MB to link). Goal names alone (`vc3.step`,
    `vc4.isTrue.post.success.pre`) wouldn't have been enough either: a `step` goal's name doesn't say
    which loop it belongs to.
  - *Not yet decided or tried:* a run-time check of each invariant (wanted: then D32's search can show a
    false one with its input; it must not be an early `return`, which would change the loop's shape for the
    proof); a run-time check that `decreases` goes down, so an unproved loop can't hang; `break` (the state
    at a `break` isn't "the invariant and not the condition"); nested loops; `for x in xs` (the invariant
    can't name what has been seen so far; an index loop can); `reversed`; a recursive function with a loop.

- **D34. To a proof, a trap is a value nothing is known about.** (2026-11-13, night 9; built. It closes a
  hole through which a false `ensures` was reported proved.)
  - *The hole:* every function with an `ensures` ends in "if the `ensures` doesn't hold for the result,
    trap". The theorem is about what the function returns, so on that branch it asks whether the `ensures`
    holds for the trap's value. To the kernel a trap was `default` (0, false, "", an empty list), meant as
    "nothing a proof can use". But D33's closing tactic unfolds `clTrap` to shed the long messages, and
    after that `grind` knows the value. So in a function with a loop, an `ensures` that 0 satisfies was
    proved whatever the loop did: `ensures result >= 0` on a loop that counts down from 0, with the true
    and useless `invariant t <= 0`, came out proved. Then the small-input search (D32), which only looks at
    unproved ones, never ran, and the program stopped at run time with nothing said at build time.
    Functions without loops never had it: their proofs don't unfold `clTrap` (checked on last night's
    compiler with a plain and a recursive function).
  - *The fix:* `opaque clTrapVal : α`, and `clTrap msg := clTrapVal`. Unfolding still sheds the message;
    what is left is a constant with no definition. A proof that the `ensures` holds for it would be a
    proof for any value, and then the check couldn't have failed.
  - *What "proved" means,* said once: for every input the `requires` allow, if the function returns, what
    it returns meets the `ensures`. A path that traps on the way (a bad index, `/` by zero) carries an
    unknown value onward, so in practice such a function is proved only when the proof shows that path
    can't happen, which a `requires` usually says.
  - *`/` and `%`:* the rules `clDiv a b m = a / b` and `clMod a b m = a % b` now ask for `b ≠ 0`. Before,
    `%` by zero was "0, which is what a trap is worth". Every proof in the tests still goes through: the
    divisors there are literals, or a loop's condition says they aren't 0.
  - *How it was found:* by an accident of the good kind. The night's message work (D33) put a mark on each
    invariant; for a loop with no invariant the goal became `clInv 1 True`, which the tactic's `simp`
    closes, and the `grind` after it then failed for want of a goal. Mending that (`<;>` for `;`) made a
    function with no invariant come out proved, which can't be right. So the old tactic had been failing
    on such goals for the wrong reason, and that failure had hidden the hole in the commonest case, a
    loop with no invariant at all.
  - *Tests:* `tests/err/loop-trap-value.cl` has three false `ensures` (no invariant; a useless one; a
    `while` returning Bool, where `false` was the free value). Last night's compiler reports one of them;
    this one reports all three, as `ensures-false` with the input.
  - *What it changes in earlier results: nothing, as it turned out.* Two of the proof trial's fourteen
    tasks have an `ensures` that 0 satisfies (`count_evens`: `result >= 0 and result <= length(xs)`;
    `max_index`: `result >= 0 and result < length(xs)`), so on those the old compiler would have passed
    any loop at all, and the trial measured nothing there. Graded again with this compiler
    (`trials/results/2026-11-13-11*`): the reference answers 14 of 14; Haiku's first answers 7 of 7 on
    the first set and 6 of 7 on the harder one, as before. Its invariants do carry those two proofs. Every
    proof in the tests still goes through as well.
  - *A control in the proof trial (night 9, step 2).* "14 of 14 proved" says nothing if clc would also
    have proved a wrong loop, and on two tasks it would have. So each task now carries one wrong loop,
    with its slip in words (stops one pass early; `r > b` for `r >= b`; counts each even number twice;
    returns the value one ahead; and so on), whose `ensures` is false for some input, and
    `trials/prove.py --control` builds them: none may come out proved. This compiler: 14 of 14 caught,
    each with an input that breaks it. Night 8's compiler: 12 of 14; it calls the wrong `count_evens`
    and the wrong `max_index` proved, the two tasks named above
    (`trials/results/2026-11-13-12*-control*`). Run it, and `--reference`, after any change to how loops
    are proved.
  - *Looked at while there: an unproved `ensures` that is false somewhere.* It is still a fact to its
    callers' proofs (D31), and from a false fact Lean proves anything. With `ensures x < 1000000` on a
    function `far`, unproved and false only for inputs the search never tries, Lean does prove `ensures
    result == 7` for a function that returns 3 and only mentions `far(2000000)`: in a branch it never
    takes, or in an `invariant`, which isn't run. This is not a hole, because such a proof was never
    counted as proved: one that leans on another function's unproved `ensures` is reported as "it
    follows from fn far's ..., which isn't proved", keeps its warning and its run-time check, and is
    searched like any unproved one. But no test had a false one. `tests/err/assumed-callee.cl` does;
    with that rule switched off in a copy of the compiler, both functions come out proved.

## Open questions

- Memory management: value semantics with copy-on-write (D19); nothing is freed yet.
- Generics: built-in only so far (`List`, and with D24 `Option` and `Result`). User generics wait
  until a trial wants them.
- Mutation: immutable by default with `var` for mutable locals? Leaning yes.
- Modules/imports: explicit, file = module, no wildcards. Details later.
- Effects in signatures (D-to-be): e.g. `fn main() uses io`. Valuable for point 6, cost unknown.
- **Contracts and formal verification** (Ari asked 2026-11-07: "does it fit?"; then: "we
  definitely want proofs, not just fuzzing"). Likely a good fit: the annotations that make
  verification tedious for people (pre/postconditions, loop invariants) are cheap for Claude
  (point 3), and value semantics, no global state and effects in signatures remove the aliasing
  and heap reasoning that make verifiers hard. It targets point 5 directly. Plan:
  (a) `requires` / `ensures` lines beside `example`, checked at runtime (D29); (b) at build time, run
  each function on many small inputs that satisfy `requires` and report the first that breaks
  `ensures`, which is the concrete counterexample a point-4 diagnostic needs (D32); (c) **proofs, the
  goal**, with `invariant` lines on loops; they would also prove D16's traps can't fire. (b) is a
  stepping stone and the counterexample finder, not a substitute for (c).
  Backend for (c): **decided in D26, Lean 4, with claude-lang compiled to Lean.** The notes that
  led there:
  - *Lean 4 core* (no Mathlib). v4.35.0 is a 594 MB download, 3.0 GB unpacked (fine on disk), and
    ships `grind` (SMT-style), `omega` (linear integer arithmetic) and `bv_decide` (bit-vectors
    via the bundled CaDiCaL, i.e. 64-bit overflow). Proofs are checked by Lean's kernel, so they
    mean something even if our translation's automation is buggy; the trusted part shrinks to the
    translation itself. Claude knows Lean far better than any proof syntax we'd invent. Measured
    2026-11-07 (`trials/lean/`): a file with `omega`, `grind`, `bv_decide` and an induction proof
    checks in 3.2 s warm (10 s cold) using ~55 MB of anonymous memory; the other ~580 MB of RSS is
    mmapped `.olean` files, which the kernel drops instead of swapping. So it fits the box. Core
    also has `mvcgen` (Hoare-style VC generation for `do` code with `for` loops and `let mut`), the
    same shape as our plan; a sum-loop proof written from memory worked first try, but 4.35 says
    `mvcgen` is deprecated in favour of `vcgen`: point 1's name churn, live. Mathlib is what's too
    heavy (~5 GB of oleans and GBs of RAM to import).
    Ari's sanity check: "is this buying Claude anything over just writing in Lean directly?" For
    claude-lang: everything fits in the prompt (Lean's names churn), Claude states facts and the
    tool finds the steps (Lean tactics are written watching the goal state), and no quiet
    defaults (`5 - 7 = 0` on Nat, `x / 0 = 0`, `xs[i]!` panics and continues with `default`).
    For Lean: maturity, proofs about the program that runs (ours would be about a translation),
    and `mvcgen` closing the gap. Settle it with a Lean-direct baseline trial before building.
    *Baseline result (2026-11-08, `trials/leanbase.py`):* six small write-and-prove tasks (isqrt,
    insertion sort sorted + permutation, tax and parking monotone, ...): Haiku and Sonnet each proved
    5/6 unaided; both failures were Mathlib names in core (`split_ifs`, `Nat.strong_induction_on`)
    that Lean's errors don't correct. With a 6-line name note, both proved everything. So at this
    scale Lean-direct works, and claude-lang's case narrows to diagnostics, a stable spec, and
    automation that needs no written proof. Compiling claude-lang to Lean is worth weighing.
  - *Z3* (apt `z3` 4.8.12, small): our own verification-condition generator, Dafny-style.
    Automatic and gives counterexamples, but the generator is trusted and nonlinear facts
    (`result * result <= n`) are weak.
  Either way Claude writes contracts and invariants in claude-lang, the compiler generates the
  proof obligations and tries automation, and a failure names the unproved line in claude-lang
  terms. Caveat: verification moves trust from the body to the spec, and a misread task gets a
  matching wrong `ensures`; the gain is a two-line contract to check instead of a long body. The
  wrong-but-compiles trial measures that.

  ```
  fn isqrt(n: Int) -> Int
    requires n >= 0
    ensures result * result <= n
    ensures (result + 1) * (result + 1) > n
    example isqrt(n: 10) == 3
  ```

## Sketch of what code might look like (not final)

```
fn gcd(a: Int, b: Int) -> Int
  example gcd(a: 12, b: 18) == 6
  example gcd(a: 7, b: 0) == 7
  if b == 0
    return a
  end if
  return gcd(a: b, b: a % b)
end fn gcd

fn main() uses io
  print(gcd(a: 48, b: 36))
end fn main
```
