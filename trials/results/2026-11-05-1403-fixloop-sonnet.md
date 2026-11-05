# Fix-loop trial 2026-11-05-1403 (sonnet)

| case | full | brief |
|---|---|---|
| arg-order | fixed | fixed |
| unnamed | fixed | fixed |
| lost-end-if | fixed | fixed |
| ampersands | fixed | fixed |
| shadowing | fixed | fixed |
| not-int | fixed | fixed |
| missing-io | fixed | fixed |
| let-not-var | fixed | fixed |
| elif | fixed | fixed |
| off-by-one | fixed | fixed |
| no-ret-type | fixed | fixed |

## arg-order

Broken program (base `gcd`):
```cl
fn gcd(a: Int, b: Int) -> Int
  example gcd(a: 12, b: 18) == 6
  example gcd(a: 7, b: 0) == 7
  if b == 0
    return a
  end if
  return gcd(a: b, b: a % b)
end fn gcd

fn main() uses io
  print(gcd(b: 36, a: 48))
end fn main
```
Full compiler output:
```
prog.cl:11:9: error[arg-order]: arguments must come in the order `fn gcd` declares them (a, b)
   11 |   print(gcd(b: 36, a: 48))
      |         ^^^
  fix: `gcd(a: 48, b: 36)`
1 error(s), 0 warning(s)
```

### full: fixed

```cl
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

### brief: fixed

```cl
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

## unnamed

Broken program (base `gcd`):
```cl
fn gcd(a: Int, b: Int) -> Int
  example gcd(a: 12, b: 18) == 6
  example gcd(a: 7, b: 0) == 7
  if b == 0
    return a
  end if
  return gcd(a: b, b: a % b)
end fn gcd

fn main() uses io
  print(gcd(48, 36))
end fn main
```
Full compiler output:
```
prog.cl:11:9: error[unnamed-arg]: `gcd` takes more than one argument, so each one must be named
   11 |   print(gcd(48, 36))
      |         ^^^
  fix: `gcd(a: 48, b: 36)`
1 error(s), 0 warning(s)
```

### full: fixed

```cl
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

### brief: fixed

```cl
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

## lost-end-if

Broken program (base `divsum`):
```cl
fn divisor_sum(n: Int) -> Int
  example divisor_sum(6) == 6
  example divisor_sum(12) == 16
  var total = 0
  var i = 1
  while i < n
    if n % i == 0
      total = total + i
    i = i + 1
  end while
  return total
end fn divisor_sum

fn is_perfect(n: Int) -> Bool
  example is_perfect(6)
  return divisor_sum(n) == n
end fn is_perfect

fn main() uses io
  print(is_perfect(28))
  print(is_perfect(12))
  print(divisor_sum(100))
end fn main
```
Full compiler output:
```
prog.cl:10:3: error[closer-mismatch]: `end while` doesn't match the innermost open block, `if` (line 7)
   10 |   end while
      |   ^^^^^^^^^
  fix: add `end if` above this line
1 error(s), 0 warning(s)
```

### full: fixed

```cl
fn divisor_sum(n: Int) -> Int
  example divisor_sum(6) == 6
  example divisor_sum(12) == 16
  var total = 0
  var i = 1
  while i < n
    if n % i == 0
      total = total + i
    end if
    i = i + 1
  end while
  return total
end fn divisor_sum

fn is_perfect(n: Int) -> Bool
  example is_perfect(6)
  return divisor_sum(n) == n
end fn is_perfect

fn main() uses io
  print(is_perfect(28))
  print(is_perfect(12))
  print(divisor_sum(100))
end fn main
```

### brief: fixed

```cl
fn divisor_sum(n: Int) -> Int
  example divisor_sum(6) == 6
  example divisor_sum(12) == 16
  var total = 0
  var i = 1
  while i < n
    if n % i == 0
      total = total + i
    end if
    i = i + 1
  end while
  return total
end fn divisor_sum

fn is_perfect(n: Int) -> Bool
  example is_perfect(6)
  return divisor_sum(n) == n
end fn is_perfect

fn main() uses io
  print(is_perfect(28))
  print(is_perfect(12))
  print(divisor_sum(100))
end fn main
```

