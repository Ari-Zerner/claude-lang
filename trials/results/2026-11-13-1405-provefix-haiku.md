# Fix-round trial 2026-11-13-1405 (haiku)

| case | the flaw | old words | new words |
|---|---|---|---|
| mul | a second `invariant` line that a pass doesn't keep when `a` is negative | 2 of 2 | 2 of 2 |
| divide | the invariant doesn't say `r >= 0`, which the end needs | 2 of 2 | 2 of 2 |
| sum | the invariant is one item ahead, so it is false at the start | 2 of 2 | 2 of 2 |
| fib | the second `invariant` line is off by one | 2 of 2 | 2 of 2 |
| gcd | `decreases x`, which doesn't go down when `x < y` | 2 of 2 | 2 of 2 |
| factorial | the invariant is one factor ahead: true at the start, not kept | 2 of 2 | 2 of 2 |
| digit_sum | the invariant doesn't say `k >= 0` | 2 of 2 | 2 of 2 |
| bsearch | the invariant doesn't say `hi <= length(xs)` | 2 of 2 | 2 of 2 |
| is_sorted | Haiku's own first answer: its invariant is false at the start | 0 of 2 | 2 of 2 |

old words: 16 of 18 fixes proved; new words: 18 of 18 fixes proved

## mul

The flaw: a second `invariant` line that a pass doesn't keep when `a` is negative.

```cl
fn mul(a: Int, b: Int) -> Int
  requires b >= 0
  ensures result == a * b
  example mul(a: 3, b: 4) == 12
  var r = 0
  for i in 0 until b
    invariant r == a * i
    invariant r >= 0
    r = r + a
  end for
  return r
end fn mul
```

### the old compiler: unproved

```
prog.cl:3:3: warning[unproved]: `ensures result == a * b` isn't proved: clc couldn't prove it from the `invariant` lines: either one doesn't hold when its loop starts, or a pass of the loop doesn't keep it, or a `decreases` doesn't get smaller, or together they aren't enough for this `ensures`; clc called it on 1508 small inputs and none broke it. It's still checked at run time
```

#### fix 1 after the old words: proved

```cl
fn mul(a: Int, b: Int) -> Int
  requires b >= 0
  ensures result == a * b
  example mul(a: 3, b: 4) == 12
  var r = 0
  for i in 0 until b
    invariant r == a * i
    r = r + a
  end for
  return r
end fn mul
```

#### fix 2 after the old words: proved

```cl
fn mul(a: Int, b: Int) -> Int
  requires b >= 0
  ensures result == a * b
  example mul(a: 3, b: 4) == 12
  var r = 0
  for i in 0 until b
    invariant r == a * i
    r = r + a
  end for
  return r
end fn mul
```

### the new compiler: unproved

```
prog.cl:3:3: warning[unproved]: `ensures result == a * b` isn't proved: clc couldn't show that a pass of the `for` on line 6 keeps `invariant r >= 0` true; clc called it on 1508 small inputs and none broke it. It's still checked at run time
```

#### fix 1 after the new words: proved

```cl
fn mul(a: Int, b: Int) -> Int
  requires b >= 0
  ensures result == a * b
  example mul(a: 3, b: 4) == 12
  var r = 0
  for i in 0 until b
    invariant r == a * i
    r = r + a
  end for
  return r
end fn mul
```

#### fix 2 after the new words: proved

```cl
fn mul(a: Int, b: Int) -> Int
  requires b >= 0
  ensures result == a * b
  example mul(a: 3, b: 4) == 12
  var r = 0
  for i in 0 until b
    invariant r == a * i
    r = r + a
  end for
  return r
end fn mul
```

## divide

The flaw: the invariant doesn't say `r >= 0`, which the end needs.

```cl
fn divide(a: Int, b: Int) -> Int
  requires a >= 0 and b > 0
  ensures result * b <= a and a < (result + 1) * b
  example divide(a: 17, b: 5) == 3
  var q = 0
  var r = a
  while r >= b
    invariant q * b + r == a
    decreases r
    r = r - b
    q = q + 1
  end while
  return q
end fn divide
```

### the old compiler: unproved

