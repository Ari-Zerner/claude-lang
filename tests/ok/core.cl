# The Lean backend's stage 1 (D26): Int, Bool, String, functions, if/while/for over numbers, print, examples.
# No lists, structs or enums, so both backends run it.

fn is_even(n: Int) -> Bool
  example is_even(0)
  example not is_even(3)
  if n == 0
    return true
  end if
  return is_odd(n - 1)
end fn is_even

fn is_odd(n: Int) -> Bool
  if n == 0
    return false
  end if
  return is_even(n - 1)
end fn is_odd

fn parity(n: Int) -> Bool
  # mutual recursion is for n >= 0; for negatives, ask about -n
  if n < 0
    return is_even(-n)
  end if
  return is_even(n)
end fn parity

fn answer() -> Int
  example answer() == 42
  return 6 * 7
end fn answer

fn digits(n: Int) -> Int
  example digits(0) == 1
  example digits(-12345) == 5
  var m = n
  if m < 0
    m = -m
  end if
  var count = 1
  while m >= 10
    m = m / 10
    count = count + 1
  end while
  return count
end fn digits

fn first_square_over(limit: Int) -> Int
  example first_square_over(50) == 64
  for i in 1 through limit
    if i * i > limit
      return i * i
    end if
  end for
  return -1
end fn first_square_over

fn skip_threes(n: Int) -> Int
  example skip_threes(10) == 27
  var total = 0
  for i in 0 until n
    if i % 3 == 0
      continue
    end if
    total = total + i
  end for
  return total
end fn skip_threes

fn countdown(n: Int) -> String
  example countdown(3) == "3 2 1 0"
  example countdown(0) == "0"
  var s = "{n}"
  for i in 0 until n reversed
    s = "{s} {i}"
  end for
  return s
end fn countdown

fn stars(n: Int) -> String
  var line = ""
  var i = 0
  while true
    if i == n
      break
    end if
    line = "{line}*"
    i = i + 1
  end while
  return line
end fn stars

fn shout(word: String) -> Int uses io
  print("{word}!")
  return length(word)
end fn shout

fn main() uses io
  print("parity {parity(10)} {parity(-7)} {is_odd(9)}")
  print("answer {answer()}")
  print("digits {digits(9)} {digits(10)} {digits(-1000)}")
  print("div {-7 / 2} {-7 % 2} {-7 / -2} {-7 % -2} {7 / -2} {7 % -2}")
  print(first_square_over(10))
  print(skip_threes(7))
  print(countdown(5))
  for k in 1 through 3 reversed
    print(stars(k))
  end for
  for k in 5 through 4
    print("never")
  end for
  let n = shout("héllo, wörld")
  print("length {n}, \{braces\} and \"quotes\" and a \\ backslash")
  let _ = shout("done")
  var big = 1
  for i in 1 through 25
    big = big * 2
  end for
  print("2^25 = {big}, and {big == 33554432}")
end fn main
