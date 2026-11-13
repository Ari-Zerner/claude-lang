# expect: ensures-false ensures-false ensures-false
# A false `ensures` on a function with a loop must not be "proved" from the trap that reports it broken. A
# function ends in "if the `ensures` doesn't hold, trap", and to a proof a trap used to be worth 0 (false, "",
# an empty list): so an `ensures` that 0 satisfies was proved whatever the loop did, the small-input search
# never ran, and the program stopped at run time with no warning at build time. A trap is now a value nothing
# is known about. Each function here was reported proved before that.

# no invariant
fn down(n: Int) -> Int
  ensures result >= 0
  var t = 0
  for i in 0 until n
    t = t - 1
  end for
  return t
end fn down

# an invariant that is true and kept, and no help
fn down_too(n: Int) -> Int
  ensures result >= 0
  var t = 0
  for i in 0 until n
    invariant t <= 0
    t = t - 1
  end for
  return t
end fn down_too

# a `while`, and a Bool: false is what a trapped Bool used to be worth
fn all_small(n: Int) -> Bool
  requires n >= 0
  ensures result == false
  var k = 0
  while k < n
    invariant k >= 0
    decreases n - k
    k = k + 1
  end while
  return k >= 0
end fn all_small

fn main() uses io
  print(down(0))
end fn main