```
prog.cl:3:3: warning[unproved]: `ensures result * b <= a and a < (result + 1) * b` isn't proved: clc couldn't prove it from the `invariant` lines: either one doesn't hold when its loop starts, or a pass of the loop doesn't keep it, or a `decreases` doesn't get smaller, or together they aren't enough for this `ensures`; clc called it on 930 small inputs and none broke it. It's still checked at run time
```

#### fix 1 after the old words: proved

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

#### fix 2 after the old words: proved

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

### the new compiler: unproved

```
prog.cl:3:3: warning[unproved]: `ensures result * b <= a and a < (result + 1) * b` isn't proved: clc couldn't show that this `ensures` follows from what is true when the `while` on line 7 ends (`invariant q * b + r == a`, and that the loop is over); clc called it on 930 small inputs and none broke it. It's still checked at run time
```

#### fix 1 after the new words: proved

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

#### fix 2 after the new words: proved

```cl
fn divide(a: Int, b: Int) -> Int
  requires a >= 0 and b > 0
  ensures result * b <= a and a < (result + 1) * b
  example divide(a: 17, b: 5) == 3
  var q = 0
  var r = a
  while r >= b
    invariant q * b + r == a and r >= 0 and q >= 0
    decreases r
    r = r - b
    q = q + 1
  end while
  return q
end fn divide
```

## sum

The flaw: the invariant is one item ahead, so it is false at the start.

```cl
fn sum(xs: List[Int]) -> Int
  ensures result == sum_spec(xs: xs, n: length(xs))
  example sum([1, 2, 3]) == 6
  var t = 0
  for i in 0 until length(xs)
    invariant t == sum_spec(xs: xs, n: i + 1)
    t = t + xs[i]
  end for
  return t
end fn sum
```

### the old compiler: unproved

```
prog.cl:10:3: warning[unproved]: `ensures result == sum_spec(xs: xs, n: length(xs))` isn't proved: clc couldn't prove it from the `invariant` lines: either one doesn't hold when its loop starts, or a pass of the loop doesn't keep it, or a `decreases` doesn't get smaller, or together they aren't enough for this `ensures`; clc called it on 3000 small inputs and none broke it. It's still checked at run time
```

#### fix 1 after the old words: proved

```cl
fn sum(xs: List[Int]) -> Int
  ensures result == sum_spec(xs: xs, n: length(xs))
  example sum([1, 2, 3]) == 6
  var t = 0
  for i in 0 until length(xs)
    invariant t == sum_spec(xs: xs, n: i)
    t = t + xs[i]
  end for
  return t
end fn sum
```

#### fix 2 after the old words: proved

```cl
fn sum(xs: List[Int]) -> Int
  ensures result == sum_spec(xs: xs, n: length(xs))
  example sum([1, 2, 3]) == 6
  var t = 0
  for i in 0 until length(xs)
    invariant i >= 0 and i <= length(xs)
    invariant t == sum_spec(xs: xs, n: i)
    t = t + xs[i]
  end for
  return t
end fn sum
```

### the new compiler: unproved

```
prog.cl:10:3: warning[unproved]: `ensures result == sum_spec(xs: xs, n: length(xs))` isn't proved: clc couldn't show that `invariant t == sum_spec(xs: xs, n: i + 1)` is true when the `for` on line 13 starts; also, clc couldn't show that a pass of the `for` on line 13 keeps `invariant t == sum_spec(xs: xs, n: i + 1)` true; also, clc couldn't show that this `ensures` follows from what is true when the `for` on line 13 ends (`invariant t == sum_spec(xs: xs, n: i + 1)`, and that the loop is over); clc called it on 3000 small inputs and none broke it. It's still checked at run time
```

#### fix 1 after the new words: proved

```cl
fn sum(xs: List[Int]) -> Int
  ensures result == sum_spec(xs: xs, n: length(xs))
  example sum([1, 2, 3]) == 6
  var t = 0
  for i in 0 until length(xs)
    invariant i >= 0 and i <= length(xs)
    invariant t == sum_spec(xs: xs, n: i)
    t = t + xs[i]
  end for
  return t
end fn sum
```

#### fix 2 after the new words: proved

```cl
fn sum(xs: List[Int]) -> Int
  ensures result == sum_spec(xs: xs, n: length(xs))
  example sum([1, 2, 3]) == 6
  var t = 0
  for i in 0 until length(xs)
    invariant t == sum_spec(xs: xs, n: i)
    t = t + xs[i]
  end for
  return t
end fn sum
```

