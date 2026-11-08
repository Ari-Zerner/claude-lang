# Hidden-input trial 2026-11-08-1104 (cl, haiku)

| task | shown example | ok | wrong | error | verdict | lines | examples |
|---|---|---|---|---|---|---|---|
| rotate | first try | 9 | 0 | 0 | all ok | 17 | 5 |
| second_largest | first try | 9 | 0 | 0 | all ok | 30 | 5 |
| spread | first try | 8 | 0 | 0 | all ok | 43 | 11 |
| window_sums | first try | 8 | 0 | 0 | all ok | 16 | 3 |
| merge_ranges | first try | 9 | 0 | 0 | all ok | 57 | 9 |
| first_at_least | first try | 8 | 0 | 0 | all ok | 18 | 5 |
| digit_sum | first try | 7 | 0 | 0 | all ok | 16 | 3 |
| run_lengths | first try | 6 | 0 | 0 | all ok | 19 | 4 |
| days_until_warmer | first try | 7 | 0 | 0 | all ok | 20 | 5 |
| balanced | after fix | 9 | 0 | 0 | all ok | 49 | 13 |
| max_subarray | first try | 7 | 0 | 0 | all ok | 18 | 3 |
| median | first try | 7 | 0 | 0 | all ok | 50 | 12 |

Totals over hidden inputs: {'ok': 94, 'wrong': 0, 'error': 0}. Programs with a wrong answer: 0 of 12.

## rotate

`fn rotate(xs: List[Int], k: Int) -> List[Int]`

### attempt 1: shown example OK

```cl
fn rotate(xs: List[Int], k: Int) -> List[Int]
  example rotate(xs: [1, 2, 3, 4, 5], k: 2) == [4, 5, 1, 2, 3]
  example rotate(xs: [1, 2, 3], k: -1) == [2, 3, 1]
  example rotate(xs: [1, 2, 3], k: 4) == [3, 1, 2]
  example rotate(xs: [1, 2, 3], k: 0) == [1, 2, 3]
  example length(rotate(xs: [], k: 3)) == 0
  let n = length(xs)
  if n == 0
    return []
  end if
  let r = ((k % n) + n) % n
  var result = repeat(item: 0, times: n)
  for i in 0 until n
    result[(i + r) % n] = xs[i]
  end for
  return result
end fn rotate
```

Hidden inputs: 9 ok, 0 wrong, 0 error

## second_largest

`fn second_largest(xs: List[Int]) -> Option[Int]`

### attempt 1: shown example OK

```cl
fn second_largest(xs: List[Int]) -> Option[Int]
  example second_largest(xs: [3, 1, 4, 1, 5]) == Some(4)
  example second_largest(xs: [1, 2]) == Some(1)
  example second_largest(xs: [7]) == None
  example second_largest(xs: [2, 2, 2]) == None
  example second_largest(xs: []) == None
  if length(xs) == 0
    return None
  end if
  var top = xs[0]
  for v in xs
    if v > top
      top = v
    end if
  end for
  var found = false
  var best = 0
  for w in xs
    if w < top
      if not found or w > best
        best = w
        found = true
      end if
    end if
  end for
  if found
    return Some(best)
  end if
  return None
end fn second_largest
```

Hidden inputs: 9 ok, 0 wrong, 0 error

## spread

`fn spread(rows: Int, cols: Int, points: List[List[Int]]) -> List[List[Int]]`

### attempt 1: shown example OK

