# expect: ensures-false input-crashed input-crashed input-crashed
# The small-input search (D32): clc calls each function with an unproved `ensures` on small inputs that its
# `requires` allow. A call that returns something the `ensures` rules out is `ensures-false`; one that stops
# the program (a bad index, a callee's broken `requires`) or recurses forever is `input-crashed`. No example
# here fails: every example passes, and each bug is one the examples miss.
# fix-mentions: calling fn wrong_abs on small inputs
# fix-mentions: add a `requires` that rules this call out

# false for x < -5: found at x = -6
fn wrong_abs(x: Int) -> Int
  ensures result >= 0
  example wrong_abs(-3) == 3
  if x < -5
    return x
  end if
  if x < 0
    return -x
  end if
  return x
end fn wrong_abs

# stopped by wrong_abs's check at x = -6, which wrong_abs's own error already says: not reported again
fn double_abs(x: Int) -> Int
  ensures result >= 0
  example double_abs(-3) == 6
  return 2 * wrong_abs(x)
end fn double_abs

# an empty list has no largest item
fn largest(xs: List[Int]) -> Int
  ensures result >= xs[0]
  example largest([3, 9, 4]) == 9
  var best = xs[0]
  for x in xs
    if x > best
      best = x
    end if
  end for
  return best
end fn largest

fn count_digits(n: Int) -> Int
  requires n >= 0
  ensures result >= 1
  example count_digits(12345) == 5
  if n < 10
    return 1
  end if
  return 1 + count_digits(n / 10)
end fn count_digits

# breaks count_digits's `requires` for a negative n
fn digits_twice(n: Int) -> Int
  ensures result >= 2
  example digits_twice(77) == 4
  var d = 0
  for i in 0 until 2
    d = d + count_digits(n)
  end for
  return d
end fn digits_twice

# never stops for a negative n
fn spin(n: Int) -> Int
  ensures result == 0
  example spin(3) == 0
  if n == 0
    return 0
  end if
  return spin(n - 1)
end fn spin

fn main() uses io
  print(wrong_abs(4))
  print(double_abs(4))
  print(largest([1, 2]))
  print(digits_twice(5))
  print(spin(2))
end fn main