## ampersands

Broken program (base `divsum`):
```cl
fn divisor_sum(n: Int) -> Int
  example divisor_sum(6) == 6
  example divisor_sum(12) == 16
  var total = 0
  var i = 1
  while i < n
    if n % i == 0
      total = total + i
    end if
    i = i + 1
  end while
  return total
end fn divisor_sum

fn is_perfect(n: Int) -> Bool
  example is_perfect(6)
  return n > 1 && divisor_sum(n) == n
end fn is_perfect

fn main() uses io
  print(is_perfect(28))
  print(is_perfect(12))
  print(divisor_sum(100))
end fn main
```
Full compiler output:
```
prog.cl:17:16: error[bad-char]: `&&` isn't an operator here; write `and`
   17 |   return n > 1 && divisor_sum(n) == n
      |                ^^
1 error(s), 0 warning(s)
```

### full: fixed

```cl
fn divisor_sum(n: Int) -> Int
  example divisor_sum(6) == 6
  example divisor_sum(12) == 16
  var total = 0
  var i = 1
  while i < n
    if n % i == 0
      total = total + i
    end if
    i = i + 1
  end while
  return total
end fn divisor_sum

fn is_perfect(n: Int) -> Bool
  example is_perfect(6)
  return n > 1 and divisor_sum(n) == n
end fn is_perfect

fn main() uses io
  print(is_perfect(28))
  print(is_perfect(12))
  print(divisor_sum(100))
end fn main
```

### brief: fixed

```cl
fn divisor_sum(n: Int) -> Int
  example divisor_sum(6) == 6
  example divisor_sum(12) == 16
  var total = 0
  var i = 1
  while i < n
    if n % i == 0
      total = total + i
    end if
    i = i + 1
  end while
  return total
end fn divisor_sum

fn is_perfect(n: Int) -> Bool
  example is_perfect(6)
  return n > 1 and divisor_sum(n) == n
end fn is_perfect

fn main() uses io
  print(is_perfect(28))
  print(is_perfect(12))
  print(divisor_sum(100))
end fn main
```

## shadowing

Broken program (base `divsum`):
```cl
fn divisor_sum(n: Int) -> Int
  example divisor_sum(6) == 6
  example divisor_sum(12) == 16
  var total = 0
  var i = 1
  while i < n
    if n % i == 0
      total = total + i
    end if
    i = i + 1
  end while
  return total
end fn divisor_sum

fn is_perfect(n: Int) -> Bool
  example is_perfect(6)
  let total = divisor_sum(n)
  let total = total - n
  return total == 0
end fn is_perfect

fn main() uses io
  print(is_perfect(28))
  print(is_perfect(12))
  print(divisor_sum(100))
end fn main
```
Full compiler output:
```
prog.cl:18:7: error[duplicate-name]: `total` is already defined on line 17; a name means one thing within a function
   18 |   let total = total - n
      |       ^^^^^
  fix: pick a new name, or declare it with `var` on line 17 and assign `total = ...`
1 error(s), 0 warning(s)
```

### full: fixed

```cl
fn divisor_sum(n: Int) -> Int
  example divisor_sum(6) == 6
  example divisor_sum(12) == 16
  var total = 0
  var i = 1
  while i < n
    if n % i == 0
      total = total + i
    end if
    i = i + 1
  end while
  return total
end fn divisor_sum

fn is_perfect(n: Int) -> Bool
  example is_perfect(6)
  let total = divisor_sum(n)
  let difference = total - n
  return difference == 0
end fn is_perfect

fn main() uses io
  print(is_perfect(28))
  print(is_perfect(12))
  print(divisor_sum(100))
end fn main
```

### brief: fixed

```cl
fn divisor_sum(n: Int) -> Int
  example divisor_sum(6) == 6
  example divisor_sum(12) == 16
  var total = 0
  var i = 1
  while i < n
    if n % i == 0
      total = total + i
    end if
    i = i + 1
  end while
  return total
end fn divisor_sum

fn is_perfect(n: Int) -> Bool
  example is_perfect(6)
  let total = divisor_sum(n)
  let extra = total - n
  return extra == 0
end fn is_perfect

fn main() uses io
  print(is_perfect(28))
  print(is_perfect(12))
  print(divisor_sum(100))
end fn main
```

