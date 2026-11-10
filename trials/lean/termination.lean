-- Night 6, step 1 probe (2026-11-10): which recursive functions Lean proves terminating, with which
-- measure and tactic. Prepend the prelude of any generated file (everything before the first `def f_`).
-- Result: gcd, bs, size, eval prove; bad (base case `n == 0`, so negative n loops) correctly fails.

theorem clMod_bound (a b : Int) (m : String) (h : b ≠ 0) : 0 ≤ clMod a b m ∧ clMod a b m < b.natAbs := by
  simp only [clMod, beq_iff_eq, h, ite_false]; exact ⟨Int.emod_nonneg a h, Int.emod_lt a h⟩
theorem clDiv_lit (a : Int) (b : Nat) (m : String) (h : b ≠ 0) : clDiv a b m = a / b := by
  simp [clDiv, h]

def f_gcd (v_a : Int) (v_b : Int) : Int := Id.run do
  if (v_b == (0 : Int)) then
    return v_a
  return (f_gcd v_b (clMod v_a v_b "x"))
termination_by v_b.natAbs
decreasing_by all_goals (simp_wf; first | omega | grind [clMod_bound, clDiv])

def f_bad (v_n : Int) : Int := Id.run do
  if (v_n == (0 : Int)) then
    return 0
  return f_bad (v_n - 1)
termination_by v_n.toNat
decreasing_by all_goals (simp_wf; first | omega | grind [clMod_bound, clDiv])

def f_bs (v_xs : Array Int) (v_lo : Int) (v_hi : Int) : Int := Id.run do
  if (v_lo >= v_hi) then
    return v_lo
  let v_mid : Int := clDiv (v_lo + v_hi) (2 : Int) "x"
  if v_mid < 5 then
    return f_bs v_xs (v_mid + 1) v_hi
  return f_bs v_xs v_lo v_mid
termination_by (v_hi - v_lo + 1).toNat
decreasing_by all_goals (simp_wf; first | omega | grind [clMod_bound, clDiv])

structure T_Tree where
  v_val : Int
  v_kids : Array T_Tree
deriving Inhabited

theorem T_Tree.clSize_v_kids (r : T_Tree) : sizeOf r.v_kids < sizeOf r := by cases r; simp; omega

def f_size (v_t : T_Tree) : Int := Id.run do
  let mut v_n : Int := 1
  for v_k in v_t.v_kids do
    v_n := v_n + f_size v_k
  return v_n
decreasing_by all_goals (simp_wf; have := Array.sizeOf_lt_of_mem ‹_ ∈ _›; have := T_Tree.clSize_v_kids v_t; omega)

inductive T_Expr where
  | v_Num (v_n : Int)
  | v_Add (v_l : T_Expr) (v_r : T_Expr)
deriving Inhabited

def f_eval (v_e : T_Expr) : Int := Id.run do
  match v_e with
  | .v_Num v_n => return v_n
  | .v_Add v_l v_r => return f_eval v_l + f_eval v_r

#print axioms f_gcd
#print axioms f_bad
#print axioms f_bs
#print axioms f_size
#print axioms f_eval
#eval f_bs #[] 0 100
