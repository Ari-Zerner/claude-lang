# backends: lean
# Two things a contract proof used to trip on (night 8), though the invariants were right:
# an `ensures a and b` whose parts need arithmetic to follow from what's known, and a value written twice
# (`xs[i]` in the body, `xs[result]` in the `ensures`; the same for `%` and `/`), which must be one value to
# the proof wherever it is written. Every `ensures` here is proved.

# division by repeated subtraction: `a < (q + 1) * b` follows from `q * b + r == a` and `r < b`
fn divide(a: Int, b: Int) -> Int
  requires a >= 0 and b > 0
  ensures result * b <= a and a < (result + 1) * b
  example divide(a: 17, b: 5) == 3
  var q = 0
  var r = a
  while r >= b
    invariant r >= 0 and q * b + r == a
    decreases r
    r = r - b
    q = q + 1
  end while
  return q
end fn divide

# the `ensures` indexes the list at another place in the file than the body does
fn find_index(xs: List[Int], want: Int) -> Int
  ensures result == -1 or (result >= 0 and result < length(xs) and xs[result] == want)
  example find_index(xs: [4, 5, 6], want: 6) == 2
  example find_index(xs: [4, 5, 6], want: 7) == -1
  for i in 0 until length(xs)
    if xs[i] == want
      return i
    end if
  end for
  return -1
end fn find_index

# the same for `%` and `/`, with no loop
fn split(a: Int, b: Int) -> Int
  requires b > 0
  ensures result == a / b + a % b
  example split(a: 17, b: 5) == 5
  let q = a / b
  let r = a % b
  return q + r
end fn split

# a two-part `ensures` with no loop, where the second part needs `(n + 1) * (n + 1)` multiplied out
fn next_square(n: Int) -> Int
  requires n >= 0
  ensures result > n * n and result == (n + 1) * (n + 1)
  example next_square(3) == 16
  return n * n + 2 * n + 1
end fn next_square

fn main() uses io
  print(divide(a: 100, b: 7))
  print(find_index(xs: [1, 2, 3], want: 2))
  print(split(a: 23, b: 4))
  print(next_square(9))
end fn main
