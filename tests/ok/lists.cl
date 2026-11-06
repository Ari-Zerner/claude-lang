fn sum(xs: List[Int]) -> Int
  example sum([1, 2, 3]) == 6
  example sum([]) == 0
  var total = 0
  var i = 0
  while i < length(xs)
    total = total + xs[i]
    i = i + 1
  end while
  return total
end fn sum

fn squares(n: Int) -> List[Int]
  example squares(4) == [0, 1, 4, 9]
  example squares(0) == []
  var out: List[Int] = []
  var i = 0
  while i < n
    out = append(list: out, item: i * i)
    i = i + 1
  end while
  return out
end fn squares

fn main() uses io
  let xs = [3, 1, 4, 1, 5]
  print(xs)
  print(sum(xs))
  var ys = xs
  ys[0] = 100
  print("xs = {xs}, ys = {ys}")
  var grid = repeat(item: repeat(item: 0, times: 3), times: 2)
  var row = grid[1]
  row[2] = 7
  grid[1] = row
  print(grid)
  let names = ["Ari", "a \"quoted\" \{x\}"]
  print(names)
  print(length(names))
  print(length("héllo"))
  print(squares(5) == [0, 1, 4, 9, 16])
  let more = append(list: xs, item: 9)
  print("{xs} {more}")
  check_values()
end fn main

fn bump_all(xs: List[Int]) -> List[Int]
  example bump_all([1, 2]) == [2, 3]
  var out = xs
  var i = 0
  while i < length(out)
    out[i] = out[i] + 1
    i = i + 1
  end while
  return out
end fn bump_all

fn check_values() uses io
  # passing, copying and returning never let one variable change another's list
  let a = [1, 2, 3]
  let b = bump_all(a)
  print("{a} {b}")
  var rows: List[List[String]] = []
  var r = ["x"]
  rows = append(list: rows, item: r)
  r[0] = "y"
  rows = append(list: rows, item: r)
  print(rows)
  print(rows == [["x"], ["y"]])
  print(length(rows[1][0]))
end fn check_values
