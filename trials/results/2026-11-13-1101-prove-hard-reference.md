# Proof trial 2026-11-13-1101 (reference, hard set)

| task | result |
|---|---|
| bsearch | proved, first try |
| gcd | proved, first try |
| factorial | proved, first try |
| digit_sum | proved, first try |
| reversed_list | proved, first try |
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
    invariant lo >= 0 and hi <= length(xs)
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
  var r = 1
  for i in 1 through n
    invariant r == fact_spec(i - 1)
    r = r * i
  end for
  return r
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
  for i in 0 until length(xs)
    invariant length(out) == i
    out = append(list: out, item: xs[length(xs) - 1 - i])
  end for
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
    invariant best >= 0 and best < length(xs)
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
  if length(xs) < 2
    return true
  end if
  var ok = true
  for i in 1 until length(xs)
    invariant ok == sorted_spec(xs: xs, n: i)
    if xs[i - 1] > xs[i]
      ok = false
    end if
  end for
  return ok
end fn is_sorted
```
