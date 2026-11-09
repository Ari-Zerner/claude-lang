# io calls run only when evaluated: the right side of and/or, an else-if condition, each while condition.
# (Lean lifts (<- ...) to the statement, so the Lean backend has to keep these under an if.)
fn noisy(tag: String, v: Bool) -> Bool uses io
  print("  called {tag}")
  return v
end fn noisy

fn main() uses io
  print("and:")
  print(false and noisy(tag: "and-right", v: true))
  print(noisy(tag: "and-left", v: true) and noisy(tag: "and-right2", v: false))
  print("or:")
  print(true or noisy(tag: "or-right", v: false))
  print("else if:")
  if true
    print("  first branch")
  else if noisy(tag: "else-if", v: true)
    print("  second branch")
  end if
  print("while:")
  var n = 0
  while noisy(tag: "while {n}", v: n < 2)
    n = n + 1
  end while
end fn main
