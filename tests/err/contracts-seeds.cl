# expect: ensures-false ensures-false
# The search (D32) also tries a function's own literals as inputs, an Int literal with its two neighbours:
# that's where its branches are. Neither bug here is within reach of small values alone.
# fix-mentions: calling fn tax on small inputs

# 10% up to 40000 and 20% above it, but 40000 itself is forgotten
fn tax(income: Int) -> Int
  requires income >= 0
  ensures result >= income / 10
  example tax(30000) == 3000
  example tax(50000) == 6000
  if income < 40000
    return income / 10
  end if
  if income > 40000
    return 4000 + (income - 40000) / 5
  end if
  return 0
end fn tax

# "back" turns the wrong way round
fn turn(cmd: String) -> Int
  ensures result >= 0
  example turn("left") == 90
  if cmd == "left"
    return 90
  else if cmd == "right"
    return 270
  else if cmd == "back"
    return -180
  end if
  return 0
end fn turn

fn main() uses io
  print(tax(100))
  print(turn("left"))
end fn main
