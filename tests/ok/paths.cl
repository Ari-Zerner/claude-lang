# Assignment paths (D23): ps[i].score = v, grid[i][j] = v, a.b.c = v, p.items[0] = v, with value
# semantics at every level, the value computed before the path is walked, and in-place append through a path.
struct Point
  x: Int
  y: Int
end struct Point

struct Line
  start: Point
  stop: Point
end struct Line

struct Player
  name: String
  score: Int
  tags: List[String]
end struct Player

struct Node
  value: Int
  kids: List[Node]
end struct Node

fn bumped(ps: List[Player], by: Int) -> List[Player]
  example bumped(ps: [Player(name: "a", score: 1, tags: [])], by: 5) == [Player(name: "a", score: 6, tags: [])]
  var out = ps
  for i in 0 until length(out)
    out[i].score = out[i].score + by
  end for
  return out
end fn bumped

fn identity(n: Int) -> List[List[Int]]
  example identity(n: 2) == [[1, 0], [0, 1]]
  var grid = repeat(item: repeat(item: 0, times: n), times: n)
  for i in 0 until n
    grid[i][i] = 1
  end for
  return grid
end fn identity

fn main() uses io
  let team = [Player(name: "Ada", score: 10, tags: []), Player(name: "Bob", score: 20, tags: ["new"])]
  let up = bumped(ps: team, by: 5)
  print("{team[0].score} {team[1].score} -> {up[0].score} {up[1].score}")

  # Every level is its own value: a copy taken before the change keeps the old value.
  var ps = team
  let before = ps
  let first = ps[0]
  ps[0].tags = append(list: ps[0].tags, item: "captain")
  ps[1].tags[0] = "veteran"
  print(ps)
  print(before == team)
  print(first)

  # A grid shares its rows until one changes.
  var grid = repeat(item: repeat(item: 0, times: 3), times: 2)
  let row = grid[1]
  grid[1][2] = 7
  grid[0][grid[1][2] - 7] = 1
  print("{grid} {row}")
  print(identity(n: 3))

  # Struct in struct.
  var l = Line(start: Point(x: 1, y: 2), stop: Point(x: 3, y: 4))
  let old = l
  l.start.x = 5
  l.stop.y = l.start.x * 10
  print("{l} {old.start}")

  # The value is computed first, so a node can be added under itself without making a cycle.
  var t = Node(value: 1, kids: [])
  t.kids = append(list: t.kids, item: t)
  t.kids[0].value = 2
  t.kids[0].kids = append(list: t.kids[0].kids, item: t)
  print(t)

  # Appending through a path grows the list in place.
  var big = [Player(name: "x", score: 0, tags: [])]
  for i in 0 until 100000
    big[0].tags = append(list: big[0].tags, item: "t")
    big[0].score = big[0].score + i
  end for
  print("{length(big[0].tags)} {big[0].score}")
end fn main
