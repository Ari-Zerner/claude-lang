import Std.Tactic.Do
open Std.Do

def mySum (l : List Nat) : Nat := Id.run do
  let mut out := 0
  for x in l do
    out := out + x
  return out

theorem mySum_correct (l : List Nat) : mySum l = l.sum := by
  generalize h : mySum l = r
  apply Id.of_wp_run_eq h
  mvcgen
  case inv1 => exact ⇓⟨xs, out⟩ => ⌜xs.prefix.sum = out⌝
  all_goals mleave; simp_all
