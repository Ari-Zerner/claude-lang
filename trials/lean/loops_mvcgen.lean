-- Night 7, step 3 probe (2026-11-11), the other route: keep each loop as the `do` loop the compiler emits
-- today, and prove the function with Lean's own verification-condition generator, `mvcgen`, given the loop's
-- invariant (and, for a `while`, a variant = `decreases`). To run: a file with `import Std.Tactic.Do`,
-- `open Std.Do`, then the prelude of any generated file, then this.
-- Results:
-- * isqrt (`while`): PROVED, on the function exactly as clc emits it (the `requires` wrapper, the run-time
--   `ensures` check, `decide` conditions). No change to the generated program at all.
-- * triangle (`for i in 1 through n`): mvcgen does its part, but two goals stay open: `grind` doesn't know
--   that the item after a prefix of `(1...=n).toList` is `1 + prefix.length`, or how long the whole list is.
--   Two prelude lemmas would say so (`Init/Data/Range/Polymorphic/IntLemmas.lean` has the raw material).
-- * `mvcgen` is marked deprecated in Lean 4.35 in favour of `vcgen`, which is marked experimental and lives in
--   a different library (`Std.WP`): swapping the name here fails with "Unknown constant Std.WP.Triple.intro".
-- * `import Std.Tactic.Do` costs ~0.3 s CPU. (`import Lean` is what costs 40-60 s.)
-- * Lean 4.35's `while` is not `partial` any more: `Loop.forIn` is `repeatM`, with `WhileInvariant` and
--   `WhileVariant` specs. NOTES said otherwise until tonight.

set_option linter.deprecated.syntax false

def f_isqrt (cl_loc : String) (v_n : Int) : Int := Id.run do
  if (decide (v_n >= (0 : Int))) then
    let mut v_r : Int := (0 : Int)
    while (decide (((v_r + (1 : Int)) * (v_r + (1 : Int))) <= v_n)) do
      v_r := (v_r + (1 : Int))
    let cl_result : Int := v_r
    if !((decide (cl_result >= (0 : Int)))) then
      return clTrap ("tests/ok/contracts.cl:26:3: runtime error: " ++ ("isqrt(" ++ "n: " ++ (toString v_n) ++ ")") ++ " returned " ++ (toString cl_result) ++ ", which breaks `ensures result >= 0` (line 18)")
    if !(((decide ((cl_result * cl_result) <= v_n)) && (decide (((cl_result + (1 : Int)) * (cl_result + (1 : Int))) > v_n)))) then
      return clTrap ("tests/ok/contracts.cl:26:3: runtime error: " ++ ("isqrt(" ++ "n: " ++ (toString v_n) ++ ")") ++ " returned " ++ (toString cl_result) ++ ", which breaks `ensures result * result <= n and (result + 1) * (result + 1) > n` (line 19)")
    return cl_result
  else
    return clTrap (cl_loc ++ ": runtime error: this call breaks `requires n >= 0` of fn isqrt (line 17): " ++ ("isqrt(" ++ "n: " ++ (toString v_n) ++ ")"))


theorem clSpec_isqrt_1 (cl_loc : String) (v_n : Int) (cl_h0 : (decide (v_n >= (0 : Int)))) :
    ((decide (((f_isqrt cl_loc v_n) * (f_isqrt cl_loc v_n)) <= v_n)) && (decide ((((f_isqrt cl_loc v_n) + (1 : Int)) * ((f_isqrt cl_loc v_n) + (1 : Int))) > v_n))) := by
  generalize cl_h : f_isqrt cl_loc v_n = cl_r
  apply Id.of_wp_run_eq cl_h
  mvcgen
  case inv1 => exact fun v_r => ⟨(v_n - v_r * v_r).toNat⟩
  case inv2 => exact ⇓ cl_s => match cl_s with
    | .inl v_r => ⌜((decide (v_r >= (0 : Int))) && (decide ((v_r * v_r) <= v_n)))⌝
    | .inr v_r => ⌜((decide (v_r >= (0 : Int))) && (decide ((v_r * v_r) <= v_n))) ∧ ¬ (decide (((v_r + (1 : Int)) * (v_r + (1 : Int))) <= v_n))⌝
  all_goals (first | (mleave; grind) | (trace_state; sorry))
#print axioms clSpec_isqrt_1

-- two goals stay open here (`sorry`): see above
def f_triangle (cl_loc : String) (v_n : Int) : Int := Id.run do
  if (decide (v_n >= (0 : Int))) then
    let mut v_t : Int := (0 : Int)
    for v_i in (1 : Int)...=v_n do
      v_t := (v_t + v_i)
    let cl_result : Int := v_t
    if !(((cl_result * (2 : Int)) == (v_n * (v_n + (1 : Int))))) then
      return clTrap ("tri.cl:9:3: runtime error: " ++ ("triangle(" ++ "n: " ++ (toString v_n) ++ ")") ++ " returned " ++ (toString cl_result) ++ ", which breaks `ensures result * 2 == n * (n + 1)` (line 3)")
    return cl_result
  else
    return clTrap (cl_loc ++ ": runtime error: this call breaks `requires n >= 0` of fn triangle (line 2): " ++ ("triangle(" ++ "n: " ++ (toString v_n) ++ ")"))


theorem clSpec_triangle_0 (cl_loc : String) (v_n : Int) (cl_h0 : (decide (v_n >= (0 : Int)))) :
    (((f_triangle cl_loc v_n) * (2 : Int)) == (v_n * (v_n + (1 : Int)))) := by
  generalize cl_h : f_triangle cl_loc v_n = cl_r
  apply Id.of_wp_run_eq cl_h
  mvcgen
  case inv1 => exact ⇓⟨cl_c, v_t⟩ => ⌜(v_t * (2 : Int)) == ((((1 : Int) + cl_c.prefix.length) - (1 : Int)) * ((1 : Int) + cl_c.prefix.length))⌝
  all_goals (first | (mleave; grind) | (trace_state; sorry))
#print axioms clSpec_triangle_0
