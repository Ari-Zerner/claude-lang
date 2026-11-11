# backends: lean
# Contracts (D29): `requires` is checked at each call (a break is the caller's error, at the call's line) and is
# a hypothesis inside the body, so `down` below is total (D28); `ensures` is checked at each `return`, with
# `result` naming the value. The failures are in tests/err/contracts-run.cl.
# total: down count_digits
# An `ensures` marked `# unproved` must be one clc can't prove (D30), and every other must be proved: isqrt's
# (a `while` loop), wrong_abs's (false for x < -5000, which nothing here reaches), steps's (clc can't show it
# stops) and double_abs's (it follows from wrong_abs's, D31). digits_plus is proved from count_digits's.
# None of them has a small counterexample (D32): those are in tests/err/contracts-search.cl.
struct Range
  lo: Int
  hi: Int
end struct Range

fn isqrt(n: Int) -> Int
  requires n >= 0
  ensures result >= 0  # unproved
  ensures result * result <= n and (result + 1) * (result + 1) > n  # unproved
  example isqrt(10) == 3
  example isqrt(0) == 0
  var r = 0
  while (r + 1) * (r + 1) <= n
    r = r + 1
  end while
  return r
end fn isqrt

# never stops for a negative n, but `requires` rules that out
fn down(n: Int) -> Int
  requires n >= 0
  ensures result == 0
  example down(3) == 0
  if n == 0
    return 0
  end if
  return down(n - 1)
end fn down

fn count_digits(n: Int) -> Int
  requires n >= 0
  ensures result >= 1
  example count_digits(0) == 1
  example count_digits(12345) == 5
  if n < 10
    return 1
  end if
  return 1 + count_digits(n / 10)
end fn count_digits

fn width(r: Range) -> Int
  requires r.lo <= r.hi
  ensures result >= 0
  example width(Range(lo: 2, hi: 5)) == 3
  return r.hi - r.lo
end fn width

fn clamp(x: Int, lo: Int, hi: Int) -> Int
  requires lo <= hi
  ensures lo <= result and result <= hi
  example clamp(x: 15, lo: 0, hi: 10) == 10
  if x < lo
    return lo
  else if x > hi
    return hi
  end if
  return x
end fn clamp

# false for x < -5000, which no example or call reaches and the small-input search (D32) doesn't either:
# checked at run time, and not proved
fn wrong_abs(x: Int) -> Int
  ensures result >= 0  # unproved
  example wrong_abs(-3) == 3
  if x < -5000
    return x
  end if
  if x < 0
    return -x
  end if
  return x
end fn wrong_abs

# always stops, but by flipping the sign first, which none of D28's measures covers
fn steps(n: Int) -> Int
  ensures result >= 0  # unproved
  example steps(-2) == 2
  if n < 0
    return steps(-n)
  end if
  if n == 0
    return 0
  end if
  return 1 + steps(n - 1)
end fn steps

# proved from count_digits's `ensures`, whose `requires` this one's `requires` gives (D31)
fn digits_plus(n: Int) -> Int
  requires n >= 0
  ensures result >= 2
  example digits_plus(5) == 2
  return count_digits(n) + 1
end fn digits_plus

# would follow from wrong_abs's `ensures`, which isn't proved
fn double_abs(x: Int) -> Int
  ensures result >= 0  # unproved
  example double_abs(-3) == 6
  return 2 * wrong_abs(x)
end fn double_abs

fn greet(times: Int) uses io
  requires times >= 1
  for i in 1 through times
    print("hello {i}")
  end for
end fn greet

fn main() uses io
  print(isqrt(99))
  print(down(5))
  print(count_digits(1000000))
  print(width(Range(lo: -3, hi: 4)))
  print(clamp(x: -4, lo: 0, hi: 10))
  print(wrong_abs(-2))
  print(steps(-3))
  print(digits_plus(123))
  print(double_abs(4))
  greet(2)
end fn main
