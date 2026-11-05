fn factorial(n: Int) -> Int
  example factorial(0) == 1
  example factorial(5) == 120
  var result = 1
  var i = 2
  while i <= n
    result = result * i
    i = i + 1
  end while
  return result
end fn factorial

fn sign(x: Int) -> Int
  example sign(-4) == -1
  example sign(0) == 0
  if x < 0
    return -1
  else if x == 0
    return 0
  else
    return 1
  end if
end fn sign

fn is_even(n: Int) -> Bool
  example is_even(4)
  example not is_even(7)
  return n % 2 == 0
end fn is_even

fn main() uses io
  print(factorial(10))
  print(sign(-7))
  print(is_even(10) and not is_even(3))
  let _ = factorial(3)
end fn main
