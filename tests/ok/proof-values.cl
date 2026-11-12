# backends: lean
# Things a contract proof used to trip on (night 8), though the invariants were right:
# an `ensures a and b` whose parts need arithmetic to follow from what's known; a value written twice
# (`xs[i]` in the body, `xs[result]` in the `ensures`; the same for `%`, `/` and a call to a function with a
# `requires`), which must be one value to the proof wherever it is written; and a contract that calls another
# function, whose definition the proof has to open. Every `ensures` here is proved.

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

# a loop proved equal to a recursive definition: the invariant and the `ensures` call `fib_spec` in three
# places, and the proof needs what `fib_spec` is
fn fib_spec(n: Int) -> Int
  requires n >= 0
  if n < 2
    return n
  end if
  return fib_spec(n - 1) + fib_spec(n - 2)
end fn fib_spec

fn fib(n: Int) -> Int
  requires n >= 0
  ensures result == fib_spec(n)
  example fib(10) == 55
  var a = 0
  var b = 1
  for i in 0 until n
    invariant a == fib_spec(i) and b == fib_spec(i + 1)
    let t = a + b
    a = b
    b = t
  end for
  return a
end fn fib

# the same with no loop and no recursion: `double` has no `ensures`, so only its definition can say this
fn double(n: Int) -> Int
  return n + n
end fn double

fn quad(n: Int) -> Int
  ensures result == double(double(n))
  example quad(3) == 12
  return 4 * n
end fn quad

fn main() uses io
  print(divide(a: 100, b: 7))
  print(find_index(xs: [1, 2, 3], want: 2))
  print(split(a: 23, b: 4))
  print(next_square(9))
  print(fib(30))
  print(quad(5))
end fn main
