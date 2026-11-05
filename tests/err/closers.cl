# expect: closer-mismatch closer-name stray-closer
fn f(x: Int) -> Int
  while x > 0
    if x == 3
      return x
  end while
  return 0
end fn g

fn main() uses io
  print(f(3))
  end if
end fn main
