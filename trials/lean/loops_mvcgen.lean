-- Night 7, steps 3-4 probe (2026-11-11), the route D33 takes: each loop stays the `do` loop clc emits today,
-- and the function's `ensures` is proved with Lean's verification-condition generator, `mvcgen`, from the
-- loop's invariant (and, for a `while`, a variant = its `decreases`). The five functions below are exactly
-- what clc emits now (paths in messages shortened); only the proofs are new, and every invariant term is
-- one clc can write mechanically from `invariant`/`decreases` lines. To run: a file with
-- `import Std.Tactic.Do`, `open Std.Do`, then the prelude of any generated file, then this.
-- Results (4.9 s CPU for all five with the prelude; `import Std.Tactic.Do` is ~0.3 s of it):
-- * isqrt (`while`), triangle (`for ... through`), count_up (`for ... until`, a list), gcd (`while`, two
--   variables: the state is the tuple of the loop's `var`s in the order they're declared), first_square
--   (an early `return` inside a `for`: the state gains an `Option` holding the returned value, and the
--   invariant says the `ensures` holds for it): ALL PROVED by one fixed tactic.
-- * What it took: two lemmas about `for` over an Int range (`clRco_cur`, `clRcc_cur`: the item after a
--   prefix is the start plus the prefix's length, and inside the range) with explicit `grind_pattern`s
--   (without them `grind` didn't use them where the invariant doesn't mention the index); `clMod_pos`;
--   invariants written with projections (`cl_x.2.1`), not tuple patterns, which block on an opaque state;
--   `simp only [clTrap, ...]` first, so the long trap messages are gone before `grind`.
-- * `mvcgen` is marked deprecated in Lean 4.35 in favour of `vcgen`, which is marked experimental, lives in
--   another library (`Std.WP`) and fails as a drop-in here ("Unknown constant Std.WP.Triple.intro"). This
--   project pins Lean 4.35, so that bites only on an upgrade.
-- * Lean 4.35's `while` is not `partial` any more: `Loop.forIn` is `repeatM`, with `WhileInvariant` and
--   `WhileVariant` specs.

set_option linter.deprecated.syntax false

/-- In a `for` over a range, the item after a prefix is the start plus the prefix's length, and inside the
range. -/
theorem clRco_cur {lo hi cur : Int} {pref suff : List Int} (h : (lo...hi).toList = pref ++ cur :: suff) :
    cur = lo + pref.length ∧ cur < hi := by
  have h1 : (lo...hi).toList[pref.length]? = some cur := by simp [h]
  rw [Int.getElem?_toList_rco_eq_some_iff] at h1
  omega
theorem clRcc_cur {lo hi cur : Int} {pref suff : List Int} (h : (lo...=hi).toList = pref ++ cur :: suff) :
    cur = lo + pref.length ∧ cur ≤ hi := by
  have h1 : (lo...=hi).toList[pref.length]? = some cur := by simp [h]
  rw [Int.getElem?_toList_rcc_eq_some_iff] at h1
  omega
grind_pattern clRco_cur => (lo...hi).toList, pref ++ cur :: suff
grind_pattern clRcc_cur => (lo...=hi).toList, pref ++ cur :: suff
/-- `%` by a positive number, in the form a `decreases y` proof needs (`clMod_bound` speaks of `natAbs`). -/
theorem clMod_pos (a b : Int) (m : String) (h : 0 < b) : 0 ≤ clMod a b m ∧ clMod a b m < b := by
  have hb : b ≠ 0 := by omega
  simp only [clMod, beq_iff_eq, hb, ite_false]; exact ⟨Int.emod_nonneg a hb, Int.emod_lt_of_pos a h⟩
grind_pattern clMod_pos => clMod a b m

-- while (r + 1) * (r + 1) <= n / invariant r >= 0 and r * r <= n / decreases n - r * r
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

axiom clUnproved_isqrt_0 (cl_loc : String) (v_n : Int) (cl_h0 : (decide (v_n >= (0 : Int)))) :
    ((decide (((f_isqrt cl_loc v_n) * (f_isqrt cl_loc v_n)) <= v_n)) && (decide ((((f_isqrt cl_loc v_n) + (1 : Int)) * ((f_isqrt cl_loc v_n) + (1 : Int))) > v_n)))
theorem clSpec_isqrt_0 (cl_loc : String) (v_n : Int) (cl_h0 : (decide (v_n >= (0 : Int)))) :
    ((decide (((f_isqrt cl_loc v_n) * (f_isqrt cl_loc v_n)) <= v_n)) && (decide ((((f_isqrt cl_loc v_n) + (1 : Int)) * ((f_isqrt cl_loc v_n) + (1 : Int))) > v_n))) := by
  first
  | (generalize cl_h : f_isqrt cl_loc v_n = cl_r
     apply Id.of_wp_run_eq cl_h
     mvcgen
     case inv1 => exact fun cl_s => let v_r := cl_s; ⟨(v_n - v_r * v_r).toNat⟩
     case inv2 => exact ⇓ cl_x => match cl_x with
       | .inl cl_s => ⌜let v_r := cl_s; ((decide (v_r >= (0 : Int))) && (decide ((v_r * v_r) <= v_n))) = true⌝
       | .inr cl_s => ⌜let v_r := cl_s; ((decide (v_r >= (0 : Int))) && (decide ((v_r * v_r) <= v_n))) = true ∧ ¬ (decide (((v_r + (1 : Int)) * (v_r + (1 : Int))) <= v_n)) = true⌝
     all_goals (mleave; (try simp only [clTrap, List.length_append, List.length_cons, List.length_nil, Int.length_toList_rcc, Int.length_toList_rco] at *); grind [clMod_bound, clDiv]))
  | exact clUnproved_isqrt_0 cl_loc v_n cl_h0
#print axioms clSpec_isqrt_0

-- for i in 1 through n / invariant t * 2 == (i - 1) * i
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

axiom clUnproved_triangle_0 (cl_loc : String) (v_n : Int) (cl_h0 : (decide (v_n >= (0 : Int)))) :
    (((f_triangle cl_loc v_n) * (2 : Int)) == (v_n * (v_n + (1 : Int))))
theorem clSpec_triangle_0 (cl_loc : String) (v_n : Int) (cl_h0 : (decide (v_n >= (0 : Int)))) :
    (((f_triangle cl_loc v_n) * (2 : Int)) == (v_n * (v_n + (1 : Int)))) := by
  first
  | (generalize cl_h : f_triangle cl_loc v_n = cl_r
     apply Id.of_wp_run_eq cl_h
     mvcgen
     case inv1 => exact ⇓ cl_x => ⌜let v_i : Int := (1 : Int) + cl_x.1.prefix.length; let v_t := cl_x.2; ((v_t * (2 : Int)) == ((v_i - (1 : Int)) * v_i)) = true⌝
     all_goals (mleave; (try simp only [clTrap, List.length_append, List.length_cons, List.length_nil, Int.length_toList_rcc, Int.length_toList_rco] at *); grind [clMod_bound, clDiv]))
  | exact clUnproved_triangle_0 cl_loc v_n cl_h0
#print axioms clSpec_triangle_0

-- for i in 0 until n / invariant length(xs) == i
def f_count_up (cl_loc : String) (v_n : Int) : (Array Int) := Id.run do
  if (decide (v_n >= (0 : Int))) then
    let mut v_xs : (Array Int) := (#[] : (Array Int))
    for v_i in (0 : Int)...<v_n do
      v_xs := (v_xs.push v_i)
    let cl_result : (Array Int) := v_xs
    if !(((Int.ofNat cl_result.size) == v_n)) then
      return clTrap ("tri.cl:28:3: runtime error: " ++ ("count_up(" ++ "n: " ++ (toString v_n) ++ ")") ++ " returned " ++ (clFmtArray (fun cl_y0_0 => (toString cl_y0_0)) cl_result) ++ ", which breaks `ensures length(result) == n` (line 23)")
    return cl_result
  else
    return clTrap (cl_loc ++ ": runtime error: this call breaks `requires n >= 0` of fn count_up (line 22): " ++ ("count_up(" ++ "n: " ++ (toString v_n) ++ ")"))

axiom clUnproved_count_up_0 (cl_loc : String) (v_n : Int) (cl_h0 : (decide (v_n >= (0 : Int)))) :
    ((Int.ofNat (f_count_up cl_loc v_n).size) == v_n)
theorem clSpec_count_up_0 (cl_loc : String) (v_n : Int) (cl_h0 : (decide (v_n >= (0 : Int)))) :
    ((Int.ofNat (f_count_up cl_loc v_n).size) == v_n) := by
  first
  | (generalize cl_h : f_count_up cl_loc v_n = cl_r
     apply Id.of_wp_run_eq cl_h
     mvcgen
     case inv1 => exact ⇓ cl_x => ⌜let v_i : Int := (0 : Int) + cl_x.1.prefix.length; let v_xs := cl_x.2; ((Int.ofNat v_xs.size) == v_i) = true⌝
     all_goals (mleave; (try simp only [clTrap, List.length_append, List.length_cons, List.length_nil, Int.length_toList_rcc, Int.length_toList_rco] at *); grind [clMod_bound, clDiv]))
  | exact clUnproved_count_up_0 cl_loc v_n cl_h0
#print axioms clSpec_count_up_0

-- while y != 0 / invariant x >= 0 and y >= 0 / decreases y
def f_gcd (cl_loc : String) (v_a : Int) (v_b : Int) : Int := Id.run do
  if ((decide (v_a >= (0 : Int))) && (decide (v_b >= (0 : Int)))) then
    let mut v_x : Int := v_a
    let mut v_y : Int := v_b
    while (v_y != (0 : Int)) do
      let v_t : Int := (clMod v_x v_y "two.cl:8:15: runtime error: division by zero in `%`")
      v_x := v_y
      v_y := v_t
    let cl_result : Int := v_x
    if !((decide (cl_result >= (0 : Int)))) then
      return clTrap ("two.cl:12:3: runtime error: " ++ ("gcd(" ++ "a: " ++ (toString v_a) ++ ", b: " ++ (toString v_b) ++ ")") ++ " returned " ++ (toString cl_result) ++ ", which breaks `ensures result >= 0` (line 3)")
    return cl_result
  else
    return clTrap (cl_loc ++ ": runtime error: this call breaks `requires a >= 0 and b >= 0` of fn gcd (line 2): " ++ ("gcd(" ++ "a: " ++ (toString v_a) ++ ", b: " ++ (toString v_b) ++ ")"))

axiom clUnproved_gcd_0 (cl_loc : String) (v_a : Int) (v_b : Int) (cl_h0 : ((decide (v_a >= (0 : Int))) && (decide (v_b >= (0 : Int))))) :
    (decide ((f_gcd cl_loc v_a v_b) >= (0 : Int)))
theorem clSpec_gcd_0 (cl_loc : String) (v_a : Int) (v_b : Int) (cl_h0 : ((decide (v_a >= (0 : Int))) && (decide (v_b >= (0 : Int))))) :
    (decide ((f_gcd cl_loc v_a v_b) >= (0 : Int))) := by
  first
  | (generalize cl_h : f_gcd cl_loc v_a v_b = cl_r
     apply Id.of_wp_run_eq cl_h
     mvcgen
     case inv1 => exact fun cl_s => let v_x := cl_s.1; let v_y := cl_s.2; ⟨(v_y).toNat⟩
     case inv2 => exact ⇓ cl_x => match cl_x with
       | .inl cl_s => ⌜let v_x := cl_s.1; let v_y := cl_s.2; ((decide (v_x >= (0 : Int))) && (decide (v_y >= (0 : Int)))) = true⌝
       | .inr cl_s => ⌜let v_x := cl_s.1; let v_y := cl_s.2; ((decide (v_x >= (0 : Int))) && (decide (v_y >= (0 : Int)))) = true ∧ ¬ (v_y != (0 : Int)) = true⌝
     all_goals (mleave; (try simp only [clTrap, List.length_append, List.length_cons, List.length_nil, Int.length_toList_rcc, Int.length_toList_rco] at *); grind [clMod_bound, clDiv]))
  | exact clUnproved_gcd_0 cl_loc v_a v_b cl_h0
#print axioms clSpec_gcd_0

-- for i in lo until hi, with `return i` inside it; no `invariant` line at all
def f_first_square (cl_loc : String) (v_target : Int) (v_lo : Int) (v_hi : Int) : Int := Id.run do
  if (decide (v_lo <= v_hi)) then
    for v_i in v_lo...<v_hi do
      if (decide ((v_i * v_i) >= v_target)) then
        let cl_result : Int := v_i
        if !(((decide (cl_result >= v_lo)) && (decide (cl_result <= v_hi)))) then
          return clTrap ("two.cl:22:7: runtime error: " ++ ("first_square(" ++ "target: " ++ (toString v_target) ++ ", lo: " ++ (toString v_lo) ++ ", hi: " ++ (toString v_hi) ++ ")") ++ " returned " ++ (toString cl_result) ++ ", which breaks `ensures result >= lo and result <= hi` (line 18)")
        return cl_result
    let cl_result : Int := v_hi
    if !(((decide (cl_result >= v_lo)) && (decide (cl_result <= v_hi)))) then
      return clTrap ("two.cl:25:3: runtime error: " ++ ("first_square(" ++ "target: " ++ (toString v_target) ++ ", lo: " ++ (toString v_lo) ++ ", hi: " ++ (toString v_hi) ++ ")") ++ " returned " ++ (toString cl_result) ++ ", which breaks `ensures result >= lo and result <= hi` (line 18)")
    return cl_result
  else
    return clTrap (cl_loc ++ ": runtime error: this call breaks `requires lo <= hi` of fn first_square (line 17): " ++ ("first_square(" ++ "target: " ++ (toString v_target) ++ ", lo: " ++ (toString v_lo) ++ ", hi: " ++ (toString v_hi) ++ ")"))

axiom clUnproved_first_square_0 (cl_loc : String) (v_target : Int) (v_lo : Int) (v_hi : Int) (cl_h0 : (decide (v_lo <= v_hi))) :
    ((decide ((f_first_square cl_loc v_target v_lo v_hi) >= v_lo)) && (decide ((f_first_square cl_loc v_target v_lo v_hi) <= v_hi)))
theorem clSpec_first_square_0 (cl_loc : String) (v_target : Int) (v_lo : Int) (v_hi : Int) (cl_h0 : (decide (v_lo <= v_hi))) :
    ((decide ((f_first_square cl_loc v_target v_lo v_hi) >= v_lo)) && (decide ((f_first_square cl_loc v_target v_lo v_hi) <= v_hi))) := by
  first
  | (generalize cl_h : f_first_square cl_loc v_target v_lo v_hi = cl_r
     apply Id.of_wp_run_eq cl_h
     mvcgen
     case inv1 => exact ⇓ cl_x => ⌜∀ cl_v, cl_x.2.1 = some cl_v → ((decide (cl_v >= v_lo)) && (decide (cl_v <= v_hi))) = true⌝
     all_goals (mleave; (try simp only [clTrap, List.length_append, List.length_cons, List.length_nil, Int.length_toList_rcc, Int.length_toList_rco] at *); grind [clMod_bound, clDiv]))
  | exact clUnproved_first_square_0 cl_loc v_target v_lo v_hi cl_h0
#print axioms clSpec_first_square_0

