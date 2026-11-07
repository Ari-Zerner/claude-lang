# expect: type-mismatch unknown-name type-mismatch type-mismatch unknown-type unknown-type type-mismatch type-mismatch needs-type needs-type syntax unknown-name method-call non-exhaustive non-exhaustive bad-char unknown-variant syntax syntax not-bool extra-tokens type-mismatch type-mismatch
# fix-mentions: `return Some(i)`
# fix-mentions: `return Ok(1)`
# fix-mentions: `return Err("bad")`
# fix-mentions: `Option[Int]`
# fix-mentions: `i` may be missing, so unpack it first: `match i`
# fix-mentions: `case _`
# fix-mentions: `Some(2)`
fn find(xs: List[Int], x: Int) -> Option[Int]
  for i in 0 until length(xs)
    if xs[i] == x
      return i
    end if
  end for
  return null
end fn find

fn parse(s: String) -> Result[Int, String]
  if s == "1"
    return 1
  end if
  return "bad"
end fn parse

fn get(xs: Optional[int]) -> Int
  return 0
end fn get

fn main() uses io
  let xs = [1, 2, 3]
  let i = find(xs: xs, x: 2)
  print(xs[i])
  let j = i + 1
  let none = None
  let k = Ok(3)
  if let Some(v) = i
    print(v)
  end if
  let u = i.unwrap()
  match i
    case Some(v)
      print(v)
  end match
  match i
    case Some(v) => print(v)
    case Nothing
  end match
  switch i
    case Some(v)
      print(v)
    default:
      print(0)
  end match
  if i is None
    print(0)
  end if
  let m: Option[Int] = Some("a")
  print(i == 2)
end fn main
