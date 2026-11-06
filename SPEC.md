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
  print("gcd = {gcd(a: 48, b: 36)}")
end fn main
```

## Lines and blocks

- **One statement per line.** No `;`, no line continuation. Indentation is not significant
  (use two spaces per level by convention).
- **Blocks have no braces and no `:`.** A block starts with its keyword line and ends with a
  closer that names it: `end if`, `end while`, `end for`, `end fn <name>` (repeating the
  function's name).

## Types

| Type | Values |
|---|---|
| `Int` | 64-bit signed integer, e.g. `0`, `42`, `1_000_000`. Negative: `-5` |
| `Bool` | `true`, `false` |
| `String` | text in double quotes, e.g. `"Hello, {name}!"` |
| `List[T]` | a list of `T`s, e.g. `[1, 2, 3]` is `List[Int]`; `List[List[String]]` nests |

There are no other types yet: no floats, records, maps, null. Nothing converts implicitly
(an `Int` is never used as a `Bool`).

## Strings

- Double quotes only, and a string ends on the line it starts. Escapes: `\n` `\t` `\\` `\"`
  `\{` `\}`.
- **Interpolation:** `{expr}` inside a string inserts the value of any expression:
  `"{a} + {b} = {a + b}"`. A string literal can't appear inside `{...}`; put it in a
  `let` first.
- **There is no string `+`.** Join strings with interpolation: `"{first}{second}"`. To build a
  string in a loop: `line = "{line} {x}"`.
- `==` and `!=` compare strings; `length(s)` counts characters. There are no other string
  operations yet (no indexing or slicing).

## Lists

- `[a, b, c]` makes a list; every item has the same type. An empty list needs its type
  written: `var xs: List[Int] = []`.
- `xs[i]` is the item at index `i`, **counting from 0**; the last is `xs[length(xs) - 1]`.
  There's no negative indexing. An index out of range stops the program.
- `length(xs)` is the number of items.
- `append(list: xs, item: x)` **returns a new list** with `x` added; it doesn't change `xs`.
  To grow a variable: `xs = append(list: xs, item: x)` (this is fast).
- `repeat(item: 0, times: n)` is a list of `n` copies of `0`.
- `xs[i] = x` changes one item of a `var` list. Only one level at a time: for a list of lists,
  `var row = grid[i]`, `row[j] = x`, `grid[i] = row`.
- **Lists are values, like `Int`s:** `var ys = xs` copies, so changing `ys` never changes
  `xs`, and a function can't change a list it's given. (Copies are made only when needed.)
- `==` compares items; `print` and `{xs}` show `[1, 2, 3]` (strings inside are quoted).
- There are no methods (`xs.append`) and no `+` on lists.

```
fn total(xs: List[Int]) -> Int
  example total([1, 2, 3]) == 6
  example total([]) == 0
  var sum = 0
  for x in xs
    sum = sum + x
  end for
  return sum
end fn total

fn main() uses io
  var xs: List[Int] = []
  xs = append(list: xs, item: 4)
  xs = append(list: xs, item: 5)
  print("{xs} has total {total(xs)}")
end fn main
```

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
  write the values out. Calls in examples name their arguments like any other call.

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
| `while cond` ... `end while` | loop while `cond` is true |
| `for x in xs` ... `end for` | once per item of the list `xs`, in order |
| `for i in 0 until n` ... `end for` | `i` = 0, 1, ..., n - 1 (`until` stops before the end) |
| `for i in 1 through n` ... `end for` | `i` = 1, 2, ..., n (`through` includes the end) |
| `break` / `continue` | leave the innermost loop / skip to its next round |
| `f(args)` | call a function for its effect |
| `xs[i] = expr` | change one item of a `var` list |
| `print(x)` | built in: prints any value and a newline; needs `uses io` |

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

`for` loops count up by 1. Add `reversed` at the end of the line to go the other way:
`for i in 0 until n reversed` is n - 1 down to 0; `for x in xs reversed` is last to first.
The bounds and the list are evaluated once, before the loop starts. The loop variable can't be
assigned (use `while` for other steps), and a range whose start is past its end runs 0 times.

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
source line and usually a `fix:` line. At run time, integer overflow, division by zero and a list index out of
range stop the program with `file:line:col: runtime error: ...` (exit code 70).

## Running

```
python3 clc.py run prog.cl     # build and run
python3 clc.py check prog.cl   # errors only
python3 clc.py test prog.cl    # build and run the examples
```
