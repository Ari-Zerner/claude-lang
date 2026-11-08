# expect: unclosed-interpolation unclosed-interpolation
# fix-mentions: `"\{x"`
# A `{` with no `}` gets one error at the brace, with the escaped string as the fix, not a second
# "no closing quote" (the string has one). A `{` right before the closing quote is a literal brace
# (D25; tests/ok/strings.cl), so `"{"` is fine.
fn label(x: Int) -> String
  return "{x"
end fn label

fn main() uses io
  print("{")
  print("set {x")
  print(label(x: 1))
end fn main
