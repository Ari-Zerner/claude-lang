# expect: duplicate-name non-exhaustive duplicate-name unknown-variant unreachable-case unnamed-bind assign-to-let unreachable-case syntax not-an-enum syntax syntax unreachable-case arg-count arg-count unnamed-arg stray-case
# fix-mentions: `case Move(dx, dy)`, `case Look`
# fix-mentions: `case Move(dx: a, dy: b)`
# fix-mentions: `case _`
# fix-mentions: `Move(dx: 1, dy: 2)`
enum Command
  Go(dir: String)
  Move(dx: Int, dy: Int)
  Look
end enum Command

enum Other
  Look
end enum Other

fn f(c: Command) -> Int
  let x = 1
  match c
    case Go(d)
      return 1
  end match
  match c
    case Go(x)
      return 1
    case Jump
      return 2
    case _
      return 3
    case Look
      return 4
  end match
  match c
    case Move(a, b)
      return a
    case Go(d)
      d = "x"
      return 0
    case Go(e)
      return 0
    else
      return 5
  end match
  match 5
    case Look
      return 1
  end match
  match c
    let y = 2
    case Command.Look
      return 1
    case Look(z)
      return 2
    case _
      return 3
  end match
end fn f

fn main() uses io
  let a = Go
  let b = Look()
  let m = Move(1, 2)
  case Look
  print("{a} {b} {m}")
end fn main
