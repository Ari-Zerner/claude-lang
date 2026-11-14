# expect: ensures-false ensures-false ensures-false ensures-false
# What proofs know about a list's items (tests/ok/list-items.cl) must not prove a false `ensures`. Each of
# these is one slip away from a function proved there, and each must come back with an input that breaks it.

# nothing says `j` isn't `i`
fn keeps_all(xs: List[Int], i: Int, j: Int, v: Int) -> List[Int]
  requires i >= 0 and i < length(xs) and j >= 0 and j < length(xs)
  ensures result[j] == xs[j]
  var out = xs
  out[i] = v
  return out
end fn keeps_all

# the second assignment reads the place the first one just changed
fn bad_swap(xs: List[Int], i: Int, j: Int) -> List[Int]
  requires i >= 0 and i < length(xs) and j >= 0 and j < length(xs)
  ensures result[i] == xs[j] and result[j] == xs[i]
  var out = xs
  out[i] = out[j]
  out[j] = out[i]
  return out
end fn bad_swap

# `append` puts the item last, not first
fn with_first(xs: List[Int], v: Int) -> List[Int]
  ensures result[0] == v
  return append(list: xs, item: v)
end fn with_first

struct Cell
  n: Int
  tag: Int
end struct Cell

# the struct at `i` did change
fn clear(cells: List[Cell], i: Int) -> List[Cell]
  requires i >= 0 and i < length(cells)
  ensures result[i] == cells[i]
  var out = cells
  out[i].n = 0
  return out
end fn clear

fn main() uses io
  print(keeps_all(xs: [1, 2], i: 0, j: 1, v: 5))
  print(bad_swap(xs: [1, 2], i: 0, j: 0))
  print(with_first(xs: [], v: 1))
  print(clear(cells: [Cell(n: 0, tag: 1)], i: 0))
end fn main
