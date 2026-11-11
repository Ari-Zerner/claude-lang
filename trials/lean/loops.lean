-- Night 7, step 3 probe (2026-11-11): loops as recursive functions, so a function with a loop is a total `def`
-- and its `ensures` can be proved (D26 stage 4(c), loops). Prepend the prelude of any generated file
-- (everything before the first `def f_`): `python3 -c "import cl_lean; print(cl_lean.PRELUDE)"`.
-- Each loop becomes `f.loopN` over the variables it reads and assigns: first the run-time `invariant` check
-- (so the invariant is a hypothesis below it, as `requires` is in D29), then the condition, then the body and
-- the recursive call. `termination_by` comes from a `decreases` line (`while`) or from the range (`for`).
-- Results: all four functions below are proved end to end (the loop stops, the loop keeps its invariant, the
-- function's `ensures` follows) by `fun_induction <;> grind` and `unfold; grind`, 2.9 s CPU for the file with
-- the prelude. Only isqrt's second measure, `n - r`, fails: it needs (r + 1)^2 >= r + 1. Compiled, a loop
-- like this runs as fast as the `do` loop and still updates an array in place (3M iterations: ~0.5 s both,
-- same peak memory). The other route is in loops_mvcgen.lean.

/-- `%` by a positive number, in the form a `decreases y` proof needs (`clMod_bound` speaks of `natAbs`). -/
theorem clMod_pos (a b : Int) (m : String) (h : 0 < b) : 0 ≤ clMod a b m ∧ clMod a b m < b := by
  have hb : b ≠ 0 := by omega
  simp only [clMod, beq_iff_eq, hb, ite_false]; exact ⟨Int.emod_nonneg a hb, Int.emod_lt_of_pos a h⟩
grind_pattern clMod_pos => clMod a b m

-- (1) fn isqrt(n: Int) -> Int
--       requires n >= 0
--       ensures result * result <= n and (result + 1) * (result + 1) > n
--       var r = 0
--       while (r + 1) * (r + 1) <= n
--         invariant r >= 0 and r * r <= n
--         decreases n - r * r
--         r = r + 1
--       end while
--       return r
def f_isqrt.loop1 (v_n : Int) (v_r : Int) : Int := Id.run do
  if !(((decide (v_r >= (0 : Int))) && (decide ((v_r * v_r) <= v_n)))) then
    return clTrap "isqrt.cl:6:5: runtime error: `invariant r >= 0 and r * r <= n` is broken"
  if (decide (((v_r + (1 : Int)) * (v_r + (1 : Int))) <= v_n)) then
    return f_isqrt.loop1 v_n (v_r + (1 : Int))
  return v_r
termination_by (v_n - v_r * v_r).toNat
decreasing_by all_goals ((try simp_wf); first | omega | grind)
#print axioms f_isqrt.loop1

-- the same loop with the more obvious measure `n - r`, which needs (r + 1)^2 >= r + 1
def f_isqrt.loop1b (v_n : Int) (v_r : Int) : Int := Id.run do
  if !(((decide (v_r >= (0 : Int))) && (decide ((v_r * v_r) <= v_n)))) then
    return clTrap "invariant"
  if (decide (((v_r + (1 : Int)) * (v_r + (1 : Int))) <= v_n)) then
    return f_isqrt.loop1b v_n (v_r + (1 : Int))
  return v_r
termination_by (v_n - v_r).toNat
decreasing_by all_goals ((try simp_wf); first | omega | grind | sorry)
#print axioms f_isqrt.loop1b

-- What the loop gives its function: entered with the invariant, it ends with the invariant and without the
-- condition.
theorem f_isqrt.loop1_spec (v_n : Int) (v_r : Int)
    (cl_inv : ((decide (v_r >= (0 : Int))) && (decide ((v_r * v_r) <= v_n)))) :
    (((decide ((f_isqrt.loop1 v_n v_r) >= (0 : Int))) && (decide (((f_isqrt.loop1 v_n v_r) * (f_isqrt.loop1 v_n v_r)) <= v_n)))
      && !(decide ((((f_isqrt.loop1 v_n v_r) + (1 : Int)) * ((f_isqrt.loop1 v_n v_r) + (1 : Int))) <= v_n))) := by
  first
  | (fun_induction f_isqrt.loop1 v_n v_r <;> grind)
  | sorry
#print axioms f_isqrt.loop1_spec
grind_pattern f_isqrt.loop1_spec => f_isqrt.loop1 v_n v_r

def f_isqrt (cl_loc : String) (v_n : Int) : Int := Id.run do
  if (decide (v_n >= (0 : Int))) then
    let mut v_r : Int := (0 : Int)
    v_r := f_isqrt.loop1 v_n v_r
    let cl_result : Int := v_r
    if !(((decide ((cl_result * cl_result) <= v_n)) && (decide (((cl_result + (1 : Int)) * (cl_result + (1 : Int))) > v_n)))) then
      return clTrap "ensures"
    return cl_result
  else
    return clTrap (cl_loc ++ ": requires")

theorem clSpec_isqrt_1 (cl_loc : String) (v_n : Int) (cl_h0 : (decide (v_n >= (0 : Int)))) :
    ((decide (((f_isqrt cl_loc v_n) * (f_isqrt cl_loc v_n)) <= v_n)) && (decide ((((f_isqrt cl_loc v_n) + (1 : Int)) * ((f_isqrt cl_loc v_n) + (1 : Int))) > v_n))) := by
  first
  | (unfold f_isqrt; grind [clMod_bound, clDiv])
  | sorry
#print axioms clSpec_isqrt_1

-- (2) fn triangle(n: Int) -> Int
--       requires n >= 0
--       ensures result * 2 == n * (n + 1)
--       var t = 0
--       for i in 1 through n
--         invariant t * 2 == (i - 1) * i
--         t = t + i
--       end for
--       return t
-- The loop variable is a parameter; `i <= n + 1` is the compiler's own invariant for a range, since the
-- exit needs "i is one past the end", not just "i is past the end".
def f_triangle.loop1 (v_n : Int) (v_i : Int) (v_t : Int) : Int := Id.run do
  if !((decide ((v_t * (2 : Int)) == ((v_i - (1 : Int)) * v_i)))) then
    return clTrap "invariant"
  if (decide (v_i <= v_n)) then
    return f_triangle.loop1 v_n (v_i + (1 : Int)) (v_t + v_i)
  return v_t
termination_by (v_n + 1 - v_i).toNat
decreasing_by all_goals ((try simp_wf); first | omega | grind)
#print axioms f_triangle.loop1

theorem f_triangle.loop1_spec (v_n : Int) (v_i : Int) (v_t : Int)
    (cl_range : (decide ((1 : Int) <= v_i)) && (decide (v_i <= v_n + (1 : Int))))
    (cl_inv : (decide ((v_t * (2 : Int)) == ((v_i - (1 : Int)) * v_i)))) :
    (decide (((f_triangle.loop1 v_n v_i v_t) * (2 : Int)) == (((v_n + (1 : Int)) - (1 : Int)) * (v_n + (1 : Int))))) := by
  first
  | (fun_induction f_triangle.loop1 v_n v_i v_t <;> grind)
  | sorry
#print axioms f_triangle.loop1_spec
grind_pattern f_triangle.loop1_spec => f_triangle.loop1 v_n v_i v_t

def f_triangle (cl_loc : String) (v_n : Int) : Int := Id.run do
  if (decide (v_n >= (0 : Int))) then
    let mut v_t : Int := (0 : Int)
    v_t := f_triangle.loop1 v_n (1 : Int) v_t
    let cl_result : Int := v_t
    if !((decide ((cl_result * (2 : Int)) == (v_n * (v_n + (1 : Int)))))) then
      return clTrap "ensures"
    return cl_result
  else
    return clTrap (cl_loc ++ ": requires")

theorem clSpec_triangle_0 (cl_loc : String) (v_n : Int) (cl_h0 : (decide (v_n >= (0 : Int)))) :
    (decide (((f_triangle cl_loc v_n) * (2 : Int)) == (v_n * (v_n + (1 : Int))))) := by
  first
  | (unfold f_triangle; grind [clMod_bound, clDiv])
  | sorry
#print axioms clSpec_triangle_0

-- (3) two variables: the loop returns a pair.
--     fn gcd(a: Int, b: Int) -> Int
--       requires a >= 0 and b >= 0
--       ensures result >= 0
--       var x = a
--       var y = b
--       while y != 0
--         invariant x >= 0 and y >= 0
--         decreases y
--         let t = x % y
--         x = y
--         y = t
--       end while
--       return x
def f_gcd.loop1 (v_x : Int) (v_y : Int) : Int × Int := Id.run do
  if !(((decide (v_x >= (0 : Int))) && (decide (v_y >= (0 : Int))))) then
    return clTrap "invariant"
  if (decide (v_y != (0 : Int))) then
    let v_t : Int := clMod v_x v_y "div0"
    return f_gcd.loop1 v_y v_t
  return (v_x, v_y)
termination_by v_y.toNat
decreasing_by all_goals ((try simp_wf); first | omega | grind [clMod_bound, clDiv] | sorry)
#print axioms f_gcd.loop1

theorem f_gcd.loop1_spec (v_x : Int) (v_y : Int)
    (cl_inv : ((decide (v_x >= (0 : Int))) && (decide (v_y >= (0 : Int))))) :
    (((decide ((f_gcd.loop1 v_x v_y).1 >= (0 : Int))) && (decide ((f_gcd.loop1 v_x v_y).2 >= (0 : Int))))
      && !(decide ((f_gcd.loop1 v_x v_y).2 != (0 : Int)))) := by
  first
  | (fun_induction f_gcd.loop1 v_x v_y <;> grind [clMod_bound, clDiv])
  | sorry
#print axioms f_gcd.loop1_spec
grind_pattern f_gcd.loop1_spec => f_gcd.loop1 v_x v_y

def f_gcd (cl_loc : String) (v_a : Int) (v_b : Int) : Int := Id.run do
  if ((decide (v_a >= (0 : Int))) && (decide (v_b >= (0 : Int)))) then
    let mut v_x : Int := v_a
    let mut v_y : Int := v_b
    (v_x, v_y) := f_gcd.loop1 v_x v_y
    let cl_result : Int := v_x
    if !((decide (cl_result >= (0 : Int)))) then
      return clTrap "ensures"
    return cl_result
  else
    return clTrap (cl_loc ++ ": requires")

theorem clSpec_gcd_0 (cl_loc : String) (v_a : Int) (v_b : Int)
    (cl_h0 : ((decide (v_a >= (0 : Int))) && (decide (v_b >= (0 : Int))))) :
    (decide ((f_gcd cl_loc v_a v_b) >= (0 : Int))) := by
  first
  | (unfold f_gcd; grind [clMod_bound, clDiv])
  | sorry
#print axioms clSpec_gcd_0

-- (4) a list in the loop's state.
--     fn count_up(n: Int) -> List[Int]
--       requires n >= 0
--       ensures length(result) == n
--       var xs: List[Int] = []
--       for i in 0 until n
--         invariant length(xs) == i
--         xs = append(list: xs, item: i)
--       end for
--       return xs
def f_count_up.loop1 (v_n : Int) (v_i : Int) (v_xs : Array Int) : Array Int := Id.run do
  if !((decide ((v_xs.size : Int) == v_i))) then
    return clTrap "invariant"
  if (decide (v_i < v_n)) then
    return f_count_up.loop1 v_n (v_i + (1 : Int)) (v_xs.push v_i)
  return v_xs
termination_by (v_n - v_i).toNat
decreasing_by all_goals ((try simp_wf); first | omega | grind)
#print axioms f_count_up.loop1

theorem f_count_up.loop1_spec (v_n : Int) (v_i : Int) (v_xs : Array Int)
    (cl_range : (decide ((0 : Int) <= v_i)) && (decide (v_i <= v_n)))
    (cl_inv : (decide ((v_xs.size : Int) == v_i))) :
    (decide (((f_count_up.loop1 v_n v_i v_xs).size : Int) == v_n)) := by
  first
  | (fun_induction f_count_up.loop1 v_n v_i v_xs <;> grind)
  | sorry
#print axioms f_count_up.loop1_spec
grind_pattern f_count_up.loop1_spec => f_count_up.loop1 v_n v_i v_xs

def f_count_up (cl_loc : String) (v_n : Int) : Array Int := Id.run do
  if (decide (v_n >= (0 : Int))) then
    let mut v_xs : Array Int := (#[] : Array Int)
    v_xs := f_count_up.loop1 v_n (0 : Int) v_xs
    let cl_result : Array Int := v_xs
    if !((decide ((cl_result.size : Int) == v_n))) then
      return clTrap "ensures"
    return cl_result
  else
    return clTrap (cl_loc ++ ": requires")

theorem clSpec_count_up_0 (cl_loc : String) (v_n : Int) (cl_h0 : (decide (v_n >= (0 : Int)))) :
    (decide (((f_count_up cl_loc v_n).size : Int) == v_n)) := by
  first
  | (unfold f_count_up; grind [clMod_bound, clDiv])
  | sorry
#print axioms clSpec_count_up_0

#eval (f_isqrt "x" 99, f_triangle "x" 100, f_gcd "x" 48 36, f_count_up "x" 5)
