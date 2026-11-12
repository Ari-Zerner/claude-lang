# Proof trial 2026-11-12-1507 (replay-hard-haiku)

| task | result |
|---|---|
| bsearch | proved, first try |
| gcd | proved, first try |
| factorial | proved, first try |
| digit_sum | proved, first try |
| reversed_list | proved, first try |
| max_index | proved, first try |
| is_sorted | not proved (last: unproved) |

First answers from `trials/results/2026-11-12-1500-prove-hard-haiku.md`, graded again with `/root/projects/claude-lang/clc.py`.

## bsearch

Task: Binary search: `xs` is sorted in increasing order; return an index where `want` is, or -1 when it isn't there. Halve the range each pass; don't scan the list item by item.

```cl
fn bsearch(xs: List[Int], want: Int) -> Int
  ensures result == -1 or (result >= 0 and result < length(xs) and xs[result] == want)
  example bsearch(xs: [1, 3, 5, 7], want: 5) == 2
  example bsearch(xs: [1, 3, 5, 7], want: 4) == -1
```

### attempt 1: proved

```cl
fn bsearch(xs: List[Int], want: Int) -> Int
  ensures result == -1 or (result >= 0 and result < length(xs) and xs[result] == want)
  example bsearch(xs: [1, 3, 5, 7], want: 5) == 2
  example bsearch(xs: [1, 3, 5, 7], want: 4) == -1
  var lo = 0
  var hi = length(xs)
  while lo < hi
    invariant 0 <= lo and lo <= hi and hi <= length(xs)
    decreases hi - lo
    let mid = (lo + hi) / 2
    if xs[mid] < want
      lo = mid + 1
    else if xs[mid] > want
      hi = mid
    else
      return mid
    end if
  end while
  return -1
end fn bsearch
```

## gcd

Task: Greatest common divisor by Euclid's method, with a loop. `gcd_spec` below is the definition it must agree with.

```cl
fn gcd_spec(a: Int, b: Int) -> Int
  requires a >= 0 and b >= 0
  if b == 0
    return a
  end if
  return gcd_spec(a: b, b: a % b)
end fn gcd_spec
fn gcd(a: Int, b: Int) -> Int
  requires a >= 0 and b >= 0
  ensures result == gcd_spec(a: a, b: b)
  example gcd(a: 48, b: 36) == 12
```

### attempt 1: proved

```cl
fn gcd(a: Int, b: Int) -> Int
  requires a >= 0 and b >= 0
  ensures result == gcd_spec(a: a, b: b)
  example gcd(a: 48, b: 36) == 12
  example gcd(a: 7, b: 0) == 7
  var x = a
  var y = b
  while y != 0
    invariant x >= 0 and y >= 0 and gcd_spec(a: x, b: y) == gcd_spec(a: a, b: b)
    decreases y
    var r = x % y
    x = y
    y = r
  end while
  return x
end fn gcd
```

## factorial

Task: n factorial, with a loop. `fact_spec` below is the definition it must agree with.

```cl
fn fact_spec(n: Int) -> Int
  requires n >= 0
  if n == 0
    return 1
  end if
  return n * fact_spec(n - 1)
end fn fact_spec
fn factorial(n: Int) -> Int
  requires n >= 0
  ensures result == fact_spec(n)
  example factorial(5) == 120
```

### attempt 1: proved

```cl
fn factorial(n: Int) -> Int
  requires n >= 0
  ensures result == fact_spec(n)
  example factorial(5) == 120
  var acc = 1
  for i in 0 until n
    invariant acc == fact_spec(i)
    acc = acc * (i + 1)
  end for
  return acc
end fn factorial
```

## digit_sum

Task: The sum of the decimal digits of n, with a loop. `digits_spec` below is the definition it must agree with.

```cl
fn digits_spec(n: Int) -> Int
  requires n >= 0
  if n < 10
    return n
  end if
  return n % 10 + digits_spec(n / 10)
end fn digits_spec
fn digit_sum(n: Int) -> Int
  requires n >= 0
  ensures result == digits_spec(n)
  example digit_sum(1234) == 10
```

### attempt 1: proved

```cl
fn digit_sum(n: Int) -> Int
  requires n >= 0
  ensures result == digits_spec(n)
  example digit_sum(1234) == 10
  var m = n
  var total = 0
  while m > 0
    invariant m >= 0 and total + digits_spec(m) == digits_spec(n)
    decreases m
    total = total + m % 10
    m = m / 10
  end while
  return total
end fn digit_sum
```

## reversed_list

Task: Return the items of the list in the opposite order.

```cl
fn reversed_list(xs: List[Int]) -> List[Int]
  ensures length(result) == length(xs)
  example reversed_list([1, 2, 3]) == [3, 2, 1]
```

### attempt 1: proved

```cl
fn reversed_list(xs: List[Int]) -> List[Int]
  ensures length(result) == length(xs)
  example reversed_list([1, 2, 3]) == [3, 2, 1]
  var out: List[Int] = []
  var i = length(xs)
  while i > 0
    invariant i >= 0 and i <= length(xs)
    invariant length(out) == length(xs) - i
    decreases i
    i = i - 1
    out = append(list: out, item: xs[i])
  end while
  return out
end fn reversed_list
```

## max_index

Task: Return the index of the largest item (the first one, if it appears more than once).

```cl
fn max_index(xs: List[Int]) -> Int
  requires length(xs) > 0
  ensures result >= 0 and result < length(xs)
  example max_index([3, 9, 2]) == 1
```

### attempt 1: proved

```cl
fn max_index(xs: List[Int]) -> Int
  requires length(xs) > 0
  ensures result >= 0 and result < length(xs)
  example max_index([3, 9, 2]) == 1
  let n = length(xs)
  var best = 0
  for i in 1 until n
    invariant best >= 0 and best < n
    if xs[i] > xs[best]
      best = i
    end if
  end for
  return best
end fn max_index
```

## is_sorted

Task: Is the list in non-decreasing order? `sorted_spec(xs, n)` below, which says whether the first n items are, is the definition it must agree with.

```cl
fn sorted_spec(xs: List[Int], n: Int) -> Bool
  requires n >= 0 and n <= length(xs)
  if n < 2
    return true
  end if
  return sorted_spec(xs: xs, n: n - 1) and xs[n - 2] <= xs[n - 1]
end fn sorted_spec
fn is_sorted(xs: List[Int]) -> Bool
  ensures result == sorted_spec(xs: xs, n: length(xs))
  example is_sorted([1, 2, 2, 5]) == true
  example is_sorted([1, 3, 2]) == false
```

### attempt 1: unproved

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

Compiler:
```
prog.cl:10:3: warning[unproved]: `ensures result == sorted_spec(xs: xs, n: length(xs))` isn't proved: clc couldn't prove it from the `invariant` lines: either one doesn't hold when its loop starts, or a pass of the loop doesn't keep it, or a `decreases` doesn't get smaller, or together they aren't enough for this `ensures`; clc called it on 3000 small inputs and none broke it. It's still checked at run time
   10 |   ensures result == sorted_spec(xs: xs, n: length(xs))
      |   ^^^^^^^
0 error(s), 1 warning(s)
```
