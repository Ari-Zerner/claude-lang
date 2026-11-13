# Fix-round trial 2026-11-13-1416 (haiku)

| case | the flaw | old words | new words |
|---|---|---|---|
| is_sorted | Haiku's own first answer: its invariant is false at the start | 4 of 5 | 5 of 5 |

old words: 4 of 5 fixes proved; new words: 5 of 5 fixes proved

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
    ok = ok and xs[i - 1] <= xs[i]
  end for
  return ok
end fn is_sorted
```

```
prog.cl:10:3: warning[unproved]: `ensures result == sorted_spec(xs: xs, n: length(xs))` isn't proved: clc couldn't show that `invariant i >= 1 and i <= n and ok == sorted_spec(xs: xs, n: i)` is true when the `for` on line 15 starts; clc called it on 3000 small inputs and none broke it. It's still checked at run time
```

#### fix 2 after the old words: proved

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
    invariant i >= 1 and i <= n and ok == sorted_spec(xs: xs, n: i)
    ok = ok and xs[i - 1] <= xs[i]
  end for
  return ok
end fn is_sorted
```

#### fix 3 after the old words: proved

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
    invariant i >= 1 and i <= n and ok == sorted_spec(xs: xs, n: i)
    ok = ok and xs[i - 1] <= xs[i]
  end for
  return ok
end fn is_sorted
```

#### fix 4 after the old words: proved

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
    invariant i >= 1 and i <= n and ok == sorted_spec(xs: xs, n: i)
    ok = ok and xs[i - 1] <= xs[i]
  end for
  return ok
end fn is_sorted
```

#### fix 5 after the old words: proved

```cl
fn is_sorted(xs: List[Int]) -> Bool
  ensures result == sorted_spec(xs: xs, n: length(xs))
  example is_sorted([1, 2, 2, 5]) == true
  example is_sorted([1, 3, 2]) == false
  let n = length(xs)
  var ok = true
  for i in 0 until n
    invariant i >= 0 and i <= n and ok == sorted_spec(xs: xs, n: i)
    ok = ok and (i == 0 or xs[i - 1] <= xs[i])
  end for
  return ok
end fn is_sorted
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
  var ok = true
  var i = 0
  while i < n
    invariant i >= 0 and i <= n and ok == sorted_spec(xs: xs, n: i)
    decreases n - i
    if i >= 1
      ok = ok and xs[i - 1] <= xs[i]
    end if
    i = i + 1
  end while
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
  if n < 2
    return true
  end if
  var ok = true
  for i in 1 until n
    invariant i >= 1 and i <= n and ok == sorted_spec(xs: xs, n: i)
    ok = ok and xs[i - 1] <= xs[i]
  end for
  return ok
end fn is_sorted
```

#### fix 3 after the new words: proved

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
    invariant i >= 1 and i <= n and ok == sorted_spec(xs: xs, n: i)
    ok = ok and xs[i - 1] <= xs[i]
  end for
  return ok
end fn is_sorted
```

#### fix 4 after the new words: proved

```cl
fn is_sorted(xs: List[Int]) -> Bool
  ensures result == sorted_spec(xs: xs, n: length(xs))
  example is_sorted([1, 2, 2, 5]) == true
  example is_sorted([1, 3, 2]) == false
  let n = length(xs)
  var ok = true
  for i in 0 until n
    invariant i >= 0 and i <= n and ok == sorted_spec(xs: xs, n: i)
    if i >= 1
      ok = ok and xs[i - 1] <= xs[i]
    end if
  end for
  return ok
end fn is_sorted
```

#### fix 5 after the new words: proved

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
    invariant i >= 1 and i <= n and ok == sorted_spec(xs: xs, n: i)
    ok = ok and xs[i - 1] <= xs[i]
  end for
  return ok
end fn is_sorted
```
