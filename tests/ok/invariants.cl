# backends: lean
# `invariant` and `decreases` lines (D33) at the top of a loop's body: what holds every time the loop is about
# to test its condition, and why a `while` stops. This file only checks that they're accepted where they
# belong and leave the program's behaviour alone; proving with them comes next.
fn isqrt(n: Int) -> Int
  requires n >= 0
  ensures result * result <= n and (result + 1) * (result + 1) > n  # unproved
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
  ensures result * 2 == n * (n + 1)  # unproved
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
  ensures result >= 0  # unproved
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

# an invariant may call a function, and a loop over a list may have one that doesn't name the item
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
  table(3)
end fn main
