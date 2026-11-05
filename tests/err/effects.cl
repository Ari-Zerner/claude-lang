# expect: missing-effect example-effect
fn shout(x: Int) uses io
  print(x)
end fn shout

fn helper(x: Int) -> Int
  example helper(1) == noisy()
  shout(x)
  return x
end fn helper

fn noisy() -> Int uses io
  return 1
end fn noisy

fn main() uses io
  print(helper(1))
end fn main