## fib

The flaw: the second `invariant` line is off by one.

```cl
fn fib(n: Int) -> Int
  requires n >= 0
  ensures result == fib_spec(n)
  example fib(10) == 55
  var a = 0
  var b = 1
  for i in 0 until n
    invariant a == fib_spec(i)
    invariant b == fib_spec(i)
    let t = a + b
    a = b
    b = t
  end for
  return a
end fn fib
```

### the old compiler: unproved

```
prog.cl:11:3: warning[unproved]: `ensures result == fib_spec(n)` isn't proved: clc couldn't prove it from the `invariant` lines: either one doesn't hold when its loop starts, or a pass of the loop doesn't keep it, or a `decreases` doesn't get smaller, or together they aren't enough for this `ensures`. It's still checked at run time
```

#### fix 1 after the old words: proved

```cl
fn fib(n: Int) -> Int
  requires n >= 0
  ensures result == fib_spec(n)
  example fib(10) == 55
  var a = 0
  var b = 1
  for i in 0 until n
    invariant a == fib_spec(i)
    invariant b == fib_spec(i + 1)
    let t = a + b
    a = b
    b = t
  end for
  return a
end fn fib
```

#### fix 2 after the old words: proved

```cl
fn fib(n: Int) -> Int
  requires n >= 0
  ensures result == fib_spec(n)
  example fib(10) == 55
  var a = 0
  var b = 1
  for i in 0 until n
    invariant a == fib_spec(i)
    invariant b == fib_spec(i + 1)
    let t = a + b
    a = b
    b = t
  end for
  return a
end fn fib
```

### the new compiler: unproved

```
prog.cl:11:3: warning[unproved]: `ensures result == fib_spec(n)` isn't proved: clc couldn't show that `invariant b == fib_spec(i)` is true when the `for` on line 15 starts; also, clc couldn't show that a pass of the `for` on line 15 keeps `invariant a == fib_spec(i)` and `invariant b == fib_spec(i)` true. It's still checked at run time
```

#### fix 1 after the new words: proved

```cl
fn fib(n: Int) -> Int
  requires n >= 0
  ensures result == fib_spec(n)
  example fib(10) == 55
  var a = 0
  var b = 1
  for i in 0 until n
    invariant a == fib_spec(i)
    invariant b == fib_spec(i + 1)
    let t = a + b
    a = b
    b = t
  end for
  return a
end fn fib
```

#### fix 2 after the new words: proved

```cl
fn fib(n: Int) -> Int
  requires n >= 0
  ensures result == fib_spec(n)
  example fib(10) == 55
  var a = 0
  var b = 1
  for i in 0 until n
    invariant a == fib_spec(i) and b == fib_spec(i + 1)
    let t = a + b
    a = b
    b = t
  end for
  return a
end fn fib
```

## gcd

The flaw: `decreases x`, which doesn't go down when `x < y`.

```cl
fn gcd(a: Int, b: Int) -> Int
  requires a >= 0 and b >= 0
  ensures result == gcd_spec(a: a, b: b)
  example gcd(a: 48, b: 36) == 12
  var x = a
  var y = b
  while y != 0
    invariant x >= 0 and y >= 0 and gcd_spec(a: x, b: y) == gcd_spec(a: a, b: b)
    decreases x
    let t = x % y
    x = y
    y = t
  end while
  return x
end fn gcd
```

### the old compiler: unproved

```
prog.cl:11:3: warning[unproved]: `ensures result == gcd_spec(a: a, b: b)` isn't proved: clc couldn't prove it from the `invariant` lines: either one doesn't hold when its loop starts, or a pass of the loop doesn't keep it, or a `decreases` doesn't get smaller, or together they aren't enough for this `ensures`; clc called it on 1225 small inputs and none broke it. It's still checked at run time
```

#### fix 1 after the old words: proved

```cl
fn gcd(a: Int, b: Int) -> Int
  requires a >= 0 and b >= 0
  ensures result == gcd_spec(a: a, b: b)
  example gcd(a: 48, b: 36) == 12
  var x = a
  var y = b
  while y != 0
    invariant x >= 0 and y >= 0 and gcd_spec(a: x, b: y) == gcd_spec(a: a, b: b)
    decreases y
    let t = x % y
    x = y
    y = t
  end while
  return x
end fn gcd
```

