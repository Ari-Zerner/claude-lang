# Spec trial 2026-11-06-1502 (structs tasks, sonnet)

| task | result |
|---|---|
| point-move | first try |
| rect | first try |
| scores | after one fix |
| bank | first try |
| copy | first try |
| segment | first try |
| inventory | first try |
| tree | first try |
| equal | first try |
| book | first try |
| by-age | first try |

## point-move

Task: Define a point type with x and y. Write a function that returns a point moved by dx and dy. Move the point (2, 3) by (1, -1) and print the new point's x, then its y, on separate lines.

### attempt 1: OK

```cl
struct Point
  x: Int
  y: Int
end struct Point

fn move(p: Point, dx: Int, dy: Int) -> Point
  example move(p: Point(x: 2, y: 3), dx: 1, dy: -1) == Point(x: 3, y: 2)
  return Point(x: p.x + dx, y: p.y + dy)
end fn move

fn main() uses io
  let p = Point(x: 2, y: 3)
  let q = move(p: p, dx: 1, dy: -1)
  print(q.x)
  print(q.y)
end fn main
```

## rect

Task: Define a rectangle type with a width and a height, with ways to compute its area and its perimeter. Print the area, then the perimeter, of a 3 by 4 rectangle.

### attempt 1: OK

```cl
struct Rect
  width: Int
  height: Int
end struct Rect

fn area(r: Rect) -> Int
  example area(Rect(width: 3, height: 4)) == 12
  return r.width * r.height
end fn area

fn perimeter(r: Rect) -> Int
  example perimeter(Rect(width: 3, height: 4)) == 14
  return 2 * (r.width + r.height)
end fn perimeter

fn main() uses io
  let r = Rect(width: 3, height: 4)
  print(area(r))
  print(perimeter(r))
end fn main
```

## scores

Task: Keep a list of players, each with a name and a score: Ann, Bob and Cy, all starting at 0. Add 5 to Bob's score twice and 3 to Cy's score once, then print each player as their name and score, like `Ann 0`, one per line.

### attempt 1: exit 1

```cl
struct Player
  name: String
  score: Int
end struct Player

fn add_score(players: List[Player], name: String, amount: Int) -> List[Player]
  var ps = players
  for i in 0 until length(ps)
    if ps[i].name == name
      ps[i].score = ps[i].score + amount
    end if
  end for
  return ps
end fn add_score

fn main() uses io
  var players = [Player(name: "Ann", score: 0), Player(name: "Bob", score: 0), Player(name: "Cy", score: 0)]
  players = add_score(players: players, name: "Bob", amount: 5)
  players = add_score(players: players, name: "Bob", amount: 5)
  players = add_score(players: players, name: "Cy", amount: 3)
  for p in players
    print("{p.name} {p.score}")
  end for
end fn main
```

Compiler:
```
prog.cl:10:7: error[nested-assign]: only one level can be assigned at a time
   10 |       ps[i].score = ps[i].score + amount
      |       ^^^^^^^^^^^
  fix: `var item = ps[i]`, then `item.score = ps[i].score + amount`, then `ps[i] = item`
1 error(s), 0 warning(s)
```

_Sent the diagnostics back for a fix._

### attempt 2: OK

```cl
struct Player
  name: String
  score: Int
end struct Player

fn add_score(players: List[Player], name: String, amount: Int) -> List[Player]
  var ps = players
  for i in 0 until length(ps)
    if ps[i].name == name
      var item = ps[i]
      item.score = item.score + amount
      ps[i] = item
    end if
  end for
  return ps
end fn add_score

fn main() uses io
  var players = [Player(name: "Ann", score: 0), Player(name: "Bob", score: 0), Player(name: "Cy", score: 0)]
  players = add_score(players: players, name: "Bob", amount: 5)
  players = add_score(players: players, name: "Bob", amount: 5)
  players = add_score(players: players, name: "Cy", amount: 3)
  for p in players
    print("{p.name} {p.score}")
  end for
end fn main
```

## bank

Task: An account has an owner and a balance. Write a function that deposits an amount into an account. Open an account for Dee with balance 100, deposit 50 into it, then print its balance.

### attempt 1: OK

```cl
struct Account
  owner: String
  balance: Int
end struct Account

fn deposit(acct: Account, amount: Int) -> Account
  example deposit(acct: Account(owner: "Dee", balance: 100), amount: 50) == Account(owner: "Dee", balance: 150)
  var result = acct
  result.balance = result.balance + amount
  return result
end fn deposit

fn main() uses io
  var acct = Account(owner: "Dee", balance: 100)
  acct = deposit(acct: acct, amount: 50)
  print(acct.balance)
end fn main
```

## copy

Task: Make a point p at (1, 2). Make q a copy of p, then set q's x to 10. Print p's x, then q's x.

### attempt 1: OK

