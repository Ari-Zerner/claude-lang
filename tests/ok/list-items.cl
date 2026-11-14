# backends: lean
# Proofs know a list's items after `xs[i] = v`, `append` and `repeat` (D33, night 10): the assigned place
# holds the new value and every other place what it held; `append` puts its item at the old length; each item
# of a `repeat` is the item. And `==` on a struct or an enum is equality to a proof. Every `ensures` here is
# proved; before, none was.

struct Cell
  n: Int
  tag: Int
end struct Cell

enum Light
  Off
  On(level: Int)
end enum Light

fn set_at(xs: List[Int], i: Int, v: Int) -> List[Int]
  requires i >= 0 and i < length(xs)
  ensures result[i] == v
  var out = xs
  out[i] = v
  return out
end fn set_at

fn keeps_others(xs: List[Int], i: Int, j: Int, v: Int) -> List[Int]
  requires i >= 0 and i < length(xs) and j >= 0 and j < length(xs) and i != j
  ensures result[j] == xs[j]
  var out = xs
  out[i] = v
  return out
end fn keeps_others

fn swap(xs: List[Int], i: Int, j: Int) -> List[Int]
  requires i >= 0 and i < length(xs) and j >= 0 and j < length(xs)
  ensures length(result) == length(xs) and result[i] == xs[j] and result[j] == xs[i]
  var out = xs
  let t = out[i]
  out[i] = out[j]
  out[j] = t
  return out
end fn swap

fn with_last(xs: List[Int], v: Int) -> List[Int]
  ensures result[length(xs)] == v
  return append(list: xs, item: v)
end fn with_last

fn append_keeps(xs: List[Int], v: Int, j: Int) -> List[Int]
  requires j >= 0 and j < length(xs)
  ensures result[j] == xs[j]
  return append(list: xs, item: v)
end fn append_keeps

fn filled(n: Int, v: Int, j: Int) -> List[Int]
  requires j >= 0 and j < n
  ensures result[j] == v
  return repeat(item: v, times: n)
end fn filled

# a field of a struct in a list: that field changes, the struct's other field and the other structs don't
fn clear(cells: List[Cell], i: Int) -> List[Cell]
  requires i >= 0 and i < length(cells)
  ensures result[i].n == 0 and result[i].tag == cells[i].tag
  var out = cells
  out[i].n = 0
  return out
end fn clear

fn clear_keeps(cells: List[Cell], i: Int, j: Int) -> List[Cell]
  requires i >= 0 and i < length(cells) and j >= 0 and j < length(cells) and j != i
  ensures result[j] == cells[j]
  var out = cells
  out[i].n = 0
  return out
end fn clear_keeps

# `==` on an enum: the result is the value put there
fn switch_on(lights: List[Light], i: Int) -> List[Light]
  requires i >= 0 and i < length(lights)
  ensures result[i] == On(level: 5)
  var out = lights
  out[i] = On(level: 5)
  return out
end fn switch_on

fn mark(grid: List[List[Int]], r: Int, c: Int) -> List[List[Int]]
  requires r >= 0 and r < length(grid) and c >= 0 and c < length(grid[r])
  ensures result[r][c] == 1 and length(result[r]) == length(grid[r])
  var out = grid
  out[r][c] = 1
  return out
end fn mark

# loops: an invariant about one fixed place
fn fill_all(xs: List[Int], v: Int, k: Int) -> List[Int]
  requires k >= 0 and k < length(xs)
  ensures length(result) == length(xs) and result[k] == v
  var out = xs
  for i in 0 until length(xs)
    invariant length(out) == length(xs) and (i <= k or out[k] == v)
    out[i] = v
  end for
  return out
end fn fill_all

fn copy(xs: List[Int]) -> List[Int]
  requires length(xs) > 0
  ensures length(result) == length(xs) and result[0] == xs[0]
  var out: List[Int] = []
  for i in 0 until length(xs)
    invariant length(out) == i and (i == 0 or out[0] == xs[0])
    out = append(list: out, item: xs[i])
  end for
  return out
end fn copy

fn main() uses io
  print(set_at(xs: [1, 2, 3], i: 1, v: 9))
  print(keeps_others(xs: [1, 2, 3], i: 1, j: 2, v: 9))
  print(swap(xs: [1, 2, 3], i: 0, j: 2))
  print(with_last(xs: [1, 2], v: 7))
  print(append_keeps(xs: [1, 2], v: 7, j: 0))
  print(filled(n: 3, v: 4, j: 2))
  print(clear(cells: [Cell(n: 4, tag: 1), Cell(n: 9, tag: 2)], i: 0))
  print(clear_keeps(cells: [Cell(n: 4, tag: 1), Cell(n: 9, tag: 2)], i: 0, j: 1))
  print(switch_on(lights: [Off, On(level: 1)], i: 0))
  print(mark(grid: [[0, 0], [0, 0]], r: 1, c: 0))
  print(fill_all(xs: [1, 2, 3], v: 7, k: 1))
  print(copy([4, 5]))
end fn main
