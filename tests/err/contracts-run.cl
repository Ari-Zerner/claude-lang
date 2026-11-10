# expect: example-crashed
# A `requires` broken by an example stops it at the example's call.
fn down(n: Int) -> Int
  requires n >= 0
  example down(-1) == 0
  if n == 0
    return 0
  end if
  return down(n - 1)
end fn down

fn main() uses io
  print(down(2))
end fn main
