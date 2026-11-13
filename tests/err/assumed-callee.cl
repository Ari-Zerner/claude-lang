# expect: ensures-false ensures-false
# An `ensures` clc couldn't prove is still a fact to its callers' proofs (D31). When it is false somewhere, a
# caller's proof can show anything from it: `far`'s says 2000000 < 1000000 as soon as a proof looks at
# far(2000000), and Lean does prove both `ensures result == 7` below from that, though each function returns
# 3 and neither calls `far` when it runs. What keeps them from being reported proved: a proof that leans on
# another function's unproved `ensures` counts as unproved itself ("it follows from fn far's ..."), so the
# small-input search still runs on it. This test fails if such a proof is ever counted as proved.

# false only for inputs far past what the search tries, so it gets a warning, not an error
fn far(x: Int) -> Int
  ensures x < 1000000
  return x
end fn far

# the call sits in a branch no small input takes
fn in_branch(n: Int) -> Int
  ensures result == 7
  if n > 5000000
    return far(2000000)
  end if
  return 3
end fn in_branch

# only the `invariant` mentions far, and an `invariant` isn't run
fn in_invariant(n: Int) -> Int
  ensures result == 7
  var r = 3
  for i in 0 until 1
    invariant far(2000000) >= 0
    r = 3
  end for
  return r
end fn in_invariant

fn main() uses io
  print(in_branch(0))
  print(in_invariant(0))
end fn main
