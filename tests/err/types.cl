# expect: not-bool type-mismatch assign-to-let missing-return unused-result bad-char
fn f(x: Int) -> Int
  if x
    return 1
  end if
end fn f

fn main() uses io
  let y = 3
  y = 4
  let z: Bool = 5
  f(1)
  print(true && false)
end fn main
