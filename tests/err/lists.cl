# expect: unknown-type unknown-type empty-list-type type-mismatch assign-to-param unknown-fn unnamed-arg unused-result type-mismatch nested-assign not-a-list type-mismatch method-call unused-result type-mismatch negative-index
# fix-mentions: `List[String]`
# fix-mentions: `repeat(item: 0, times: 5)`
# fix-mentions: `length(xs)`
# fix-mentions: `xs = append(list: xs, item: 4)`
# fix-mentions: `var row = g[0]`
# fix-mentions: `xs[length(xs) - 1]`
fn bad(xs: List[Int], names: list[str]) -> Int
  let e = []
  let z = [0] * 5
  xs[0] = 1
  let w = len(xs)
  append(xs, 4)
  let m = [1, "a"]
  var g = [[1]]
  g[0][0] = 2
  let s = "abc"
  let c = s[0]
  return xs[true]
end fn bad

fn habits() -> Int
  var xs = [1, 2]
  xs.append(4)
  append(list: xs, item: 5)
  xs = xs + [4]
  return xs[-1]
end fn habits

fn main() uses io
  print(bad(xs: [1], names: ["a"]))
end fn main
