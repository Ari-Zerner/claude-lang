# expect: contract-placement contract-placement contract-placement contract-placement decreases-for duplicate-decreases not-bool type-mismatch contract-effect invariant-item syntax unknown-name
# `invariant` and `decreases` lines (D33): where they go, what they may say.
# fix-mentions: on a function, the words are `requires` and `ensures`
# fix-mentions: inside a loop, the word is `invariant`
# fix-mentions: for i in 0 until length(xs)
# fix-mentions: remove this line
fn noisy(n: Int) -> Int uses io
  print("n = {n}")
  return n
end fn noisy

# not a loop: on a function the words are `requires` and `ensures`
fn f(n: Int) -> Int
  invariant n >= 0
  var i = 0
  var t = 0
  while i < n
    t = t + i
    invariant t >= 0
    i = i + 1
  end while
  return t
end fn f

fn g(n: Int, xs: List[Int]) -> Int
  var t = 0
  for i in 0 until n
    decreases n - i
    t = t + i
  end for
  var k = n
  while k > 0
    decreases k
    decreases k + 1
    invariant k
    k = k - 1
  end while
  while k < n
    decreases k < n
    invariant noisy(k) >= 0
    ensures t >= 0
    k = k + 1
  end while
  for x in xs
    invariant t >= x
    invariant later >= 0
    let later = x
    t = t + later
  end for
  if t > 0
    invariant t > 0
    assert t > 0
  end if
  return t
end fn g

fn main() uses io
  print(f(3))
  print(g(n: 3, xs: [1]))
end fn main
