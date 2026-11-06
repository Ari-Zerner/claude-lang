# Structs (D22): construction with named fields, value semantics through copies, lists of structs,
# structs in structs, a recursive tree through a list, == and print.
struct Point
  x: Int
  y: Int
end struct Point

struct Player
  name: String
  pos: Point
  scores: List[Int]
end struct Player

struct Tree
  value: Int
  children: List[Tree]
end struct Tree

fn moved(p: Point, dx: Int) -> Point
  example moved(p: Point(x: 1, y: 2), dx: 3) == Point(x: 4, y: 2)
  var q = p
  q.x = q.x + dx
  return q
end fn moved

fn total(t: Tree) -> Int
  example total(Tree(value: 1, children: [])) == 1
  var sum = t.value
  for c in t.children
    sum = sum + total(c)
  end for
  return sum
end fn total

fn main() uses io
  let a = Point(x: 1, y: 2)
  var b = a
  b.y = 10
  print(a)
  print(b)
  print(moved(p: a, dx: 5))
  print(a == Point(x: 1, y: 2))
  var p = Player(name: "Ada \"A\"", pos: a, scores: [1, 2])
  var s = p.scores
  s = append(list: s, item: 3)
  p.scores = s
  print(p)
  let snapshot = p
  p.name = "Bob"
  print("{snapshot.name} then {p.name}, at {p.pos.x}")
  var ps = [a, b]
  var first = ps[0]
  first.x = 99
  ps[0] = first
  print(ps)
  print(a)
  let leaf = Tree(value: 3, children: [])
  let t = Tree(value: 1, children: [leaf, Tree(value: 2, children: [leaf])])
  print(total(t))
  print(t)
end fn main
