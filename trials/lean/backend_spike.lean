-- D26 spike (2026-11-08): what clc's Lean backend might emit, written by hand.
-- Build and run:  lean -c Main.c backend_spike.lean && leanc Main.c -O1 -o main && ./main
-- Measured on the box: lean -c 1.4-7 s, leanc -O1 1.5-5 s (default -O3: ~5.6 s);
-- 1M Array.push + 1M set! run in 0.05 s at -O1 (in place, since the array is unshared);
-- the trap prints "runtime error: ..." after flushing stdout, and exits 70 (D16).
-- tax_nonneg is a contract closed by `split`/`omega`, with no proof written by hand.
-- What clc might emit for a small claude-lang program (hand-written spike).
-- claude-lang: Int is unbounded here (Lean Int); List[T] -> Array T (refcounted, in-place when unique).

structure Item where
  name : String
  stock : Int
deriving Repr, BEq, Inhabited

inductive Cmd where
  | take (item : String)
  | look
deriving Repr, BEq, Inhabited

-- Runtime trap: logically `default` (so proofs must show it is unreachable),
-- at run time prints claude-lang's message and exits 70 (D16).
unsafe def clTrapImpl {α : Type} [Inhabited α] (msg : String) : α :=
  match unsafeIO (do (← IO.getStdout).flush; IO.eprintln s!"runtime error: {msg}"; (IO.Process.exit 70 : IO α)) with
  | .ok a => a
  | .error _ => default
@[implemented_by clTrapImpl, noinline] def clTrap {α : Type} [Inhabited α] (msg : String) : α := default

-- fn find(items: List[Item], name: String) -> Option[Int]
def find (items : Array Item) (name : String) : Option Int := Id.run do
  for h : i in [0:items.size] do
    if items[i].name == name then
      return some i
  return none

-- fn isqrt(n: Int) -> Int, requires n >= 0, ensures r*r <= n, ensures (r+1)*(r+1) > n

-- fn tax(income: Int) -> Int  (piecewise, contract: monotone)
def tax (income : Int) : Int :=
  if income ≤ 10000 then 0
  else if income ≤ 40000 then (income - 10000) / 10
  else 3000 + (income - 40000) / 5

theorem tax_nonneg (income : Int) : tax income ≥ 0 := by
  unfold tax; split <;> (try split) <;> omega

-- index with claude-lang's trap: out of range stops the program
def at! (xs : Array Item) (i : Int) : Item :=
  if h : 0 ≤ i ∧ i.toNat < xs.size then xs[i.toNat] else clTrap s!"index {i} out of range (length {xs.size})"

def restock (items : Array Item) (k : Int) : Array Item := Id.run do
  let mut out := items
  for i in [0:out.size] do
    out := out.modify i (fun it => { it with stock := it.stock + k })
  return out

def main : IO Unit := do
  let items := #[Item.mk "lamp" 2, Item.mk "key" 0]
  IO.println (repr (find items "key"))
  IO.println (repr (find items "sword"))
  IO.println (repr (restock items 3))
  IO.println (tax 55000)
  let mut big : Array Int := #[]
  for i in [0:1000000] do
    big := big.push i
  for i in [0:1000000] do
    big := big.set! i (big[i]! * 2)
  IO.println (big[999999]!)
  IO.println (at! items 5).name
  IO.println "not reached"