```cl
struct Point
  x: Int
  y: Int
end struct Point

fn main() uses io
  let p = Point(x: 1, y: 2)
  var q = p
  q.x = 10
  print(p.x)
  print(q.x)
end fn main
```

## segment

Task: A line segment has a start point and an end point. Write a function that returns a segment's squared length. Make the segment from (3, 4) to (6, 8) and print its squared length; then change its start point's x to 0 and print its squared length again.

### attempt 1: OK

```cl
struct Point
  x: Int
  y: Int
end struct Point

struct Segment
  first: Point
  last: Point
end struct Segment

fn squared_length(s: Segment) -> Int
  example squared_length(Segment(first: Point(x: 3, y: 4), last: Point(x: 6, y: 8))) == 25
  example squared_length(Segment(first: Point(x: 0, y: 0), last: Point(x: 0, y: 0))) == 0
  let dx = s.last.x - s.first.x
  let dy = s.last.y - s.first.y
  return dx * dx + dy * dy
end fn squared_length

fn main() uses io
  var seg = Segment(first: Point(x: 3, y: 4), last: Point(x: 6, y: 8))
  print(squared_length(seg))
  var p = seg.first
  p.x = 0
  seg.first = p
  print(squared_length(seg))
end fn main
```

## inventory

Task: An inventory has an owner's name and a list of item names. Write a function that adds an item to an inventory. Start Eve with an empty inventory, add sword, then shield, then print the number of items, then the last item.

### attempt 1: OK

```cl
struct Inventory
  owner: String
  items: List[String]
end struct Inventory

fn add_item(inv: Inventory, item: String) -> Inventory
  var result = inv
  result.items = append(list: result.items, item: item)
  return result
end fn add_item

fn main() uses io
  let none: List[String] = []
  var eve = Inventory(owner: "Eve", items: none)
  eve = add_item(inv: eve, item: "sword")
  eve = add_item(inv: eve, item: "shield")
  print(length(eve.items))
  print(eve.items[length(eve.items) - 1])
end fn main
```

## tree

Task: Define a tree where each node has an Int value and any number of children. Build the tree whose root is 1, with children 2 (whose children are 4 and 5) and 3. Print the sum of all values, then the tree's depth (a single node has depth 1).

### attempt 1: OK

```cl
struct Tree
  value: Int
  children: List[Tree]
end struct Tree

fn total(t: Tree) -> Int
  var s = t.value
  for c in t.children
    s = s + total(c)
  end for
  return s
end fn total

fn depth(t: Tree) -> Int
  var best = 0
  for c in t.children
    let d = depth(c)
    if d > best
      best = d
    end if
  end for
  return best + 1
end fn depth

fn main() uses io
  let none: List[Tree] = []
  let n4 = Tree(value: 4, children: none)
  let n5 = Tree(value: 5, children: none)
  let n3 = Tree(value: 3, children: none)
  var kids2: List[Tree] = []
  kids2 = append(list: kids2, item: n4)
  kids2 = append(list: kids2, item: n5)
  let n2 = Tree(value: 2, children: kids2)
  var kids1: List[Tree] = []
  kids1 = append(list: kids1, item: n2)
  kids1 = append(list: kids1, item: n3)
  let root = Tree(value: 1, children: kids1)
  print(total(root))
  print(depth(root))
end fn main
```

## equal

Task: Make two points at (1, 2) and a third at (2, 1). Print whether the first two are equal, then whether the first and third are equal.

### attempt 1: OK

```cl
struct Point
  x: Int
  y: Int
end struct Point

fn main() uses io
  let a = Point(x: 1, y: 2)
  let b = Point(x: 1, y: 2)
  let c = Point(x: 2, y: 1)
  print(a == b)
  print(a == c)
end fn main
```

## book

Task: Define a struct named Book with fields title (a String) and year (an Int), in that order. Make the book Dune from 1965 and print it by passing the struct itself to print.

### attempt 1: OK

```cl
struct Book
  title: String
  year: Int
end struct Book

fn main() uses io
  let b = Book(title: "Dune", year: 1965)
  print(b)
end fn main
```

## by-age

Task: People have a name and an age: Ann is 31, Bob is 25, Cy is 40. Sort them by age, youngest first, with a sort you write yourself, and print their names, one per line.

### attempt 1: OK

```cl
struct Person
  name: String
  age: Int
end struct Person

fn sort_by_age(people: List[Person]) -> List[Person]
  var xs = people
  for i in 1 until length(xs)
    var j = i
    while j > 0 and xs[j - 1].age > xs[j].age
      let a = xs[j - 1]
      let b = xs[j]
      xs[j - 1] = b
      xs[j] = a
      j = j - 1
    end while
  end for
  return xs
end fn sort_by_age

fn main() uses io
  let people = [Person(name: "Ann", age: 31), Person(name: "Bob", age: 25), Person(name: "Cy", age: 40)]
  let ordered = sort_by_age(people)
  for p in ordered
    print(p.name)
  end for
end fn main
```
