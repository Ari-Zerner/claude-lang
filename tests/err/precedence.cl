# expect: mixed-and-or chained-comparison ambiguous-division not-scope
fn main() uses io
  let a = 1
  let b = 2
  print(a < b and b < 3 or a == 1)
  print(a < b < 3)
  print(a / b * 2)
  print(not a == b)
end fn main