## not-int

Broken program (base `divsum`):
```cl
fn divisor_sum(n: Int) -> Int
  example divisor_sum(6) == 6
  example divisor_sum(12) == 16
  var total = 0
  var i = 1
  while i < n
    if not (n % i)
      total = total + i
    end if
    i = i + 1
  end while
  return total
end fn divisor_sum

fn is_perfect(n: Int) -> Bool
  example is_perfect(6)
  return divisor_sum(n) == n
end fn is_perfect

fn main() uses io
  print(is_perfect(28))
  print(is_perfect(12))
  print(divisor_sum(100))
end fn main
```
Full compiler output:
```
prog.cl:7:12: error[type-mismatch]: `not` needs Bool, but `(n % i)` is Int
    7 |     if not (n % i)
      |            ^^^^^^^
1 error(s), 0 warning(s)
```

### full: fixed

```cl
fn divisor_sum(n: Int) -> Int
  example divisor_sum(6) == 6
  example divisor_sum(12) == 16
  var total = 0
  var i = 1
  while i < n
    if n % i == 0
      total = total + i
    end if
    i = i + 1
  end while
  return total
end fn divisor_sum

fn is_perfect(n: Int) -> Bool
  example is_perfect(6)
  return divisor_sum(n) == n
end fn is_perfect

fn main() uses io
  print(is_perfect(28))
  print(is_perfect(12))
  print(divisor_sum(100))
end fn main
```

### brief: fixed

```cl
fn divisor_sum(n: Int) -> Int
  example divisor_sum(6) == 6
  example divisor_sum(12) == 16
  var total = 0
  var i = 1
  while i < n
    if n % i == 0
      total = total + i
    end if
    i = i + 1
  end while
  return total
end fn divisor_sum

fn is_perfect(n: Int) -> Bool
  example is_perfect(6)
  return divisor_sum(n) == n
end fn is_perfect

fn main() uses io
  print(is_perfect(28))
  print(is_perfect(12))
  print(divisor_sum(100))
end fn main
```

## missing-io

Broken program (base `countdown`):
```cl
fn countdown(n: Int)
  var i = n
  while i >= 1
    print(i)
    i = i - 1
  end while
end fn countdown

fn main() uses io
  countdown(5)
  print(0)
end fn main
```
Full compiler output:
```
prog.cl:4:5: error[missing-effect]: `print` uses io, so `fn countdown` must declare `uses io` too
    4 |     print(i)
      |     ^^^^^
  fix: `fn countdown(n: Int) uses io`
1 error(s), 0 warning(s)
```

### full: fixed

```cl
fn countdown(n: Int) uses io
  var i = n
  while i >= 1
    print(i)
    i = i - 1
  end while
end fn countdown

fn main() uses io
  countdown(5)
  print(0)
end fn main
```

### brief: fixed

```cl
fn countdown(n: Int) uses io
  var i = n
  while i >= 1
    print(i)
    i = i - 1
  end while
end fn countdown

fn main() uses io
  countdown(5)
  print(0)
end fn main
```

## let-not-var

Broken program (base `countdown`):
```cl
fn countdown(n: Int) uses io
  let i = n
  while i >= 1
    print(i)
    i = i - 1
  end while
end fn countdown

fn main() uses io
  countdown(5)
  print(0)
end fn main
```
Full compiler output:
```
prog.cl:5:5: error[assign-to-let]: `i` was declared with `let` (line 2), so it can't change
    5 |     i = i - 1
      |     ^
  fix: declare it with `var i = ...` on line 2
1 error(s), 0 warning(s)
```

### full: fixed

```cl
fn countdown(n: Int) uses io
  var i = n
  while i >= 1
    print(i)
    i = i - 1
  end while
end fn countdown

fn main() uses io
  countdown(5)
  print(0)
end fn main
```

### brief: fixed

```cl
fn countdown(n: Int) uses io
  var i = n
  while i >= 1
    print(i)
    i = i - 1
  end while
end fn countdown

fn main() uses io
  countdown(5)
  print(0)
end fn main
```

