# backends: lean
# When a loop's `ensures` isn't proved, the warning says which loop and which of the three things an invariant
# must do clc couldn't show (D33): be true when the loop starts, be kept by a pass, say enough once the loop
# is over. Every `ensures` here is true (so the small-input search finds nothing) and none is proved.

# false at the start: `c >= 1` when `c` is still 0
fn count_up(n: Int) -> Int
  requires n >= 0
  ensures result == n  # unproved: clc couldn't show that `invariant c == i and c >= 1` is true when the `for` on line 11 starts; clc called
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
  ensures result >= 0  # unproved: clc couldn't show that a pass of the `while` on line 23 keeps `invariant m >= 0` true and makes `decreases n - m` smaller while it stays at 0 or above; clc called
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
  ensures result == 2 * n  # unproved: clc couldn't show that this `ensures` follows from what is true when the `for` on line 36 ends (`invariant t >= 0`, and that the loop is over); clc called
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
  ensures result >= 0  # unproved: the `for` on line 48 has no `invariant` line saying what stays true as it runs, and without one clc couldn't show this `ensures` after the loop; clc called
  var t = 0
  for i in 0 until n
    t = t + i
  end for
  return t
end fn total

# two loops: the first is fine, the second's invariant is off by one, so it fails at its start and at its end
fn twice(n: Int) -> Int
  requires n >= 0
  ensures result == 2 * n  # unproved: clc couldn't show that its 2 `invariant` lines are true when the `for` on line 63 starts; also, clc couldn't show that this `ensures` follows from what is true when the `for` on line 63 ends (its 2 `invariant` lines, and that the loop is over); clc called
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
  ensures result >= 0  # unproved: clc couldn't show that a pass of the `for` on line 75 returns only a value that meets this `ensures`; clc called
  var c = 0
  for i in 0 until n
    if i * i > 50
      return c
    end if
    c = c + 1
  end for
  return 0
end fn count_until

fn main() uses io
  print(count_up(4))
  print(halve_down(9))
  print(double(5))
  print(total(4))
  print(twice(3))
  print(count_until(20))
end fn main
