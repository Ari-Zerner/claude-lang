# expect: unknown-type bad-char unclosed-string bad-escape empty-interpolation nested-string type-mismatch
# fix-mentions: `"hi"`
# fix-mentions: interpolation
fn greet(name: str) -> String
  example greet(name: "Ari") == "Hi, Ari"
  return "Hello, {name}!"
end fn greet

fn main() uses io
  print('hi')
  print("unclosed)
  print("bad \q escape {}")
  print("nested {greet("x")} ok")
  print("x" + 1)
end fn main