## elif

Broken program (base `basics`):
```cl
fn factorial(n: Int) -> Int
  example factorial(0) == 1
  example factorial(5) == 120
  var result = 1
  var i = 2
  while i <= n
    result = result * i
    i = i + 1
  end while
  return result
end fn factorial

fn sign(x: Int) -> Int
  example sign(-4) == -1
  example sign(0) == 0
  if x < 0
    return -1
  elif x == 0
    return 0
  else
    return 1
  end if
end fn sign

fn is_even(n: Int) -> Bool
  example is_even(4)
  example not is_even(7)
  return n % 2 == 0
end fn is_even

fn main() uses io
  print(factorial(10))
  print(sign(-7))
  print(is_even(10) and not is_even(3))
end fn main
```
Full compiler output:
```
prog.cl:18:3: error[syntax]: `elif` isn't a keyword; write `else if`
   18 |   elif x == 0
      |   ^^^^
prog.cl:19:5: warning[unreachable]: this line can never run: it comes after a `return`
   19 |     return 0
      |     ^^^^^^
1 error(s), 1 warning(s)
```

### full: fixed

```cl
fn factorial(n: Int) -> Int
  example factorial(0) == 1
  example factorial(5) == 120
  var result = 1
  var i = 2
  while i <= n
    result = result * i
    i = i + 1
  end while
  return result
end fn factorial

fn sign(x: Int) -> Int
  example sign(-4) == -1
  example sign(0) == 0
  if x < 0
    return -1
  else if x == 0
    return 0
  else
    return 1
  end if
end fn sign

fn is_even(n: Int) -> Bool
  example is_even(4)
  example not is_even(7)
  return n % 2 == 0
end fn is_even

fn main() uses io
  print(factorial(10))
  print(sign(-7))
  print(is_even(10) and not is_even(3))
end fn main
```

### brief: fixed

```cl
fn factorial(n: Int) -> Int
  example factorial(0) == 1
  example factorial(5) == 120
  var result = 1
  var i = 2
  while i <= n
    result = result * i
    i = i + 1
  end while
  return result
end fn factorial

fn sign(x: Int) -> Int
  example sign(-4) == -1
  example sign(0) == 0
  if x < 0
    return -1
  else if x == 0
    return 0
  else
    return 1
  end if
end fn sign

fn is_even(n: Int) -> Bool
  example is_even(4)
  example not is_even(7)
  return n % 2 == 0
end fn is_even

fn main() uses io
  print(factorial(10))
  print(sign(-7))
  print(is_even(10) and not is_even(3))
end fn main
```

## off-by-one

Broken program (base `basics`):
```cl
fn factorial(n: Int) -> Int
  example factorial(0) == 1
  example factorial(5) == 120
  var result = 1
  var i = 2
  while i < n
    result = result * i
    i = i + 1
  end while
  return result
end fn factorial

fn sign(x: Int) -> Int
  example sign(-4) == -1
  example sign(0) == 0
  if x < 0
    return -1
  else if x == 0
    return 0
  else
    return 1
  end if
end fn sign

fn is_even(n: Int) -> Bool
  example is_even(4)
  example not is_even(7)
  return n % 2 == 0
end fn is_even

fn main() uses io
  print(factorial(10))
  print(sign(-7))
  print(is_even(10) and not is_even(3))
end fn main
```
Full compiler output:
```
prog.cl:3:3: error[example-failed]: example is false: `factorial(5)` is 24, expected 120
    3 |   example factorial(5) == 120
      |   ^^^^^^^
1 error(s), 0 warning(s)
```

### full: fixed

```cl
fn factorial(n: Int) -> Int
  example factorial(0) == 1
  example factorial(5) == 120
  var result = 1
  var i = 2
  while i <= n
    result = result * i
    i = i + 1
  end while
  return result
end fn factorial

fn sign(x: Int) -> Int
  example sign(-4) == -1
  example sign(0) == 0
  if x < 0
    return -1
  else if x == 0
    return 0
  else
    return 1
  end if
end fn sign

fn is_even(n: Int) -> Bool
  example is_even(4)
  example not is_even(7)
  return n % 2 == 0
end fn is_even

fn main() uses io
  print(factorial(10))
  print(sign(-7))
  print(is_even(10) and not is_even(3))
end fn main
```

