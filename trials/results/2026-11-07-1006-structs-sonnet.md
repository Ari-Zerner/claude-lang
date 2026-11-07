# Spec trial 2026-11-07-1006 (structs tasks, sonnet)

| task | result |
|---|---|
| scores | first try |
| segment | first try |

## scores

Task: Keep a list of players, each with a name and a score: Ann, Bob and Cy, all starting at 0. Add 5 to Bob's score twice and 3 to Cy's score once, then print each player as their name and score, like `Ann 0`, one per line.

### attempt 1: OK

```cl
struct Player
  name: String
  score: Int
end struct Player

fn main() uses io
  var players: List[Player] = [Player(name: "Ann", score: 0), Player(name: "Bob", score: 0), Player(name: "Cy", score: 0)]
  players[1].score = players[1].score + 5
  players[1].score = players[1].score + 5
  players[2].score = players[2].score + 3
  for p in players
    print("{p.name} {p.score}")
  end for
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
  p: Point
  q: Point
end struct Segment

fn squared_length(s: Segment) -> Int
  let dx = s.q.x - s.p.x
  let dy = s.q.y - s.p.y
  return dx * dx + dy * dy
end fn squared_length

fn main() uses io
  var seg = Segment(p: Point(x: 3, y: 4), q: Point(x: 6, y: 8))
  print(squared_length(seg))
  seg.p.x = 0
  print(squared_length(seg))
end fn main
```
