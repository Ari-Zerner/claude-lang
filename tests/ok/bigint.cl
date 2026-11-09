# backends: lean
# Int has no size limit (D26): these pass 64 bits, where the C backend stops with an overflow error.
fn factorial(n: Int) -> Int
  example factorial(5) == 120
  example factorial(21) == 51090942171709440000
  var r = 1
  for i in 2 through n
    r = r * i
  end for
  return r
end fn factorial

fn main() uses io
  print(factorial(30))
  var p = 1
  for i in 1 through 100
    p = p * 2
  end for
  print("2^100 = {p}")
  print("{-p / 3} {-p % 3}")
end fn main
