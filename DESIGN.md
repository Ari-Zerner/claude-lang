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
  when debugging. (Possible later: self-host, or emit something else directly.)
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
  stop the program with `file:line:col: runtime error: ...` (exit code 70).
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
  (a) `requires` / `ensures` lines beside `example`, checked at runtime; (b) at build time, run
  each function on many small inputs that satisfy `requires` and report the first that breaks
  `ensures`, which is the concrete counterexample a point-4 diagnostic needs; (c) **proofs, the
  goal**, with `invariant` lines on loops; they would also prove D16's traps can't fire. (b) is a
  stepping stone and the counterexample finder, not a substitute for (c).
  Backend for (c), *open*:
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
