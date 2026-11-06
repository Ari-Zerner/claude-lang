# expect: example-failed example-crashed
fn evens(n: Int) -> List[Int]
  example evens(3) == [0, 2, 4]
  var out: List[Int] = []
  var i = 0
  while i <= n
    out = append(list: out, item: 2 * i)
    i = i + 1
  end while
  return out
end fn evens

fn last(xs: List[Int]) -> Int
  example last([1, 2, 3]) == 3
  return xs[length(xs)]
end fn last

fn main() uses io
  print(evens(2))
  print(last([5]))
end fn main
