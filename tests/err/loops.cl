# expect: unknown-fn unknown-fn range-to assign-to-loop-var bad-char syntax syntax not-a-list not-a-list duplicate-name outside-loop stray-closer closer-mismatch missing-return
# fix-mentions: `for i in 0 until n`
# fix-mentions: `for i in 0 through n - 1 reversed`
# fix-mentions: `for i in 1 through n` (includes n)
fn f(xs: List[Int], n: Int) -> Int
  for i in range(n)
    let a = i
  end for
  for i in range(n - 1, -1, -1)
    let b = i
  end for
  for i in 1 to n
    i = i + 1
  end for
  for i in 0..n
    let c = i
  end for
  for (i = 0; i < n; i++)
  end for
  for i, x in xs
  end for
  for x in n
  end for
  for x in "abc"
  end for
  for n in xs
  end for
  break
  for x in xs
    let d = x
  end while
  return 0
end fn f

fn main() uses io
  print(f(xs: [1], n: 2))
end fn main
