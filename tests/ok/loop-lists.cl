# backends: lean
# Proofs know what `repeat`, `xs[i] = v` and `xs[i].f = v` do to a list's length (D33, night 9): `repeat` makes
# `times` items, and an assignment into the list keeps its length when the index is in range. Every `ensures`
# here is proved. The first function is, but for its name, what Haiku wrote for "reverse a list" and clc
# couldn't prove: a true invariant about a list filled in place.

struct Cell
  n: Int
end struct Cell

fn reversed_fill(xs: List[Int]) -> List[Int]
  ensures length(result) == length(xs)
  let n = length(xs)
  var out = repeat(item: 0, times: n)
  for i in 0 until n
    invariant length(out) == n
    out[n - 1 - i] = xs[i]
  end for
  return out
end fn reversed_fill

fn zeros(n: Int) -> List[Int]
  requires n >= 0
  ensures length(result) == n
  return repeat(item: 0, times: n)
end fn zeros

fn bump(xs: List[Int], i: Int) -> List[Int]
  requires i >= 0 and i < length(xs)
  ensures length(result) == length(xs)
  var out = xs
  out[i] = out[i] + 1
  return out
end fn bump

fn clear(cells: List[Cell], i: Int) -> List[Cell]
  requires i >= 0 and i < length(cells)
  ensures length(result) == length(cells)
  var out = cells
  out[i].n = 0
  return out
end fn clear

# a running maximum written back into the list: the length is all the invariant needs to say
fn running_max(xs: List[Int]) -> List[Int]
  ensures length(result) == length(xs)
  var out = xs
  for i in 1 until length(xs)
    invariant length(out) == length(xs)
    if out[i - 1] > out[i]
      out[i] = out[i - 1]
    end if
  end for
  return out
end fn running_max

fn main() uses io
  print(reversed_fill([1, 2, 3]))
  print(zeros(3))
  print(bump(xs: [5, 6], i: 1))
  print(length(clear(cells: [Cell(n: 4), Cell(n: 9)], i: 0)))
  print(running_max([3, 1, 4, 1, 5]))
end fn main
