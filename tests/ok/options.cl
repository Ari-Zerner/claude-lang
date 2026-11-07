# Option and Result (D24): Some/None/Ok/Err typed from context, match with bindings, ==, print,
# options inside lists and structs, nested Options, and a parse that returns a Result.
struct Item
  name: String
  price: Int
end struct Item

fn find(items: List[Item], name: String) -> Option[Int]
  example find(items: [Item(name: "a", price: 1)], name: "a") == Some(0)
  example find(items: [], name: "a") == None
  for i in 0 until length(items)
    if items[i].name == name
      return Some(i)
    end if
  end for
  return None
end fn find

fn digit(c: String) -> Result[Int, String]
  example digit("7") == Ok(7)
  example digit("x") == Err("not a digit: x")
  let digits = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
  for i in 0 until 10
    if digits[i] == c
      return Ok(i)
    end if
  end for
  return Err("not a digit: {c}")
end fn digit

fn price_of(items: List[Item], name: String) -> Result[Int, String]
  match find(items: items, name: name)
    case Some(i)
      return Ok(items[i].price)
    case None
      return Err("no {name}")
  end match
end fn price_of

fn first_even(xs: List[Int]) -> Option[Int]
  example first_even([1, 3, 4, 6]) == Some(4)
  example first_even([1]) == None
  for x in xs
    if x % 2 == 0
      return Some(x)
    end if
  end for
  return None
end fn first_even

fn main() uses io
  let items = [Item(name: "apple", price: 3), Item(name: "bread", price: 5)]
  for name in ["bread", "fig"]
    match find(items: items, name: name)
      case Some(i)
        print("{name} at {i} costs {items[i].price}")
      case None
        print("no {name}")
    end match
  end for
  print(price_of(items: items, name: "apple"))
  print(price_of(items: items, name: "fig"))
  match digit("x")
    case Ok(v)
      print(v)
    case Err(e)
      print("error: {e}")
  end match

  var best: Option[Int] = None
  for x in [5, 2, 8]
    match best
      case None
        best = Some(x)
      case Some(b)
        if x > b
          best = Some(x)
        end if
    end match
  end for
  print(best)
  print(best == Some(8))
  print(best == None)
  let maybes = [Some(1), None, Some(3)]
  print(maybes)
  var total = 0
  for m in maybes
    match m
      case Some(v)
        total = total + v
      case None
    end match
  end for
  print(total)
  let nested: Option[Option[Int]] = Some(None)
  print(nested)
  let r: Result[List[Int], String] = Ok([1, 2])
  print(r)
  print("{first_even([7, 10])} {first_even([])}")
end fn main