```cl
fn in_bounds(r: Int, c: Int, rows: Int, cols: Int) -> Bool
  example in_bounds(r: 0, c: 0, rows: 1, cols: 1) == true
  example in_bounds(r: -1, c: 0, rows: 2, cols: 2) == false
  example in_bounds(r: 1, c: 2, rows: 2, cols: 3) == true
  example in_bounds(r: 2, c: 0, rows: 2, cols: 3) == false
  return r >= 0 and r < rows and c >= 0 and c < cols
end fn in_bounds

fn make_grid(rows: Int, cols: Int) -> List[List[Int]]
  example make_grid(rows: 2, cols: 3) == [[0, 0, 0], [0, 0, 0]]
  example make_grid(rows: 1, cols: 1) == [[0]]
  var grid: List[List[Int]] = []
  for i in 0 until rows
    grid = append(list: grid, item: repeat(item: 0, times: cols))
  end for
  return grid
end fn make_grid

fn bump_cell(grid: List[List[Int]], r: Int, c: Int, rows: Int, cols: Int) -> List[List[Int]]
  example bump_cell(grid: [[0]], r: 0, c: 0, rows: 1, cols: 1) == [[1]]
  example bump_cell(grid: [[0]], r: 1, c: 0, rows: 1, cols: 1) == [[0]]
  var g = grid
  if in_bounds(r: r, c: c, rows: rows, cols: cols)
    g[r][c] = g[r][c] + 1
  end if
  return g
end fn bump_cell

fn add_point(grid: List[List[Int]], r: Int, c: Int, rows: Int, cols: Int) -> List[List[Int]]
  example add_point(grid: [[0, 0], [0, 0]], r: 0, c: 0, rows: 2, cols: 2) == [[1, 1], [1, 0]]
  var g = bump_cell(grid: grid, r: r, c: c, rows: rows, cols: cols)
  g = bump_cell(grid: g, r: r - 1, c: c, rows: rows, cols: cols)
  g = bump_cell(grid: g, r: r + 1, c: c, rows: rows, cols: cols)
  g = bump_cell(grid: g, r: r, c: c - 1, rows: rows, cols: cols)
  g = bump_cell(grid: g, r: r, c: c + 1, rows: rows, cols: cols)
  return g
end fn add_point

fn spread(rows: Int, cols: Int, points: List[List[Int]]) -> List[List[Int]]
  example spread(rows: 2, cols: 3, points: [[0, 0]]) == [[1, 1, 0], [1, 0, 0]]
  example spread(rows: 1, cols: 1, points: []) == [[0]]
  var grid = make_grid(rows: rows, cols: cols)
  for p in points
    grid = add_point(grid: grid, r: p[0], c: p[1], rows: rows, cols: cols)
  end for
  return grid
end fn spread
```

Hidden inputs: 8 ok, 0 wrong, 0 error

## window_sums

`fn window_sums(xs: List[Int], k: Int) -> List[Int]`

### attempt 1: shown example OK

```cl
fn window_sums(xs: List[Int], k: Int) -> List[Int]
  example window_sums(xs: [1, 2, 3, 4], k: 2) == [3, 5, 7]
  example window_sums(xs: [1, 2], k: 3) == []
  example window_sums(xs: [], k: 1) == []
  var out: List[Int] = []
  var start = 0
  while start + k <= length(xs)
    var total = 0
    for j in start until start + k
      total = total + xs[j]
    end for
    out = append(list: out, item: total)
    start = start + 1
  end while
  return out
end fn window_sums
```

Hidden inputs: 8 ok, 0 wrong, 0 error

## merge_ranges

`fn merge_ranges(ranges: List[List[Int]]) -> List[List[Int]]`

### attempt 1: shown example OK

