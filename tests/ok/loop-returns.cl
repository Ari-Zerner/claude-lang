# backends: lean
# A `return` inside a loop that also has `invariant` lines (night 8). While such a loop runs, nothing has been
# returned yet, and each pass has to be able to count on that, or it can't use the invariant from the pass
# before. Both `ensures` here are proved; neither was before clc said so in what it hands Lean.

# a `while` with a `return`: binary search. The `decreases` needs `lo >= 0` from the pass before.
fn bsearch(xs: List[Int], want: Int) -> Int
  ensures result == -1 or (result >= 0 and result < length(xs) and xs[result] == want)
  example bsearch(xs: [1, 3, 5, 7], want: 5) == 2
  example bsearch(xs: [1, 3, 5, 7], want: 4) == -1
  var lo = 0
  var hi = length(xs)
  while lo < hi
    invariant lo >= 0 and hi <= length(xs)
    decreases hi - lo
    let mid = (lo + hi) / 2
    if xs[mid] == want
      return mid
    end if
    if xs[mid] < want
      lo = mid + 1
    else
      hi = mid
    end if
  end while
  return -1
end fn bsearch

# a `for` with a `return`, where the value returned is only right because of the invariant
fn capped_sum(xs: List[Int], cap: Int) -> Int
  requires cap >= 0
  ensures result <= cap
  example capped_sum(xs: [3, 4, 5], cap: 6) == 3
  var total = 0
  for i in 0 until length(xs)
    invariant total <= cap
    if total + xs[i] > cap
      return total
    end if
    total = total + xs[i]
  end for
  return total
end fn capped_sum

fn main() uses io
  print(bsearch(xs: [2, 4, 6, 8, 10], want: 8))
  print(bsearch(xs: [2, 4, 6, 8, 10], want: 5))
  print(capped_sum(xs: [1, 1, 9], cap: 5))
  print(capped_sum(xs: [1, 1, 2], cap: 5))
end fn main
