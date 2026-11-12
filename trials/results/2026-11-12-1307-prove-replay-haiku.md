# Proof trial 2026-11-12-1307 (replay-haiku)

| task | result |
|---|---|
| mul | proved, first try |
| divide | not proved (last: unproved) |
| count_evens | proved, first try |
| find_index | not proved (last: unproved) |
| fib | not proved (last: unproved) |
| sum | not proved (last: unproved) |
| power | not proved (last: unproved) |

First answers from `trials/results/2026-11-12-1303-prove-haiku.md`, graded again with the compiler as it was at commit b1e2a71 (night 8 step 1, before that night's prover fixes).

## mul

Task: Multiply by adding `a` to a running total `b` times.

```cl
fn mul(a: Int, b: Int) -> Int
  requires b >= 0
  ensures result == a * b
  example mul(a: 3, b: 4) == 12
```

### attempt 1: proved

```cl
fn mul(a: Int, b: Int) -> Int
  requires b >= 0
  ensures result == a * b
  example mul(a: 3, b: 4) == 12
  var total = 0
  var i = 0
  while i < b
    invariant i >= 0 and i <= b and total == a * i
    decreases b - i
    total = total + a
    i = i + 1
  end while
  return total
end fn mul
```

## divide

Task: Whole-number division by repeated subtraction: how many times `b` fits into `a`.

```cl
fn divide(a: Int, b: Int) -> Int
  requires a >= 0 and b > 0
  ensures result * b <= a and a < (result + 1) * b
  example divide(a: 17, b: 5) == 3
```

### attempt 1: unproved

```cl
fn divide(a: Int, b: Int) -> Int
  requires a >= 0 and b > 0
  ensures result * b <= a and a < (result + 1) * b
  example divide(a: 17, b: 5) == 3
  var q = 0
  var r = a
  while r >= b
    invariant q >= 0 and r >= 0 and q * b + r == a
    decreases r
    r = r - b
    q = q + 1
  end while
  return q
end fn divide
```

Compiler:
```
prog.cl:3:3: warning[unproved]: `ensures result * b <= a and a < (result + 1) * b` isn't proved: clc couldn't prove it from the `invariant` lines: either one doesn't hold when its loop starts, or a pass of the loop doesn't keep it, or a `decreases` doesn't get smaller, or together they aren't enough for this `ensures`; clc called it on 930 small inputs and none broke it. It's still checked at run time
    3 |   ensures result * b <= a and a < (result + 1) * b
      |   ^^^^^^^
0 error(s), 1 warning(s)
```

## count_evens

Task: Count the even numbers in the list.

```cl
fn count_evens(xs: List[Int]) -> Int
  ensures result >= 0 and result <= length(xs)
  example count_evens([1, 2, 4]) == 2
```

### attempt 1: proved

```cl
fn count_evens(xs: List[Int]) -> Int
  ensures result >= 0 and result <= length(xs)
  example count_evens([1, 2, 4]) == 2
  var count = 0
  for i in 0 until length(xs)
    invariant count >= 0 and count <= i and i <= length(xs)
    if xs[i] % 2 == 0
      count = count + 1
    end if
  end for
  return count
end fn count_evens
```

## find_index

Task: Return the index of the first item equal to `want`, or -1 when there is none.

```cl
fn find_index(xs: List[Int], want: Int) -> Int
  ensures result == -1 or (result >= 0 and result < length(xs) and xs[result] == want)
  example find_index(xs: [4, 5, 6], want: 6) == 2
  example find_index(xs: [4, 5, 6], want: 7) == -1
```

### attempt 1: unproved

```cl
fn find_index(xs: List[Int], want: Int) -> Int
  ensures result == -1 or (result >= 0 and result < length(xs) and xs[result] == want)
  example find_index(xs: [4, 5, 6], want: 6) == 2
  example find_index(xs: [4, 5, 6], want: 7) == -1
  var found = -1
  for i in 0 until length(xs)
    invariant found == -1 or (found >= 0 and found < i and xs[found] == want)
    if found == -1 and xs[i] == want
      found = i
    end if
  end for
  return found
end fn find_index
```

Compiler:
```
prog.cl:2:3: warning[unproved]: `ensures result == -1 or (result >= 0 and result < length(xs) and xs[result] == want)` isn't proved: clc couldn't prove it from the `invariant` lines: either one doesn't hold when its loop starts, or a pass of the loop doesn't keep it, or a `decreases` doesn't get smaller, or together they aren't enough for this `ensures`; clc called it on 3000 small inputs and none broke it. It's still checked at run time
    2 |   ensures result == -1 or (result >= 0 and result < length(xs) and xs[result] == want)
      |   ^^^^^^^
0 error(s), 1 warning(s)
```

## fib

Task: Compute the n-th Fibonacci number with a loop that keeps two running values. `fib_spec` below is the definition it must agree with; it is far too slow to call from the body.

```cl
fn fib_spec(n: Int) -> Int
  requires n >= 0
  if n < 2
    return n
  end if
  return fib_spec(n - 1) + fib_spec(n - 2)
end fn fib_spec
fn fib(n: Int) -> Int
  requires n >= 0
  ensures result == fib_spec(n)
  example fib(10) == 55
```

### attempt 1: unproved

```cl
fn fib(n: Int) -> Int
  requires n >= 0
  ensures result == fib_spec(n)
  example fib(10) == 55
  var a = 0
  var b = 1
  for i in 0 until n
    invariant a == fib_spec(i) and b == fib_spec(i + 1)
    var t = a + b
    a = b
    b = t
  end for
  return a
end fn fib
```

Compiler:
```
prog.cl:9:4: warning[input-timeout]: fib(n: 55) was still running after 2 s of computing, when clc called fn fib on small inputs to check its `ensures`
    9 | fn fib(n: Int) -> Int
      |    ^^^
  fix: if it never stops, fix that or add a `requires` that rules this call out
prog.cl:11:3: warning[unproved]: `ensures result == fib_spec(n)` isn't proved: clc couldn't prove it from the `invariant` lines: either one doesn't hold when its loop starts, or a pass of the loop doesn't keep it, or a `decreases` doesn't get smaller, or together they aren't enough for this `ensures`. It's still checked at run time
   11 |   ensures result == fib_spec(n)
      |   ^^^^^^^
0 error(s), 2 warning(s)
```

## sum

Task: Add up the items of the list. `sum_spec(xs, n)` below, the sum of the first n items, is the definition it must agree with.

```cl
fn sum_spec(xs: List[Int], n: Int) -> Int
  requires n >= 0 and n <= length(xs)
  if n == 0
    return 0
  end if
  return sum_spec(xs: xs, n: n - 1) + xs[n - 1]
end fn sum_spec
fn sum(xs: List[Int]) -> Int
  ensures result == sum_spec(xs: xs, n: length(xs))
  example sum([1, 2, 3]) == 6
```

### attempt 1: unproved

```cl
fn sum(xs: List[Int]) -> Int
  ensures result == sum_spec(xs: xs, n: length(xs))
  example sum([1, 2, 3]) == 6
  var total = 0
  for i in 0 until length(xs)
    invariant i >= 0 and i <= length(xs) and total == sum_spec(xs: xs, n: i)
    total = total + xs[i]
  end for
  return total
end fn sum
```

Compiler:
```
prog.cl:10:3: warning[unproved]: `ensures result == sum_spec(xs: xs, n: length(xs))` isn't proved: clc couldn't prove it from the `invariant` lines: either one doesn't hold when its loop starts, or a pass of the loop doesn't keep it, or a `decreases` doesn't get smaller, or together they aren't enough for this `ensures`; clc called it on 3000 small inputs and none broke it. It's still checked at run time
   10 |   ensures result == sum_spec(xs: xs, n: length(xs))
      |   ^^^^^^^
0 error(s), 1 warning(s)
```

## power

Task: Raise `b` to the power `e` by repeated multiplication. `pow_spec` below is the definition it must agree with.

```cl
fn pow_spec(b: Int, e: Int) -> Int
  requires e >= 0
  if e == 0
    return 1
  end if
  return b * pow_spec(b: b, e: e - 1)
end fn pow_spec
fn power(b: Int, e: Int) -> Int
  requires e >= 0
  ensures result == pow_spec(b: b, e: e)
  example power(b: 2, e: 10) == 1024
```

### attempt 1: unproved

```cl
fn power(b: Int, e: Int) -> Int
  requires e >= 0
  ensures result == pow_spec(b: b, e: e)
  example power(b: 2, e: 10) == 1024
  var r = 1
  var i = 0
  while i < e
    invariant 0 <= i and i <= e
    invariant r == pow_spec(b: b, e: i)
    decreases e - i
    r = r * b
    i = i + 1
  end while
  return r
end fn power
```

Compiler:
```
prog.cl:11:3: warning[unproved]: `ensures result == pow_spec(b: b, e: e)` isn't proved: clc couldn't prove it from the `invariant` lines: either one doesn't hold when its loop starts, or a pass of the loop doesn't keep it, or a `decreases` doesn't get smaller, or together they aren't enough for this `ensures`; clc called it on 1414 small inputs and none broke it. It's still checked at run time
   11 |   ensures result == pow_spec(b: b, e: e)
      |   ^^^^^^^
0 error(s), 1 warning(s)
```
