# claude-lang spec (v0)

This is the whole language. It is new, so don't assume features from other languages: if
something isn't described here, it doesn't exist yet.

## Programs

A program is one `.cl` file of functions. It starts at `fn main()`. Comments start with `#` and
run to the end of the line.

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

## Lines and blocks

- **One statement per line.** No `;`, no line continuation. Indentation is not significant
  (use two spaces per level by convention).
- **Blocks have no braces and no `:`.** A block starts with its keyword line and ends with a
  closer that names it: `end if`, `end while`, `end fn <name>` (repeating the function's name).

## Types

| Type | Values |
|---|---|
| `Int` | 64-bit signed integer, e.g. `0`, `42`, `1_000_000`. Negative: `-5` |
| `Bool` | `true`, `false` |

There are no other types yet: no strings, floats, lists, null. Nothing converts implicitly
(an `Int` is never used as a `Bool`).

## Functions

```
fn name(param: Type, other: Type) -> ReturnType uses io
  example ...
  body
end fn name
```

- Every parameter has a type. `-> ReturnType` is left out if the function returns nothing.
- `uses io` is required if the function calls `print`, or calls any function that `uses io`.
  Leave it out otherwise.
- A function with a return type must `return` a value on every path.
- Functions can be declared in any order and can be recursive. They can't be nested.
- **`example` lines** go right after the `fn` line, before the body. Each is a `Bool`
  expression, usually `f(...) == expected`. The compiler runs every example on every build, and
  a false one is a compile error. Examples can't see parameters or call `uses io` functions;
  write the values out.

## Calls

- **With more than one argument, every argument is named, in the order the function declares
  them:** `gcd(a: 48, b: 36)`. Names use `:`, not `=`.
- With exactly one argument, naming is optional: `factorial(5)` or `factorial(n: 5)`.
- A call whose result isn't used is an error, unless the function returns nothing. Discard a
  result on purpose with `let _ = f(x)`.

## Statements

| Statement | Meaning |
|---|---|
| `let x = expr` | constant; can't be reassigned. Optional type: `let x: Int = 5` |
| `var x = expr` | variable; reassign with `x = expr` (same type) |
| `x = expr` | assignment, only to a `var` |
| `return expr` / `return` | leave the function (with a value if it has a return type) |
| `if` / `else if` / `else` / `end if` | conditions must be `Bool` |
| `while cond` ... `end while` | loop. There is no `for`, `break` or `continue` yet |
| `f(args)` | call a function for its effect |
| `print(x)` | built in: prints an `Int` or `Bool` and a newline; needs `uses io` |

```
fn sign(x: Int) -> Int
  if x < 0
    return -1
  else if x == 0
    return 0
  else
    return 1
  end if
end fn sign
```

A name can't be reused inside a function: no shadowing, and no redeclaring in an inner block.
A variable declared inside a block is visible only in that block.

## Expressions

| Operators | Operands -> result |
|---|---|
| `+ - * / %` | `Int` -> `Int`. `/` truncates toward zero; `%` has the sign of the left side |
| `< <= > >=` | `Int` -> `Bool` |
| `== !=` | two values of the same type -> `Bool` |
| `and or not` | `Bool` -> `Bool` (short-circuit) |
| `-x` | negation |

Precedence, loosest to tightest: `and`/`or`, comparisons, `+ -`, `* / %`, unary `-`/`not`.
`+ -` and `* / %` group left to right. Parentheses are **required** where readings commonly
differ:

- mixing `and` with `or`: write `(a and b) or c`;
- chained comparisons: `a < b < c` is an error, write `a < b and b < c`;
- `/` or `%` followed by `*`, `/` or `%`: write `(a / b) * c`;
- `not` in front of a comparison or arithmetic: write `not (a == b)`.

## Errors

The compiler reports every error at once as `file:line:col: error[code]: message`, with the
source line and usually a `fix:` line. At run time, integer overflow and division by zero stop
the program with `file:line:col: runtime error: ...` (exit code 70).

## Running

```
python3 clc.py run prog.cl     # build and run
python3 clc.py check prog.cl   # errors only
python3 clc.py test prog.cl    # build and run the examples
```
