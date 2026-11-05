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

## Open questions

- Memory management: leaning value semantics + refcounting (D18). Confirm before lists.
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
