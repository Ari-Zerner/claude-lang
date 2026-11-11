# expect: example-crashed
# backends: lean
# An example that recurses without end stops the build within seconds (clc gives Lean a 64 MB stack), not
# after minutes and gigabytes. On C the same example overflows the stack or times out, depending on gcc.
fn count(n: Int) -> Int
  example count(3) == 3
  example count(-1) == 0
  if n == 0
    return 0
  end if
  return 1 + count(n - 1)
end fn count

fn main() uses io
  print(count(2))
end fn main
