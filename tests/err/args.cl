# expect: arg-order unnamed-arg unknown-fn unknown-arg-name
fn sub(a: Int, b: Int) -> Int
  return a - b
end fn sub

fn main() uses io
  print(sub(b: 1, a: 2))
  print(sub(1, 2))
  println(3)
  print(sub(a: 1, c: 2))
end fn main
