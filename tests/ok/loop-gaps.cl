# backends: lean
# When a loop's `ensures` isn't proved, the warning says which loop and which of the three things an invariant
# must do clc couldn't show (D33): be true when the loop starts, be kept by a pass, say enough once the loop
# is over. For the first two it names the `invariant` line, and for a pass it says which of its jobs: keeping
# a line, making the `decreases` smaller, returning only what meets the `ensures`. Every `ensures` here is true
# (so the small-input search finds nothing) and none is proved.

# false at the start: `c >= 1` when `c` is still 0
fn count_up(n: Int) -> Int
  requires n >= 0
  ensures result == n  # unproved: clc couldn't show that `invariant c == i and c >= 1` is true when the `for` on line 13 starts; clc called
  var c = 0
  for i in 0 until n
    invariant c == i and c >= 1
    c = c + 1
  end for
  return c
end fn count_up

# a pass doesn't make the `decreases` smaller: `n - m` grows as `m` shrinks
fn halve_down(n: Int) -> Int
  requires n >= 0
  ensures result >= 0  # unproved: clc couldn't show that a pass of the `while` on line 25 makes `decreases n - m` smaller while it stays at 0 or above; clc called
  var m = n
  while m > 0
    invariant m >= 0
    decreases n - m
    m = m / 2
  end while
  return m
end fn halve_down

# true at the start and kept, but it says too little
fn double(n: Int) -> Int
  requires n >= 0
  ensures result == 2 * n  # unproved: clc couldn't show that this `ensures` follows from what is true when the `for` on line 38 ends (`invariant t >= 0`, and that the loop is over); clc called
  var t = 0
  for i in 0 until n
    invariant t >= 0
    t = t + 2
  end for
  return t
end fn double

# no `invariant` at all
fn total(n: Int) -> Int
  requires n >= 0
  ensures result >= 0  # unproved: the `for` on line 50 has no `invariant` line saying what stays true as it runs, and without one clc couldn't show this `ensures` after the loop; clc called
  var t = 0
  for i in 0 until n
    t = t + i
  end for
  return t
end fn total

# two loops: the first is fine, the second's invariant is off by one, so it fails at its start and at its end
fn twice(n: Int) -> Int
  requires n >= 0
  ensures result == 2 * n  # unproved: clc couldn't show that `invariant a == n + j + 1` is true when the `for` on line 65 starts; also, clc couldn't show that this `ensures` follows from what is true when the `for` on line 65 ends (its 2 `invariant` lines, and that the loop is over); clc called
  var a = 0
  for i in 0 until n
    invariant a == i
    a = a + 1
  end for
  for j in 0 until n
    invariant a >= 0
    invariant a == n + j + 1
    a = a + 1
  end for
  return a
end fn twice

# a `return` inside the loop is part of what a pass must get right: nothing says `c >= 0` there
fn count_until(n: Int) -> Int
  ensures result >= 0  # unproved: clc couldn't show that a pass of the `for` on line 77 returns only a value that meets this `ensures`; clc called
  var c = 0
  for i in 0 until n
    if i * i > 50
      return c
    end if
    c = c + 1
  end for
  return 0
end fn count_until

# two `invariant` lines, and a pass keeps only the first: the warning names the other
fn two_lines(n: Int) -> Int
  requires n >= 0
  ensures result == n  # unproved: clc couldn't show that a pass of the `for` on line 92 keeps `invariant s == i` true; clc called
  var r = 0
  var s = 0
  for i in 0 until n
    invariant r == i
    invariant s == i
    r = r + 1
    s = s + 2
  end for
  return r
end fn two_lines

# a `while` whose `decreases` is fine, but a pass doesn't keep its second line
fn drain(n: Int) -> Int
  requires n >= 0
  ensures result == 0  # unproved: clc couldn't show that a pass of the `while` on line 107 keeps `invariant seen <= 3` true; clc called
  var k = n
  var seen = 0
  while k > 0
    invariant k >= 0
    invariant seen <= 3
    decreases k
    k = k - 1
    seen = seen + 1
  end while
  return k
end fn drain

# a `while` with a `return`: its lines and its `decreases` are fine, the returned value is what's unknown
fn steps_until(n: Int) -> Int
  requires n >= 0
  ensures result >= 0  # unproved: clc couldn't show that a pass of the `while` on line 123 returns only a value that meets this `ensures`; clc called
  var k = n
  var c = 0
  while k > 0
    invariant k >= 0
    decreases k
    if k * k < 50
      return c
    end if
    k = k - 1
    c = c + 1
  end while
  return 0
end fn steps_until

fn main() uses io
  print(count_up(4))
  print(halve_down(9))
  print(double(5))
  print(total(4))
  print(twice(3))
  print(count_until(20))
  print(two_lines(3))
  print(drain(5))
  print(steps_until(10))
end fn main
