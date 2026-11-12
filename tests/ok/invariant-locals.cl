# backends: lean
# `invariant` and `decreases` lines may use a `let` from before the loop when its value is made from the
# parameters alone, maybe through other such `let`s (D33): clc restates the definition in what it hands Lean.
# So may a `for`'s range and a `while`'s condition. Every `ensures` here is proved except the two marked.
# a local in a `for`'s invariant
fn count_pos(xs: List[Int]) -> Int
  ensures result <= length(xs)
  example count_pos([1, -2, 3]) == 2
  let n = length(xs)
  var c = 0
  for i in 0 until n
    invariant c <= i and i <= n
    if xs[i] > 0
      c = c + 1
    end if
  end for
  return c
end fn count_pos

# a range that starts at a local, made from another local
fn upper_half(n: Int) -> Int
  requires n >= 0
  ensures result == n - n / 2
  example upper_half(7) == 4
  let mid = n / 2
  let start = mid + 0
  var k = 0
  for i in start until n
    invariant k == i - start
    k = k + 1
  end for
  return k
end fn upper_half

fn clamp(x: Int, top: Int) -> Int
  requires top >= 0
  ensures result >= 0 and result <= top
  if x < 0
    return 0
  end if
  if x > top
    return top
  end if
  return x
end fn clamp

# a local made by a call; the proof needs the callee's `ensures`
fn climb(x: Int, top: Int) -> Int
  requires top >= 0
  ensures result == top
  example climb(x: 3, top: 10) == 10
  let from = clamp(x: x, top: top)
  var i = from
  while i < top
    invariant i >= from and i <= top
    decreases top - i
    i = i + 1
  end while
  return i
end fn climb

# one name, two meanings, in two branches
fn either(up: Bool, n: Int) -> Int
  requires n >= 0
  ensures result >= n
  example either(up: true, n: 3) == 6
  example either(up: false, n: 3) == 3
  var r = 0
  if up
    let goal = n * 2
    while r < goal
      invariant r <= goal
      decreases goal - r
      r = r + 1
    end while
  else
    let goal = n
    while r < goal
      invariant r <= goal
      decreases goal - r
      r = r + 1
    end while
  end if
  return r
end fn either

# a local that comes from an earlier loop isn't made from the parameters alone, so clc says it can't use it
fn twice(xs: List[Int]) -> Int
  ensures result >= 0  # unproved: tests `m`, a local variable
  example twice([1, 2]) == 2
  var t = 0
  for x in xs
    invariant t >= 0
    t = t + 1
  end for
  let m = t
  var i = 0
  while i < m
    invariant i <= m
    decreases m - i
    i = i + 1
  end while
  return i
end fn twice

# a `return` inside the loop, and a local bound
fn find_first(xs: List[Int], want: Int) -> Int
  ensures result >= -1 and result < length(xs)
  example find_first(xs: [4, 5, 6], want: 5) == 1
  let n = length(xs)
  for i in 0 until n
    invariant i <= n
    if xs[i] == want
      return i
    end if
  end for
  return -1
end fn find_first

# a `let` after an earlier loop, still made from parameters alone
fn two_loops(n: Int) -> Int
  requires n >= 0
  ensures result == n + n
  example two_loops(3) == 6
  var a = 0
  for i in 0 until n
    invariant a == i
    a = a + 1
  end for
  let stop = n + n
  while a < stop
    invariant a <= stop
    decreases stop - a
    a = a + 1
  end while
  return a
end fn two_loops

# the same limit, met in an `invariant` line
fn after(xs: List[Int]) -> Int
  ensures result >= 0  # unproved: mentions `t`, a local variable
  example after([1, 2]) == 3
  var t = 0
  for x in xs
    invariant t >= 0
    t = t + 1
  end for
  var u = 0
  for i in 0 until 3
    invariant u >= 0 and t >= 0
    u = u + 1
  end for
  return u
end fn after

fn main() uses io
  print(count_pos([1, 2, -3]))
  print(upper_half(9))
  print(climb(x: -4, top: 5))
  print(either(up: true, n: 4))
  print(twice([7, 7, 7]))
  print(find_first(xs: [1, 2, 3], want: 3))
  print(two_loops(5))
  print(after([9]))
end fn main
