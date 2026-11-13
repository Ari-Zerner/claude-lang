# Proof trial 2026-11-13-1205 (control, night 8's compiler, hard set)

| task | the slip | result |
|---|---|---|
| bsearch | returns the low end of the range, not where it found the item | caught: clc found an input that breaks it |
| gcd | stops when `y` reaches 1, one step early | caught: clc found an input that breaks it |
| factorial | leaves out the last factor | caught: clc found an input that breaks it |
| digit_sum | forgets the last digit | caught: clc found an input that breaks it |
| reversed_list | leaves out the last item | caught: clc found an input that breaks it |
| max_index | remembers the index after the largest item | PROVED, though the `ensures` is false |
| is_sorted | treats two equal neighbours as out of order | caught: clc found an input that breaks it |

Each task's wrong loop, built with night 8's compiler (commit f16db28, before D34): its `ensures` is false for some input, so it must not come out proved.

## bsearch

The slip: it returns the low end of the range, not where it found the item.

```cl
fn bsearch(xs: List[Int], want: Int) -> Int
  ensures result == -1 or (result >= 0 and result < length(xs) and xs[result] == want)
  var lo = 0
  var hi = length(xs)
  while lo < hi
    invariant lo >= 0 and hi <= length(xs)
    decreases hi - lo
    let mid = (lo + hi) / 2
    if xs[mid] == want
      return lo
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

**caught: clc found an input that breaks it**

Compiler:
```
prog.cl:2:3: error[ensures-false]: `ensures result == -1 or (result >= 0 and result < length(xs) and xs[result] == want)` is false: bsearch(xs: [0, 1], want: 1) returns 0
    2 |   ensures result == -1 or (result >= 0 and result < length(xs) and xs[result] == want)
      |   ^^^^^^^
  fix: clc found this by calling fn bsearch on small inputs. Change the function or the `ensures`, or add a `requires` that rules this call out
1 error(s), 0 warning(s)
```

## gcd

The slip: it stops when `y` reaches 1, one step early.

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
  var x = a
  var y = b
  while y > 1
    invariant x >= 0 and y >= 0 and gcd_spec(a: x, b: y) == gcd_spec(a: a, b: b)
    decreases y
    let t = x % y
    x = y
    y = t
  end while
  return x
end fn gcd
```

**caught: clc found an input that breaks it**

Compiler:
```
prog.cl:11:3: error[ensures-false]: `ensures result == gcd_spec(a: a, b: b)` is false: gcd(a: 0, b: 1) returns 0
   11 |   ensures result == gcd_spec(a: a, b: b)
      |   ^^^^^^^
  fix: clc found this by calling fn gcd on small inputs. Change the function or the `ensures`, or add a `requires` that rules this call out
1 error(s), 0 warning(s)
```

## factorial

The slip: it leaves out the last factor.

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
  var r = 1
  for i in 1 until n
    invariant r == fact_spec(i - 1)
    r = r * i
  end for
  return r
end fn factorial
```

**caught: clc found an input that breaks it**

Compiler:
```
prog.cl:11:3: error[ensures-false]: `ensures result == fact_spec(n)` is false: factorial(n: 2) returns 1
   11 |   ensures result == fact_spec(n)
      |   ^^^^^^^
  fix: clc found this by calling fn factorial on small inputs. Change the function or the `ensures`, or add a `requires` that rules this call out
1 error(s), 0 warning(s)
```

## digit_sum

The slip: it forgets the last digit.

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
  var k = n
  var s = 0
  while k >= 10
    invariant k >= 0 and s + digits_spec(k) == digits_spec(n)
    decreases k
    s = s + k % 10
    k = k / 10
  end while
  return s
end fn digit_sum
```

**caught: clc found an input that breaks it**

Compiler:
```
prog.cl:11:3: error[ensures-false]: `ensures result == digits_spec(n)` is false: digit_sum(n: 1) returns 0
   11 |   ensures result == digits_spec(n)
      |   ^^^^^^^
  fix: clc found this by calling fn digit_sum on small inputs. Change the function or the `ensures`, or add a `requires` that rules this call out
1 error(s), 0 warning(s)
```

## reversed_list

The slip: it leaves out the last item.

```cl
fn reversed_list(xs: List[Int]) -> List[Int]
  ensures length(result) == length(xs)
  var out: List[Int] = []
  for i in 1 until length(xs)
    invariant length(out) == i - 1
    out = append(list: out, item: xs[length(xs) - 1 - i])
  end for
  return out
end fn reversed_list
```

**caught: clc found an input that breaks it**

Compiler:
```
prog.cl:2:3: error[ensures-false]: `ensures length(result) == length(xs)` is false: reversed_list(xs: [0]) returns []
    2 |   ensures length(result) == length(xs)
      |   ^^^^^^^
  fix: clc found this by calling fn reversed_list on small inputs. Change the function or the `ensures`, or add a `requires` that rules this call out
1 error(s), 0 warning(s)
```

## max_index

The slip: it remembers the index after the largest item.

```cl
fn max_index(xs: List[Int]) -> Int
  requires length(xs) > 0
  ensures result >= 0 and result < length(xs)
  var best = 0
  for i in 1 until length(xs)
    invariant best >= 0
    if xs[i] > xs[best]
      best = i + 1
    end if
  end for
  return best
end fn max_index
```

**PROVED, though the `ensures` is false**

Compiler:
```
0 example(s) passed; 1 of 1 `ensures` proved
```

## is_sorted

The slip: it treats two equal neighbours as out of order.

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
  if length(xs) < 2
    return true
  end if
  var ok = true
  for i in 1 until length(xs)
    invariant ok == sorted_spec(xs: xs, n: i)
    if xs[i - 1] >= xs[i]
      ok = false
    end if
  end for
  return ok
end fn is_sorted
```

**caught: clc found an input that breaks it**

Compiler:
```
prog.cl:10:3: error[ensures-false]: `ensures result == sorted_spec(xs: xs, n: length(xs))` is false: is_sorted(xs: [0, 0]) returns false
   10 |   ensures result == sorted_spec(xs: xs, n: length(xs))
      |   ^^^^^^^
  fix: clc found this by calling fn is_sorted on small inputs. Change the function or the `ensures`, or add a `requires` that rules this call out
1 error(s), 0 warning(s)
```
