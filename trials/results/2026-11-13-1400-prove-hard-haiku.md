# Proof trial 2026-11-13-1400 (haiku, hard set)

| task | result |
|---|---|
| bsearch | proved, first try |
| gcd | proved, first try |
| factorial | proved, first try |
| digit_sum | proved, first try |
| reversed_list | proved after 1 fix |
| max_index | proved, first try |
| is_sorted | proved, first try |

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
    let mid = lo + (hi - lo) / 2
    if xs[mid] == want
      return mid
    else if xs[mid] < want
      lo = mid + 1
    else
      hi = mid
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
  var x = a
  var y = b
  while y != 0
    invariant x >= 0 and y >= 0
    invariant gcd_spec(a: x, b: y) == gcd_spec(a: a, b: b)
    decreases y
    var t = x % y
    x = y
    y = t
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
  for i in 1 until n + 1
    invariant i >= 1 and i <= n + 1
    invariant acc == fact_spec(i - 1)
    acc = acc * i
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
  var s = 0
  while m > 0
    invariant s >= 0 and m >= 0 and s + digits_spec(m) == digits_spec(n)
    decreases m
    s = s + m % 10
    m = m / 10
  end while
  return s
end fn digit_sum
```

## reversed_list

Task: Return the items of the list in the opposite order.

```cl
fn reversed_list(xs: List[Int]) -> List[Int]
  ensures length(result) == length(xs)
  example reversed_list([1, 2, 3]) == [3, 2, 1]
```

### attempt 1: unproved

```cl
fn reversed_list(xs: List[Int]) -> List[Int]
  ensures length(result) == length(xs)
  example reversed_list([1, 2, 3]) == [3, 2, 1]
  let n = length(xs)
  var out = repeat(item: 0, times: n)
  for i in 0 until n
    invariant length(out) == n
    out[n - 1 - i] = xs[i]
  end for
  return out
end fn reversed_list
```

Compiler:
```
prog.cl:2:3: warning[unproved]: `ensures length(result) == length(xs)` isn't proved: clc couldn't show that `invariant length(out) == n` is true when the `for` on line 6 starts; also, clc couldn't show that a pass of the `for` on line 6 keeps `invariant length(out) == n` true; clc called it on 3000 small inputs and none broke it. It's still checked at run time
    2 |   ensures length(result) == length(xs)
      |   ^^^^^^^
0 error(s), 1 warning(s)
```

_Sent back for a fix._

### attempt 2: proved

```cl
fn reversed_list(xs: List[Int]) -> List[Int]
  ensures length(result) == length(xs)
  example reversed_list([1, 2, 3]) == [3, 2, 1]
  let n = length(xs)
  var out: List[Int] = []
  var i = 0
  while i < n
    invariant i >= 0 and i <= n and length(out) == i
    decreases n - i
    out = append(list: out, item: xs[n - 1 - i])
    i = i + 1
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
  var best = 0
  for i in 1 until length(xs)
    invariant best >= 0 and best < length(xs) and best < i
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

### attempt 1: proved

```cl
fn is_sorted(xs: List[Int]) -> Bool
  ensures result == sorted_spec(xs: xs, n: length(xs))
  example is_sorted([1, 2, 2, 5]) == true
  example is_sorted([1, 3, 2]) == false
  let n = length(xs)
  var ok = true
  var i = 0
  while i < n
    invariant 0 <= i and i <= n
    invariant ok == sorted_spec(xs: xs, n: i)
    decreases n - i
    if i >= 1
      ok = ok and xs[i - 1] <= xs[i]
    end if
    i = i + 1
  end while
  return ok
end fn is_sorted
```
