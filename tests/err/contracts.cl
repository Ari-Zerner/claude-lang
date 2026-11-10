# expect: not-bool contract-unit contract-placement reserved-name contract-effect contract-main
fn f(n: Int) -> Int
  requires n
  ensures result >= 0
  return n
end fn f

fn g(n: Int)
  ensures n >= 0
  let x = n
  requires x > 0
end fn g

fn h(result: Int) -> Int
  ensures result >= 0
  return 1
end fn h

fn ask() -> Int uses io
  print("?")
  return 1
end fn ask

fn k(n: Int) -> Int uses io
  ensures result >= ask()
  return n
end fn k

fn main() uses io
  requires true
  print(f(1))
end fn main
