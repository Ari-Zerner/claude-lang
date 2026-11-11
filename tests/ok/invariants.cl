# backends: lean
# `invariant` and `decreases` lines (D33) at the top of a loop's body: what holds every time the loop is about
# to test its condition, and why a `while` stops. With them clc proves the `ensures` of a function that has
# loops; every `ensures` here is proved except the two marked `# unproved`, which say why.
fn isqrt(n: Int) -> Int
  requires n >= 0
  ensures result * result <= n and (result + 1) * (result + 1) > n
  example isqrt(10) == 3
  var r = 0
  while (r + 1) * (r + 1) <= n
    invariant r >= 0 and r * r <= n
    decreases n - r * r
    r = r + 1
  end while
  return r
end fn isqrt

fn triangle(n: Int) -> Int
  requires n >= 0
  ensures result * 2 == n * (n + 1)
  example triangle(4) == 10
  var t = 0
  for i in 1 through n
    invariant t * 2 == (i - 1) * i
    t = t + i
  end for
  return t
end fn triangle

fn gcd(a: Int, b: Int) -> Int
  requires a >= 0 and b >= 0
  ensures result >= 0
  example gcd(a: 48, b: 36) == 12
  var x = a
  var y = b
  while y != 0
    invariant x >= 0
    invariant y >= 0
    decreases y
    let t = x % y
    x = y
    y = t
  end while
  return x
end fn gcd

# A loop over a list may have an invariant that doesn't name the item, and an invariant may call a function.
# This one is true but isn't proved: `c <= length(xs)` isn't kept by a pass as far as the invariant itself
# says (it would need "c is at most the number of items seen so far", and there's no name for that here).
fn count_big(xs: List[Int], limit: Int) -> Int
  ensures result >= 0  # unproved
  example count_big(xs: [5, 1, 9], limit: 4) == 2
  var c = 0
  for x in xs
    invariant c >= 0 and c <= length(xs)
    if x > limit
      c = c + 1
    end if
  end for
  return c
end fn count_big

# the same loop with an invariant that a pass does keep
fn count_small(xs: List[Int], limit: Int) -> Int
  ensures result >= 0
  example count_small(xs: [5, 1, 9], limit: 4) == 1
  var c = 0
  for x in xs
    invariant c >= 0
    if x <= limit
      c = c + 1
    end if
  end for
  return c
end fn count_small

# a `return` inside a loop: the `ensures` is proved for that value too, and no `invariant` line is needed
fn first_square(target: Int, lo: Int, hi: Int) -> Int
  requires lo <= hi
  ensures result >= lo and result <= hi
  example first_square(target: 10, lo: 0, hi: 9) == 4
  for i in lo until hi
    if i * i >= target
      return i
    end if
  end for
  return hi
end fn first_square

# a `while` with no `decreases`: clc can't show that it stops, and says so
fn halve(n: Int) -> Int
  requires n >= 0
  ensures result >= 0  # unproved
  example halve(40) == 2
  var k = n
  while k > 4
    invariant k >= 0
    k = k / 2
  end while
  return k
end fn halve

# nested loops, each with its own lines; an io function can have them too
fn table(n: Int) uses io
  for i in 1 through n
    invariant i >= 1
    var j = 1
    var row = 0
    while j <= i
      invariant j >= 1 and row == i * (j - 1)
      decreases i - j + 1
      row = row + i
      j = j + 1
    end while
    print("{i}: {row}")
  end for
end fn table

fn main() uses io
  print(isqrt(99))
  print(triangle(100))
  print(gcd(a: 12, b: 18))
  print(count_big(xs: [1, 2, 3, 4], limit: 2))
  print(count_small(xs: [1, 2, 3, 4], limit: 2))
  print(first_square(target: 50, lo: 0, hi: 20))
  print(halve(100))
  table(3)
end fn main