### brief: fixed

```cl
fn factorial(n: Int) -> Int
  example factorial(0) == 1
  example factorial(5) == 120
  var result = 1
  var i = 2
  while i <= n
    result = result * i
    i = i + 1
  end while
  return result
end fn factorial

fn sign(x: Int) -> Int
  example sign(-4) == -1
  example sign(0) == 0
  if x < 0
    return -1
  else if x == 0
    return 0
  else
    return 1
  end if
end fn sign

fn is_even(n: Int) -> Bool
  example is_even(4)
  example not is_even(7)
  return n % 2 == 0
end fn is_even

fn main() uses io
  print(factorial(10))
  print(sign(-7))
  print(is_even(10) and not is_even(3))
end fn main
```

## no-ret-type

Broken program (base `basics`):
```cl
fn factorial(n: Int) -> Int
  example factorial(0) == 1
  example factorial(5) == 120
  var result = 1
  var i = 2
  while i <= n
    result = result * i
    i = i + 1
  end while
  return result
end fn factorial

fn sign(x: Int) -> Int
  example sign(-4) == -1
  example sign(0) == 0
  if x < 0
    return -1
  else if x == 0
    return 0
  else
    return 1
  end if
end fn sign

fn is_even(n: Int)
  example is_even(4)
  example not is_even(7)
  return n % 2 == 0
end fn is_even

fn main() uses io
  print(factorial(10))
  print(sign(-7))
  print(is_even(10) and not is_even(3))
end fn main
```
Full compiler output:
```
prog.cl:26:11: error[not-bool]: an example must be a Bool expression, usually `f(...) == expected`
   26 |   example is_even(4)
      |           ^^^^^^^^^^
prog.cl:27:15: error[type-mismatch]: `not` needs Bool, but `is_even(7)` is Unit
   27 |   example not is_even(7)
      |               ^^^^^^^^^^
prog.cl:28:3: error[unexpected-return-value]: `fn is_even` has no return type, so `return` takes no value
   28 |   return n % 2 == 0
      |   ^^^^^^
  fix: add `-> Bool` to the signature, or write plain `return`
prog.cl:34:9: error[type-mismatch]: `and` needs Bool, but `is_even(10)` is Unit
   34 |   print(is_even(10) and not is_even(3))
      |         ^^^^^^^^^^^
prog.cl:34:29: error[type-mismatch]: `not` needs Bool, but `is_even(3)` is Unit
   34 |   print(is_even(10) and not is_even(3))
      |                             ^^^^^^^^^^
5 error(s), 0 warning(s)
```

### full: fixed

```cl
fn factorial(n: Int) -> Int
  example factorial(0) == 1
  example factorial(5) == 120
  var result = 1
  var i = 2
  while i <= n
    result = result * i
    i = i + 1
  end while
  return result
end fn factorial

fn sign(x: Int) -> Int
  example sign(-4) == -1
  example sign(0) == 0
  if x < 0
    return -1
  else if x == 0
    return 0
  else
    return 1
  end if
end fn sign

fn is_even(n: Int) -> Bool
  example is_even(4)
  example not is_even(7)
  return n % 2 == 0
end fn is_even

fn main() uses io
  print(factorial(10))
  print(sign(-7))
  print(is_even(10) and not is_even(3))
end fn main
```

### brief: fixed

```cl
fn factorial(n: Int) -> Int
  example factorial(0) == 1
  example factorial(5) == 120
  var result = 1
  var i = 2
  while i <= n
    result = result * i
    i = i + 1
  end while
  return result
end fn factorial

fn sign(x: Int) -> Int
  example sign(-4) == -1
  example sign(0) == 0
  if x < 0
    return -1
  else if x == 0
    return 0
  else
    return 1
  end if
end fn sign

fn is_even(n: Int) -> Bool
  example is_even(4)
  example not is_even(7)
  return n % 2 == 0
end fn is_even

fn main() uses io
  print(factorial(10))
  print(sign(-7))
  print(is_even(10) and not is_even(3))
end fn main
```