#### fix 2 after the old words: proved

```cl
fn gcd(a: Int, b: Int) -> Int
  requires a >= 0 and b >= 0
  ensures result == gcd_spec(a: a, b: b)
  example gcd(a: 48, b: 36) == 12
  var x = a
  var y = b
  while y != 0
    invariant x >= 0 and y >= 0 and gcd_spec(a: x, b: y) == gcd_spec(a: a, b: b)
    decreases y
    let t = x % y
    x = y
    y = t
  end while
  return x
end fn gcd
```

### the new compiler: unproved

```
prog.cl:11:3: warning[unproved]: `ensures result == gcd_spec(a: a, b: b)` isn't proved: clc couldn't show that a pass of the `while` on line 15 makes `decreases x` smaller while it stays at 0 or above; clc called it on 1225 small inputs and none broke it. It's still checked at run time
```

#### fix 1 after the new words: proved

```cl
fn gcd(a: Int, b: Int) -> Int
  requires a >= 0 and b >= 0
  ensures result == gcd_spec(a: a, b: b)
  example gcd(a: 48, b: 36) == 12
  var x = a
  var y = b
  while y != 0
    invariant x >= 0 and y >= 0 and gcd_spec(a: x, b: y) == gcd_spec(a: a, b: b)
    decreases y
    let t = x % y
    x = y
    y = t
  end while
  return x
end fn gcd
```

#### fix 2 after the new words: proved

```cl
fn gcd(a: Int, b: Int) -> Int
  requires a >= 0 and b >= 0
  ensures result == gcd_spec(a: a, b: b)
  example gcd(a: 48, b: 36) == 12
  var x = a
  var y = b
  while y != 0
    invariant x >= 0 and y >= 0 and gcd_spec(a: x, b: y) == gcd_spec(a: a, b: b)
    decreases y
    let t = x % y
    x = y
    y = t
  end while
  return x
end fn gcd
```

## factorial

The flaw: the invariant is one factor ahead: true at the start, not kept.

```cl
fn factorial(n: Int) -> Int
  requires n >= 0
  ensures result == fact_spec(n)
  example factorial(5) == 120
  var r = 1
  for i in 1 through n
    invariant r == fact_spec(i)
    r = r * i
  end for
  return r
end fn factorial
```

### the old compiler: unproved

```
prog.cl:11:3: warning[unproved]: `ensures result == fact_spec(n)` isn't proved: clc couldn't prove it from the `invariant` lines: either one doesn't hold when its loop starts, or a pass of the loop doesn't keep it, or a `decreases` doesn't get smaller, or together they aren't enough for this `ensures`; clc called it on 32 small inputs and none broke it. It's still checked at run time
```

#### fix 1 after the old words: proved

```cl
fn factorial(n: Int) -> Int
  requires n >= 0
  ensures result == fact_spec(n)
  example factorial(5) == 120
  var r = 1
  for i in 1 through n
    invariant r == fact_spec(i - 1)
    r = r * i
  end for
  return r
end fn factorial
```

#### fix 2 after the old words: proved

```cl
fn factorial(n: Int) -> Int
  requires n >= 0
  ensures result == fact_spec(n)
  example factorial(5) == 120
  var r = 1
  for i in 1 through n
    invariant i >= 1 and i <= n + 1 and r == fact_spec(i - 1)
    r = r * i
  end for
  return r
end fn factorial
```

### the new compiler: unproved

```
prog.cl:11:3: warning[unproved]: `ensures result == fact_spec(n)` isn't proved: clc couldn't show that a pass of the `for` on line 14 keeps `invariant r == fact_spec(i)` true; also, clc couldn't show that this `ensures` follows from what is true when the `for` on line 14 ends (`invariant r == fact_spec(i)`, and that the loop is over); clc called it on 32 small inputs and none broke it. It's still checked at run time
```

#### fix 1 after the new words: proved

