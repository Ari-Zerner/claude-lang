# Recursion (D28): each recursive function becomes a total Lean `def` when clc finds a measure Lean can
# check, else `partial`. The `total`/`partial` lines below are checked against the generated Lean.
# total: fact fib sum_range search sum_from size eval is_even countdown
# partial: down
struct Tree
  value: Int
  children: List[Tree]
end struct Tree

enum Expr
  Num(value: Int)
  Add(left: Expr, right: Expr)
end enum Expr

fn fact(n: Int) -> Int
  example fact(5) == 120
  if n <= 0
    return 1
  end if
  return n * fact(n - 1)
end fn fact

fn fib(n: Int) -> Int
  example fib(10) == 55
  if n < 2
    return n
  end if
  return fib(n - 1) + fib(n - 2)
end fn fib

# counts up to a bound: (hi - lo + 1) goes down
fn sum_range(lo: Int, hi: Int) -> Int
  example sum_range(lo: 1, hi: 4) == 10
  if lo > hi
    return 0
  end if
  return lo + sum_range(lo: lo + 1, hi: hi)
end fn sum_range

# binary search: needs `/` by a literal unfolded
fn search(xs: List[Int], target: Int, lo: Int, hi: Int) -> Int
  example search(xs: [1, 3, 5, 7], target: 5, lo: 0, hi: 3) == 2
  example search(xs: [1, 3, 5, 7], target: 4, lo: 0, hi: 3) == -1
  if lo > hi
    return -1
  end if
  let mid = (lo + hi) / 2
  if xs[mid] == target
    return mid
  end if
  if xs[mid] < target
    return search(xs: xs, target: target, lo: mid + 1, hi: hi)
  end if
  return search(xs: xs, target: target, lo: lo, hi: mid - 1)
end fn search

# walks a list by index: (length(xs) - i + 1) goes down
fn sum_from(xs: List[Int], i: Int) -> Int
  example sum_from(xs: [1, 2, 3], i: 0) == 6
  if i >= length(xs)
    return 0
  end if
  return xs[i] + sum_from(xs: xs, i: i + 1)
end fn sum_from

# a tree through a list field
fn size(t: Tree) -> Int
  example size(Tree(value: 1, children: [Tree(value: 2, children: [])])) == 2
  var n = 1
  for c in t.children
    n = n + size(c)
  end for
  return n
end fn size

# structural, through an enum
fn eval(e: Expr) -> Int
  example eval(Add(left: Num(2), right: Num(3))) == 5
  match e
    case Num(v)
      return v
    case Add(left, right)
      return eval(left) + eval(right)
  end match
end fn eval

# mutual recursion
fn is_even(n: Int) -> Bool
  example is_even(4)
  if n <= 0
    return n == 0
  end if
  return is_odd(n - 1)
end fn is_even

fn is_odd(n: Int) -> Bool
  example is_odd(3)
  if n <= 0
    return false
  end if
  return is_even(n - 1)
end fn is_odd

# with io
fn countdown(n: Int) uses io
  if n <= 0
    return
  end if
  print(n)
  countdown(n - 1)
end fn countdown

# never stops for a negative n, so it can't be total
fn down(n: Int) -> Int
  example down(3) == 0
  if n == 0
    return 0
  end if
  return down(n - 1)
end fn down

fn main() uses io
  print(fact(10))
  print(fib(15))
  print(sum_range(lo: 1, hi: 100))
  print(search(xs: [2, 4, 6, 8, 10], target: 8, lo: 0, hi: 4))
  print(sum_from(xs: [5, 6, 7], i: 0))
  print(size(Tree(value: 1, children: [Tree(value: 2, children: []), Tree(value: 3, children: [Tree(value: 4, children: [])])])))
  print(eval(Add(left: Num(40), right: Add(left: Num(1), right: Num(1)))))
  print(is_even(10))
  print(is_odd(10))
  countdown(3)
  print(down(5))
end fn main
