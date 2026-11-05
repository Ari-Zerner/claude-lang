# expect: closer-mismatch syntax
# fix-mentions: above line 11 (`i = i + 1`)
# fix-mentions: `else if x == 0`
fn divisor_sum(n: Int) -> Int
  var total = 0
  var i = 1
  while i < n
    if n % i == 0
      total = total + i
    # comment lines don't count
    i = i + 1
  end while
  return total
end fn divisor_sum

fn sign(x: Int) -> Int
  if x < 0
    return -1
  elif x == 0
    return 0
  else
    return 1
  end if
end fn sign

fn main() uses io
  print(divisor_sum(28))
  print(sign(-2))
end fn main