```cl
fn factorial(n: Int) -> Int
  requires n >= 0
  ensures result == fact_spec(n)
  example factorial(5) == 120
  var r = 1
  for i in 0 until n
    invariant r == fact_spec(i)
    r = r * (i + 1)
  end for
  return r
end fn factorial
```

#### fix 2 after the new words: proved

```cl
fn factorial(n: Int) -> Int
  requires n >= 0
  ensures result == fact_spec(n)
  example factorial(5) == 120
  var r = 1
  for i in 0 until n
    invariant r == fact_spec(i)
    r = (i + 1) * r
  end for
  return r
end fn factorial
```

## digit_sum

The flaw: the invariant doesn't say `k >= 0`.

```cl
fn digit_sum(n: Int) -> Int
  requires n >= 0
  ensures result == digits_spec(n)
  example digit_sum(1234) == 10
  var k = n
  var s = 0
  while k >= 10
    invariant s + digits_spec(k) == digits_spec(n)
    decreases k
    s = s + k % 10
    k = k / 10
  end while
  return s + k
end fn digit_sum
```

### the old compiler: unproved

```
prog.cl:11:3: warning[unproved]: `ensures result == digits_spec(n)` isn't proved: clc couldn't prove it from the `invariant` lines: either one doesn't hold when its loop starts, or a pass of the loop doesn't keep it, or a `decreases` doesn't get smaller, or together they aren't enough for this `ensures`; clc called it on 32 small inputs and none broke it. It's still checked at run time
```

#### fix 1 after the old words: proved

```cl
fn digit_sum(n: Int) -> Int
  requires n >= 0
  ensures result == digits_spec(n)
  example digit_sum(1234) == 10
  var k = n
  var s = 0
  while k >= 10
    invariant k >= 0 and s + digits_spec(k) == digits_spec(n)
    decreases k
    s = s + k % 10
    k = k / 10
  end while
  return s + k
end fn digit_sum
```

#### fix 2 after the old words: proved

```cl
fn digit_sum(n: Int) -> Int
  requires n >= 0
  ensures result == digits_spec(n)
  example digit_sum(1234) == 10
  var k = n
  var s = 0
  while k >= 10
    invariant k >= 0 and k <= n
    invariant s >= 0
    invariant s + digits_spec(k) == digits_spec(n)
    decreases k
    s = s + k % 10
    k = k / 10
  end while
  return s + k
end fn digit_sum
```

### the new compiler: unproved

```
prog.cl:11:3: warning[unproved]: `ensures result == digits_spec(n)` isn't proved: clc couldn't show that this `ensures` follows from what is true when the `while` on line 15 ends (`invariant s + digits_spec(k) == digits_spec(n)`, and that the loop is over); clc called it on 32 small inputs and none broke it. It's still checked at run time
```

#### fix 1 after the new words: proved

```cl
fn digit_sum(n: Int) -> Int
  requires n >= 0
  ensures result == digits_spec(n)
  example digit_sum(1234) == 10
  var k = n
  var s = 0
  while k >= 10
    invariant k >= 0 and s >= 0
    invariant s + digits_spec(k) == digits_spec(n)
    decreases k
    s = s + k % 10
    k = k / 10
  end while
  return s + k
end fn digit_sum
```

#### fix 2 after the new words: proved

```cl
fn digit_sum(n: Int) -> Int
  requires n >= 0
  ensures result == digits_spec(n)
  example digit_sum(1234) == 10
  var k = n
  var s = 0
  while k > 0
    invariant k >= 0 and s + digits_spec(k) == digits_spec(n)
    decreases k
    s = s + k % 10
    k = k / 10
  end while
  return s + k
end fn digit_sum
```

## bsearch

The flaw: the invariant doesn't say `hi <= length(xs)`.

```cl
fn bsearch(xs: List[Int], want: Int) -> Int
  ensures result == -1 or (result >= 0 and result < length(xs) and xs[result] == want)
  example bsearch(xs: [1, 3, 5, 7], want: 5) == 2
  example bsearch(xs: [1, 3, 5, 7], want: 4) == -1
  var lo = 0
  var hi = length(xs)
  while lo < hi
    invariant lo >= 0
    decreases hi - lo
    let mid = (lo + hi) / 2
    if xs[mid] == want
      return mid
    end if
    if xs[mid] < want
      lo = mid + 1
    else
      hi = mid
    end if
  end while
  return -1
end fn bsearch
```

