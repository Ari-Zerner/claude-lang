# Enums and match (D24): variants with and without fields, construction by D4's rules, exhaustive
# match with positional, by-name and renamed bindings, case _, ==, print, recursion through an enum,
# break inside an arm, and a function whose every arm returns.
enum Command
  Go(dir: String)
  Take(item: String)
  Move(dx: Int, dy: Int)
  Look
end enum Command

enum Expr
  Num(value: Int)
  Add(left: Expr, right: Expr)
  Mul(left: Expr, right: Expr)
end enum Expr

struct Robot
  x: Int
  y: Int
  log: List[Command]
end struct Robot

fn eval(e: Expr) -> Int
  example eval(Num(4)) == 4
  example eval(Add(left: Num(1), right: Mul(left: Num(2), right: Num(3)))) == 7
  match e
    case Num(v)
      return v
    case Add(left, right)
      return eval(left) + eval(right)
    case Mul(right, left)
      return eval(left) * eval(right)
  end match
end fn eval

fn describe(c: Command) -> String
  example describe(Go("north")) == "go north"
  example describe(Look) == "look"
  match c
    case Go(d)
      return "go {d}"
    case Move(dx: a, dy: b)
      return "move {a},{b}"
    case Look
      return "look"
    case _
      return "something else"
  end match
end fn describe

fn step(r: Robot, c: Command) -> Robot
  var out = r
  match c
    case Move(dx, dy)
      out.x = out.x + dx
      out.y = out.y + dy
    case Go
      out.y = out.y + 1
    case Take
    case Look
  end match
  out.log = append(list: out.log, item: c)
  return out
end fn step

fn main() uses io
  let cmds = [Go("north"), Take(item: "key"), Move(dx: 2, dy: -1), Look, Go(dir: "east")]
  for c in cmds
    print(describe(c))
  end for
  print(cmds[2])
  print(cmds)
  print(Look == Look)
  print(Go("a") == Go("a"))
  print(Go("a") == Go("b"))
  print(Go("a") == Take("a"))

  var r = Robot(x: 0, y: 0, log: [])
  for c in cmds
    r = step(r: r, c: c)
  end for
  print("{r.x} {r.y} {length(r.log)} {r.log[4]}")

  let e = Add(left: Num(10), right: Mul(left: Num(3), right: Add(left: Num(1), right: Num(1))))
  print(e)
  print(eval(e))

  # break inside an arm leaves the loop, not just the match
  var n = 0
  for c in cmds
    match c
      case Look
        break
      case _
        n = n + 1
    end match
  end for
  print(n)

  # a list of enums keeps value semantics
  var copy = cmds
  copy[0] = Look
  print("{cmds[0]} {copy[0]}")
end fn main
