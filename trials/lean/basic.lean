import Std.Tactic.BVDecide
-- core Lean only (no imports beyond the prelude)
theorem t_omega (a b : Int) (h : a < b) : a + 1 ≤ b := by omega
theorem t_grind (a b c : Int) (h1 : a = b) (h2 : b = c) : a = c := by grind
theorem t_bv (x y : BitVec 8) : x + y = y + x := by bv_decide

def sumTo : Nat → Nat
  | 0 => 0
  | n+1 => (n+1) + sumTo n

theorem t_sum (n : Nat) : 2 * sumTo n = n * (n + 1) := by
  induction n with
  | zero => rfl
  | succ k ih => simp only [sumTo]; grind

-- Lean's quiet defaults, for the record
#eval (5 - 7 : Nat)
#eval (7 / 0 : Int)