### the old compiler: unproved

```
prog.cl:2:3: warning[unproved]: `ensures result == -1 or (result >= 0 and result < length(xs) and xs[result] == want)` isn't proved: clc couldn't prove it from the `invariant` lines: either one doesn't hold when its loop starts, or a pass of the loop doesn't keep it, or a `decreases` doesn't get smaller, or together they aren't enough for this `ensures`; clc called it on 3000 small inputs and none broke it. It's still checked at run time
```

#### fix 1 after the old words: proved

```cl
fn bsearch(xs: List[Int], want: Int) -> Int
  ensures result == -1 or (result >= 0 and result < length(xs) and xs[result] == want)
  example bsearch(xs: [1, 3, 5, 7], want: 5) == 2
  example bsearch(xs: [1, 3, 5, 7], want: 4) == -1
  var lo = 0
  var hi = length(xs)
  while lo < hi
    invariant lo >= 0
    invariant hi <= length(xs)
    invariant lo <= hi
    decreases hi - lo
    let mid = (lo + hi) / 2
    if xs[mid] == want
      return mid
    end if
    if xs[mid] < want
      lo = mid + 1
    else
      hi = mid
    end if
  end while
  return -1
end fn bsearch
```

#### fix 2 after the old words: proved

```cl
fn bsearch(xs: List[Int], want: Int) -> Int
  ensures result == -1 or (result >= 0 and result < length(xs) and xs[result] == want)
  example bsearch(xs: [1, 3, 5, 7], want: 5) == 2
  example bsearch(xs: [1, 3, 5, 7], want: 4) == -1
  var lo = 0
  var hi = length(xs)
  while lo < hi
    invariant lo >= 0 and lo <= hi and hi <= length(xs)
    decreases hi - lo
    let mid = lo + (hi - lo) / 2
    if xs[mid] == want
      return mid
    end if
    if xs[mid] < want
      lo = mid + 1
    else
      hi = mid
    end if
  end while
  return -1
end fn bsearch
```

### the new compiler: unproved

```
prog.cl:2:3: warning[unproved]: `ensures result == -1 or (result >= 0 and result < length(xs) and xs[result] == want)` isn't proved: clc couldn't show that a pass of the `while` on line 7 returns only a value that meets this `ensures`; clc called it on 3000 small inputs and none broke it. It's still checked at run time
```

#### fix 1 after the new words: proved

```cl
fn bsearch(xs: List[Int], want: Int) -> Int
  ensures result == -1 or (result >= 0 and result < length(xs) and xs[result] == want)
  example bsearch(xs: [1, 3, 5, 7], want: 5) == 2
  example bsearch(xs: [1, 3, 5, 7], want: 4) == -1
  let n = length(xs)
  var lo = 0
  var hi = n
  while lo < hi
    invariant lo >= 0 and lo <= hi and hi <= n
    decreases hi - lo
    let mid = (lo + hi) / 2
    if xs[mid] == want
      return mid
    end if
    if xs[mid] < want
      lo = mid + 1
    else
      hi = mid
    end if
  end while
  return -1
end fn bsearch
```

#### fix 2 after the new words: proved

```cl
fn bsearch(xs: List[Int], want: Int) -> Int
  ensures result == -1 or (result >= 0 and result < length(xs) and xs[result] == want)
  example bsearch(xs: [1, 3, 5, 7], want: 5) == 2
  example bsearch(xs: [1, 3, 5, 7], want: 4) == -1
  var lo = 0
  var hi = length(xs)
  while lo < hi
    invariant lo >= 0 and lo <= hi and hi <= length(xs)
    decreases hi - lo
    let mid = lo + (hi - lo) / 2
    if xs[mid] == want
      return mid
    end if
    if xs[mid] < want
      lo = mid + 1
    else
      hi = mid
    end if
  end while
  return -1
end fn bsearch
```

## is_sorted

The flaw: Haiku's own first answer: its invariant is false at the start.

```cl
fn is_sorted(xs: List[Int]) -> Bool
  ensures result == sorted_spec(xs: xs, n: length(xs))
  example is_sorted([1, 2, 2, 5]) == true
  example is_sorted([1, 3, 2]) == false
  let n = length(xs)
  var ok = true
  for i in 1 until n
    invariant i >= 1 and i <= n and ok == sorted_spec(xs: xs, n: i)
    ok = ok and xs[i - 1] <= xs[i]
  end for
  return ok
end fn is_sorted
```

