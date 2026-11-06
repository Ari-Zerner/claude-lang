fn contains(xs: List[Int], x: Int) -> Bool
  example contains(xs: [1, 2, 3], x: 2) == true
  example contains(xs: [], x: 1) == false
  for y in xs
    if y == x
      return true
    end if
  end for
  return false
end fn contains

fn first_over(xs: List[Int], limit: Int) -> Int
  example first_over(xs: [1, 5, 9], limit: 4) == 5
  var found = -1
  for x in xs
    if x > limit
      found = x
      break
    end if
  end for
  return found
end fn first_over

fn forever() -> Int
  var i = 0
  while true
    i = i + 1
    if i == 10
      break
    end if
  end while
  return i
end fn forever

fn main() uses io
  var line = ""
  for i in 0 until 5
    line = "{line}{i}"
  end for
  print(line)
  line = ""
  for i in 1 through 5
    if i == 3
      continue
    end if
    line = "{line}{i}"
  end for
  print(line)
  line = ""
  for i in 0 until 5 reversed
    line = "{line}{i}"
  end for
  print(line)
  line = ""
  for i in 1 through 5 reversed
    line = "{line}{i}"
  end for
  print(line)
  for i in 5 until 5
    print("never")
  end for
  for i in 5 through 4
    print("never")
  end for
  for i in 5 until 5 reversed
    print("never")
  end for
  for i in 9_223_372_036_854_775_806 through 9_223_372_036_854_775_807
    print(i)
  end for
  for i in -9_223_372_036_854_775_807 - 1 through -9_223_372_036_854_775_807 reversed
    print(i)
  end for
  var xs = [1, 2, 3]
  for x in xs
    xs = append(list: xs, item: x * 10)
  end for
  print(xs)
  for x in xs reversed
    if x < 10
      continue
    end if
    print(x)
    if x == 20
      break
    end if
  end for
  print(contains(xs: xs, x: 20))
  print(first_over(xs: xs, limit: 2))
  print(forever())
  var grid = [[1, 2], [3]]
  for row in grid
    for v in row
      print(v)
    end for
  end for
end fn main