```cl
fn insert_range(items: List[List[Int]], r: List[Int]) -> List[List[Int]]
  example insert_range(items: [[1, 2], [5, 6]], r: [3, 4]) == [[1, 2], [3, 4], [5, 6]]
  example insert_range(items: [], r: [3, 4]) == [[3, 4]]
  var out: List[List[Int]] = []
  var placed = false
  for x in items
    if (not placed) and r[0] <= x[0]
      out = append(list: out, item: r)
      placed = true
    end if
    out = append(list: out, item: x)
  end for
  if not placed
    out = append(list: out, item: r)
  end if
  return out
end fn insert_range

fn sort_ranges(ranges: List[List[Int]]) -> List[List[Int]]
  example sort_ranges(ranges: [[5, 6], [1, 3]]) == [[1, 3], [5, 6]]
  example sort_ranges(ranges: []) == []
  var sorted_so_far: List[List[Int]] = []
  for r in ranges
    sorted_so_far = insert_range(items: sorted_so_far, r: r)
  end for
  return sorted_so_far
end fn sort_ranges

fn merge_ranges(ranges: List[List[Int]]) -> List[List[Int]]
  example merge_ranges(ranges: [[5, 6], [1, 3], [2, 4]]) == [[1, 4], [5, 6]]
  example merge_ranges(ranges: []) == []
  example merge_ranges(ranges: [[1, 3], [4, 6]]) == [[1, 3], [4, 6]]
  example merge_ranges(ranges: [[1, 10], [2, 3]]) == [[1, 10]]
  example merge_ranges(ranges: [[2, 2], [2, 2]]) == [[2, 2]]
  var ordered = sort_ranges(ranges: ranges)
  var result: List[List[Int]] = []
  var has_cur = false
  var lo = 0
  var hi = 0
  for r in ordered
    if not has_cur
      lo = r[0]
      hi = r[1]
      has_cur = true
    else if r[0] <= hi
      if r[1] > hi
        hi = r[1]
      end if
    else
      result = append(list: result, item: [lo, hi])
      lo = r[0]
      hi = r[1]
    end if
  end for
  if has_cur
    result = append(list: result, item: [lo, hi])
  end if
  return result
end fn merge_ranges
```

Hidden inputs: 9 ok, 0 wrong, 0 error

## first_at_least

`fn first_at_least(xs: List[Int], x: Int) -> Int`

### attempt 1: shown example OK

```cl
fn first_at_least(xs: List[Int], x: Int) -> Int
  example first_at_least(xs: [1, 3, 3, 5], x: 3) == 1
  example first_at_least(xs: [1, 3, 3, 5], x: 0) == 0
  example first_at_least(xs: [1, 3, 3, 5], x: 5) == 3
  example first_at_least(xs: [1, 3, 3, 5], x: 6) == 4
  example first_at_least(xs: [], x: 3) == 0
  var lo = 0
  var hi = length(xs)
  while lo < hi
    let mid = lo + (hi - lo) / 2
    if xs[mid] < x
      lo = mid + 1
    else
      hi = mid
    end if
  end while
  return lo
end fn first_at_least
```

Hidden inputs: 8 ok, 0 wrong, 0 error

## digit_sum

`fn digit_sum(n: Int) -> Int`

### attempt 1: shown example OK

```cl
fn digit_sum(n: Int) -> Int
  example digit_sum(n: 1234) == 10
  example digit_sum(n: -1234) == 10
  example digit_sum(n: 0) == 0
  var m = n
  var sum = 0
  while m != 0
    var d = m % 10
    if d < 0
      d = -d
    end if
    sum = sum + d
    m = m / 10
  end while
  return sum
end fn digit_sum
```

Hidden inputs: 7 ok, 0 wrong, 0 error

## run_lengths

`fn run_lengths(xs: List[Int]) -> List[List[Int]]`

### attempt 1: shown example OK

```cl
fn run_lengths(xs: List[Int]) -> List[List[Int]]
  example run_lengths(xs: [1, 1, 2, 3, 3, 3]) == [[1, 2], [2, 1], [3, 3]]
  example run_lengths(xs: []) == []
  example run_lengths(xs: [5]) == [[5, 1]]
  example run_lengths(xs: [4, 4, 4]) == [[4, 3]]
  var runs: List[List[Int]] = []
  var i = 0
  while i < length(xs)
    var count = 0
    var j = i
    while j < length(xs) and xs[j] == xs[i]
      count = count + 1
      j = j + 1
    end while
    runs = append(list: runs, item: [xs[i], count])
    i = j
  end while
  return runs
end fn run_lengths
```

Hidden inputs: 6 ok, 0 wrong, 0 error

## days_until_warmer

`fn days_until_warmer(temps: List[Int]) -> List[Int]`

### attempt 1: shown example OK

