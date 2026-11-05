# expect: example-failed
fn double(x: Int) -> Int
  example double(3) == 6
  example double(4) == 9
  return x + x
end fn double

fn main() uses io
  print(double(2))
end fn main