### the old compiler: unproved

```
prog.cl:10:3: warning[unproved]: `ensures result == sorted_spec(xs: xs, n: length(xs))` isn't proved: clc couldn't prove it from the `invariant` lines: either one doesn't hold when its loop starts, or a pass of the loop doesn't keep it, or a `decreases` doesn't get smaller, or together they aren't enough for this `ensures`; clc called it on 3000 small inputs and none broke it. It's still checked at run time
```

#### fix 1 after the old words: unproved

```cl
fn is_sorted(xs: List[Int]) -> Bool
  ensures result == sorted_spec(xs: xs, n: length(xs))
  example is_sorted([1, 2, 2, 5]) == true
  example is_sorted([1, 3, 2]) == false
  let n = length(xs)
  var ok = true
  for i in 1 until n
    invariant i >= 1 and i <= n and ok == sorted_spec(xs: xs, n: i)
    if xs[i - 1] > xs[i]
      ok = false
    end if
  end for
  return ok
end fn is_sorted
```

```
prog.cl:10:3: warning[unproved]: `ensures result == sorted_spec(xs: xs, n: length(xs))` isn't proved: clc couldn't show that `invariant i >= 1 and i <= n and ok == sorted_spec(xs: xs, n: i)` is true when the `for` on line 15 starts; clc called it on 3000 small inputs and none broke it. It's still checked at run time
```

#### fix 2 after the old words: unproved

```cl
fn is_sorted(xs: List[Int]) -> Bool
  ensures result == sorted_spec(xs: xs, n: length(xs))
  example is_sorted([1, 2, 2, 5]) == true
  example is_sorted([1, 3, 2]) == false
  let n = length(xs)
  var ok = true
  var i = 1
  while i < n
    invariant i >= 1 and i <= n + 1 and (i > n or ok == sorted_spec(xs: xs, n: i))
    decreases n - i
    ok = ok and xs[i - 1] <= xs[i]
    i = i + 1
  end while
  return ok
end fn is_sorted
```

```
prog.cl:10:3: warning[unproved]: `ensures result == sorted_spec(xs: xs, n: length(xs))` isn't proved: clc couldn't show that this `ensures` follows from what is true when the `while` on line 16 ends (`invariant i >= 1 and i <= n + 1 and (i > n or ok == sorted_spec(xs: xs, n: i))`, and that the loop is over); clc called it on 3000 small inputs and none broke it. It's still checked at run time
```

### the new compiler: unproved

```
prog.cl:10:3: warning[unproved]: `ensures result == sorted_spec(xs: xs, n: length(xs))` isn't proved: clc couldn't show that `invariant i >= 1 and i <= n and ok == sorted_spec(xs: xs, n: i)` is true when the `for` on line 15 starts; clc called it on 3000 small inputs and none broke it. It's still checked at run time
```

#### fix 1 after the new words: proved

```cl
fn is_sorted(xs: List[Int]) -> Bool
  ensures result == sorted_spec(xs: xs, n: length(xs))
  example is_sorted([1, 2, 2, 5]) == true
  example is_sorted([1, 3, 2]) == false
  let n = length(xs)
  if n < 2
    return true
  end if
  var ok = true
  for i in 1 until n
    invariant i >= 1 and i <= n and n >= 2 and ok == sorted_spec(xs: xs, n: i)
    ok = ok and xs[i - 1] <= xs[i]
  end for
  return ok
end fn is_sorted
```

#### fix 2 after the new words: proved

```cl
fn is_sorted(xs: List[Int]) -> Bool
  ensures result == sorted_spec(xs: xs, n: length(xs))
  example is_sorted([1, 2, 2, 5]) == true
  example is_sorted([1, 3, 2]) == false
  let n = length(xs)
  var ok = true
  for i in 0 until n
    invariant i >= 0 and i <= n and ok == sorted_spec(xs: xs, n: i)
    if i > 0
      ok = ok and xs[i - 1] <= xs[i]
    end if
  end for
  return ok
end fn is_sorted
```