```cl
fn days_until_warmer(temps: List[Int]) -> List[Int]
  example days_until_warmer(temps: [73, 74, 75, 71, 69, 72, 76, 73]) == [1, 1, 4, 2, 1, 1, 0, 0]
  example days_until_warmer(temps: []) == []
  example days_until_warmer(temps: [50]) == [0]
  example days_until_warmer(temps: [70, 70, 70]) == [0, 0, 0]
  example days_until_warmer(temps: [1, 2, 3, 4]) == [1, 1, 1, 0]
  var n = length(temps)
  var result = repeat(item: 0, times: n)
  for i in 0 until n
    var days = 0
    for j in i + 1 until n
      if temps[j] > temps[i]
        days = j - i
        break
      end if
    end for
    result[i] = days
  end for
  return result
end fn days_until_warmer
```

Hidden inputs: 7 ok, 0 wrong, 0 error

## balanced

`fn balanced(tokens: List[String]) -> Bool`

### attempt 1: build-fail

```cl
fn is_open(c: String) -> Bool
  example is_open(c: "(") == true
  example is_open(c: "]") == false
  return c == "(" or c == "[" or c == "{"
end fn is_open

fn opener_of(c: String) -> String
  example opener_of(c: ")") == "("
  example opener_of(c: "]") == "["
  example opener_of(c: "}") == "{"
  example opener_of(c: "(") == ""
  if c == ")"
    return "("
  else if c == "]"
    return "["
  else if c == "}"
    return "{"
  else
    return ""
  end if
end fn opener_of

fn balanced(tokens: List[String]) -> Bool
  example balanced(tokens: ["(", "[", "]", ")"]) == true
  example balanced(tokens: []) == true
  example balanced(tokens: ["("]) == false
  example balanced(tokens: ["(", "]"]) == false
  example balanced(tokens: [")", "("]) == false
  example balanced(tokens: ["{", "[", "}", "]"]) == false
  example balanced(tokens: ["(", ")", "{", "}", "[", "]"]) == true
  var stack = repeat(item: "", times: length(tokens))
  var top = 0
  var ok = true
  for t in tokens
    if is_open(c: t)
      stack[top] = t
      top = top + 1
    else
      if top == 0
        ok = false
        break
      end if
      top = top - 1
      if stack[top] != opener_of(c: t)
        ok = false
        break
      end if
    end if
  end for
  return ok and (top == 0)
end fn balanced
```

Diagnostics sent back:
```
prog.cl:4:39: error[unclosed-string]: this string has no closing `"` on its line
    4 |   return c == "(" or c == "[" or c == "{"
      |                                       ^^^
  fix: strings end on the line they start; use `\n` for a line break
prog.cl:4:40: error[unclosed-interpolation]: `{` starts an interpolation, but there's no `}`
    4 |   return c == "(" or c == "[" or c == "{"
      |                                        ^
  fix: write `\{` for a literal brace
prog.cl:10:32: error[unclosed-string]: this string has no closing `"` on its line
   10 |   example opener_of(c: "}") == "{"
      |                                ^^^
  fix: strings end on the line they start; use `\n` for a line break
prog.cl:10:33: error[unclosed-interpolation]: `{` starts an interpolation, but there's no `}`
   10 |   example opener_of(c: "}") == "{"
      |                                 ^
  fix: write `\{` for a literal brace
prog.cl:17:12: error[unclosed-string]: this string has no closing `"` on its line
   17 |     return "{"
      |            ^^^
  fix: strings end on the line they start; use `\n` for a line break
prog.cl:17:13: error[unclosed-interpolation]: `{` starts an interpolation, but there's no `}`
   17 |     return "{"
      |             ^
  fix: write `\{` for a literal brace
prog.cl:29:31: error[nested-string]: a string can't appear inside `{...}` in another string
   29 |   example balanced(tokens: ["{", "[", "}", "]"]) == false
      |                               ^
  fix: store it in a `let` first and interpolate the name
prog.cl:30:41: error[nested-string]: a string can't appear inside `{...}` in another string
   30 |   example balanced(tokens: ["(", ")", "{", "}", "[", "]"]) == true
      |                                         ^
  fix: store it in a `let` first and interpolate the name
