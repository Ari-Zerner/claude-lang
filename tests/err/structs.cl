# expect: syntax syntax unknown-type syntax recursive-struct closer-name bad-char closer-kind duplicate-fn unnamed-arg bad-char syntax arg-count arg-order no-field assign-to-let no-field unused-result type-mismatch assign-to-loop-var unnamed-arg unused-result
# fix-mentions: `Point(x: 1, y: 2)`
# fix-mentions: `ps[i].x = ...`
# fix-mentions: `length(xs)`
# fix-mentions: `bx.items = append(list: bx.items, item: 2)`
# fix-mentions: `next: List[Node]`
# fix-mentions: `Point(x: 1, y: ...)`
# fix-mentions: `end struct Pair`
struct Point
  x: Int
  y: Int
end struct Point

class Box
  var w: Int
  h: int,
  items: List[Int]
end struct Box

struct Node
  next: Node
end struct Node

struct Line
  start: Point
  stop: Point
end struct

struct Pair {
  a: Int
}

fn Point(x: Int) -> Int
  return x
end fn Point

fn main() uses io
  let a = Point(1, 2)
  let b = Point { x: 1, y: 2 }
  let c = new Point(x: 1, y: 2)
  let d = Point(x: 1)
  let e = Point(y: 2, x: 1)
  var l = Line(start: a, stop: a)
  l.start.x = 5
  print(a.z)
  a.x = 3
  let xs = [1, 2]
  print(xs.length)
  var ps = [a]
  ps[0].x = 4
  Point(x: 1, y: 2)
  var bx = Box(w: 1, h: 2, items: [])
  bx.items[0] = 1
  bx.w = "wide"
  for p in ps
    p.x = 0
  end for
  append(bx.items, 2)
  print("{b} {c} {d} {e} {l} {ps} {bx}")
end fn main
