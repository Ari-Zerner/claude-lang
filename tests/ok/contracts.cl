# backends: lean
# Contracts (D29): `requires` is checked at each call (a break is the caller's error, at the call's line) and is
# a hypothesis inside the body, so `down` below is total (D28); `ensures` is checked at each `return`, with
# `result` naming the value. The failures are in tests/err/contracts-run.cl.
# total: down count_digits
struct Range
  lo: Int
  hi: Int
end struct Range

fn isqrt(n: Int) -> Int
  requires n >= 0
  ensures result >= 0
  ensures result * result <= n and (result + 1) * (result + 1) > n
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
  greet(2)
end fn main
