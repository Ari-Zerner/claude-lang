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
  - *`xs[i] = v` only one level deep* for now; `grid[i][j] = v` gets the three-line rewrite.
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

## Open questions

- Memory management: value semantics with copy-on-write (D19); nothing is freed yet.
- Generics: needed for `Result` and `List` at least. Built-in generic types only at first?
- Mutation: immutable by default with `var` for mutable locals? Leaning yes.
- Modules/imports: explicit, file = module, no wildcards. Details later.
- Effects in signatures (D-to-be): e.g. `fn main() uses io`. Valuable for point 6, cost unknown.

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