8 error(s), 0 warning(s)
```

### attempt 2: shown example OK

```cl
fn is_open(c: String) -> Bool
  example is_open(c: "(") == true
  example is_open(c: "]") == false
  return c == "(" or c == "[" or c == "\{"
end fn is_open

fn opener_of(c: String) -> String
  example opener_of(c: ")") == "("
  example opener_of(c: "]") == "["
  example opener_of(c: "\}") == "\{"
  example opener_of(c: "(") == ""
  if c == ")"
    return "("
  else if c == "]"
    return "["
  else if c == "\}"
    return "\{"
  else
    return ""
  end if
end fn opener_of

fn balanced(tokens: List[String]) -> Bool
  example balanced(tokens: ["(", "[", "]", ")"]) == true
  example balanced(tokens: []) == true
  example balanced(tokens: ["("]) == false
  example balanced(tokens: ["(", "]"]) == false
  example balanced(tokens: [")", "("]) == false
  example balanced(tokens: ["\{", "[", "\}", "]"]) == false
  example balanced(tokens: ["(", ")", "\{", "\}", "[", "]"]) == true
  var stack = repeat(item: "", times: length(tokens))
  var top = 0
  var ok = true
  for t in tokens
    if is_open(c: t)
      stack[top] = t
      top = top + 1
    else
      if top == 0
        ok = false
        break
      end if
      top = top - 1
      if stack[top] != opener_of(c: t)
        ok = false
        break
      end if
    end if
  end for
  return ok and (top == 0)
end fn balanced
```

Hidden inputs: 9 ok, 0 wrong, 0 error

## max_subarray

`fn max_subarray(xs: List[Int]) -> Int`

### attempt 1: shown example OK

```cl
fn max_subarray(xs: List[Int]) -> Int
  example max_subarray(xs: [-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6
  example max_subarray(xs: [5]) == 5
  example max_subarray(xs: [-3, -1, -2]) == -1
  var best = xs[0]
  var here = xs[0]
  for i in 1 until length(xs)
    if here < 0
      here = xs[i]
    else
      here = here + xs[i]
    end if
    if here > best
      best = here
    end if
  end for
  return best
end fn max_subarray
```

Hidden inputs: 7 ok, 0 wrong, 0 error

## median

`fn median(xs: List[Int]) -> Int`

### attempt 1: shown example OK

```cl
fn median(xs: List[Int]) -> Int
  example median(xs: [3, 1, 2]) == 2
  example median(xs: [7]) == 7
  example median(xs: [4, 1, 3, 2]) == 2
  example median(xs: [-1, -2]) == -2
  example median(xs: [-3, 1]) == -1
  let s = sort_ints(xs: xs)
  let n = length(s)
  if n % 2 == 1
    return s[n / 2]
  end if
  return floor_mean(a: s[n / 2 - 1], b: s[n / 2])
end fn median

fn sort_ints(xs: List[Int]) -> List[Int]
  example sort_ints(xs: [3, 1, 2]) == [1, 2, 3]
  example sort_ints(xs: [5]) == [5]
  example sort_ints(xs: [2, 2, -1]) == [-1, 2, 2]
  var s = xs
  var i = 1
  while i < length(s)
    var j = i
    while j > 0 and s[j - 1] > s[j]
      var t = s[j - 1]
      s[j - 1] = s[j]
      s[j] = t
      j = j - 1
    end while
    i = i + 1
  end while
  return s
end fn sort_ints

fn floor_mean(a: Int, b: Int) -> Int
  example floor_mean(a: 1, b: 2) == 1
  example floor_mean(a: -3, b: 1) == -1
  example floor_mean(a: -1, b: -2) == -2
  example floor_mean(a: 4, b: 6) == 5
  var qa = a / 2
  if a % 2 < 0
    qa = qa - 1
  end if
  var qb = b / 2
  if b % 2 < 0
    qb = qb - 1
  end if
  var bonus = 0
  if a % 2 != 0 and b % 2 != 0
    bonus = 1
  end if
  return qa + qb + bonus
end fn floor_mean
```

Hidden inputs: 7 ok, 0 wrong, 0 error
