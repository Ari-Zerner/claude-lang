fn greet(name: String) -> String
  example greet("Ari") == "Hello, Ari!"
  return "Hello, {name}!"
end fn greet

fn main() uses io
  print(greet("world"))
  var row = ""
  var i = 1
  while i <= 4
    row = "{row} {i * 3}"
    i = i + 1
  end while
  print(row)
  print("tab:\t|brace: \{x\}|quote: \"|bool: {3 > 2}|é ?? ok")
  let a = "x"
  print(a == "x" and "{a}{a}" != "x")
  # D25: a `{` right before the closing quote is a literal brace
  print("{")
  print(["{", "}"])
  print("{" == "\{")
  print("{a}{")
end fn main
