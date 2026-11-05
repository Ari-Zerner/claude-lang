# expect: example-failed
fn greet(name: String) -> String
  example greet("Ari") == "Hi, Ari"
  return "Hello, {name}!"
end fn greet

fn main() uses io
  print(greet("Ari"))
end fn main
