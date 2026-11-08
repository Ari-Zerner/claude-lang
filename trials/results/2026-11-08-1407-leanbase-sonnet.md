# Lean-direct baseline 2026-11-08-1407 (sonnet)

| task | result | lines | Lean s per attempt |
|---|---|---|---|
| sum | first try | 11 | [3.9] |
| isqrt | fail | 39 | [5.0, 4.9, 5.4] |
| max | first try | 65 | [1.5] |
| isort | after 1 fix | 50 | [1.9, 2.0] |
| tax | first try | 8 | [5.7] |
| parking | first try | 26 | [3.5] |

## sum

```
    theorem sumTo_spec : ∀ n : Nat, 2 * sumTo n = n * (n + 1)
```

### attempt 1: ok (Lean 3.9 s)

```lean
def sumTo : Nat → Nat
  | 0 => 0
  | n+1 => sumTo n + (n+1)

theorem sumTo_spec : ∀ n : Nat, 2 * sumTo n = n * (n + 1) := by
  intro n
  induction n with
  | zero => rfl
  | succ k ih =>
    show 2 * (sumTo k + (k+1)) = (k+1) * (k+1+1)
    simp only [Nat.mul_add, Nat.add_mul, Nat.mul_one, Nat.one_mul] at ih ⊢
    omega
```

## isqrt

```
    theorem isqrt_spec : ∀ n : Nat, isqrt n * isqrt n ≤ n ∧ n < (isqrt n + 1) * (isqrt n + 1)
```

### attempt 1: errors (Lean 5.0 s)

```lean
def isqrtAux (n r : Nat) : Nat :=
  if n < (r + 1) * (r + 1) then r else r + 1

def isqrt (n : Nat) : Nat :=
  if h : n < 2 then n else isqrtAux n (2 * isqrt (n / 4))
termination_by n
decreasing_by omega

theorem isqrtAux_spec (n s : Nat) (hs1 : s * s ≤ n / 4) (hs2 : n / 4 < (s + 1) * (s + 1)) :
    isqrtAux n (2 * s) * isqrtAux n (2 * s) ≤ n ∧
    n < (isqrtAux n (2 * s) + 1) * (isqrtAux n (2 * s) + 1) := by
  have e1 : (s + 1) * (s + 1) = s * s + 2 * s + 1 := by
    simp only [Nat.add_mul, Nat.mul_add, Nat.mul_one, Nat.one_mul] <;> omega
  have e2 : (2 * s + 1) * (2 * s + 1) = 4 * (s * s) + 4 * s + 1 := by
    simp only [Nat.add_mul, Nat.mul_add, Nat.mul_one, Nat.one_mul, Nat.mul_comm,
      Nat.mul_left_comm, Nat.mul_assoc] <;> omega
  have e3 : (2 * s + 1 + 1) * (2 * s + 1 + 1) = 4 * (s * s) + 8 * s + 4 := by
    simp only [Nat.add_mul, Nat.mul_add, Nat.mul_one, Nat.one_mul, Nat.mul_comm,
      Nat.mul_left_comm, Nat.mul_assoc] <;> omega
  have e4 : 2 * s * (2 * s) = 4 * (s * s) := by
    simp only [Nat.add_mul, Nat.mul_add, Nat.mul_one, Nat.one_mul, Nat.mul_comm,
      Nat.mul_left_comm, Nat.mul_assoc] <;> omega
  by_cases h : n < (2 * s + 1) * (2 * s + 1)
  · rw [isqrtAux, if_pos h]
    omega
  · rw [isqrtAux, if_neg h]
    omega

theorem isqrt_spec : ∀ n : Nat, isqrt n * isqrt n ≤ n ∧ n < (isqrt n + 1) * (isqrt n + 1) := by
  intro n
  induction n using Nat.strong_induction_on with
  | _ n ih =>
    by_cases h : n < 2
    · have e : isqrt n = n := by
        conv_lhs => rw [isqrt]
        rw [dif_pos h]
      rw [e]
      have : n = 0 ∨ n = 1 := by omega
      rcases this with rfl | rfl <;> decide
    · have e : isqrt n = isqrtAux n (2 * isqrt (n / 4)) := by
        conv_lhs => rw [isqrt]
        rw [dif_neg h]
      have ih' := ih (n / 4) (by omega)
      rw [e]
      exact isqrtAux_spec n _ ih'.1 ih'.2
```

Sent back:
```
line 16:44: error: omega could not prove the goal:
a possible counterexample may satisfy the constraints
  f ≥ 0
  e ≥ 0
  e - f ≥ 1
  d ≥ 0
  c ≥ 0
  c - 2*d ≥ 1
  b ≥ 0
  a - c ≤ -1
  a - c + 2*d ≥ -1
  -3 ≤ 4*a - b ≤ 0
where
 a := ↑n / 4
 b := ↑n
 c := ↑(s + 1) * ↑(s + 1)
 d := ↑s
 e := ↑s * ↑(s * 4)
 f := ↑s * ↑(s * (2 * 2))
line 19:44: error: omega could not prove the goal:
a possible counterexample may satisfy the constraints
  f ≥ 0
  e ≥ 0
  e - f ≥ 1
  d ≥ 0
  c ≥ 0
  c - 2*d ≥ 1
  c - d ≥ 1
  b ≥ 0
  a - c ≤ -1
  a - c + 2*d ≥ -1
  -3 ≤ 4*a - b ≤ 0
where
 a := ↑n / 4
 b := ↑n
 c := ↑(s + 1) * ↑(s + 1)
 d := ↑s
 e := ↑s * ↑(s * 4)
 f := ↑s * ↑(s * (2 * 2))
line 35:9: error: unknown tactic
`isqrt_spec` depends on ['sorryAx'] (sorry, an axiom or native_decide)
```

### attempt 2: errors (Lean 4.9 s)

```lean
def isqrtAux (n r : Nat) : Nat :=
  if n < (r + 1) * (r + 1) then r else r + 1

def isqrt (n : Nat) : Nat :=
  if h : n < 2 then n else isqrtAux n (2 * isqrt (n / 4))
termination_by n
decreasing_by omega

theorem isqrtAux_spec (n s : Nat) (hs1 : s * s ≤ n / 4) (hs2 : n / 4 < (s + 1) * (s + 1)) :
    isqrtAux n (2 * s) * isqrtAux n (2 * s) ≤ n ∧
    n < (isqrtAux n (2 * s) + 1) * (isqrtAux n (2 * s) + 1) := by
  have e1 : (s + 1) * (s + 1) = s * s + 2 * s + 1 := by
    simp only [Nat.two_mul, Nat.add_mul, Nat.mul_add, Nat.mul_one, Nat.one_mul] <;> omega
  have e2 : (2 * s + 1) * (2 * s + 1) = 4 * (s * s) + 4 * s + 1 := by
    simp only [Nat.two_mul, Nat.add_mul, Nat.mul_add, Nat.mul_one, Nat.one_mul] <;> omega
  have e3 : (2 * s + 1 + 1) * (2 * s + 1 + 1) = 4 * (s * s) + 8 * s + 4 := by
    simp only [Nat.two_mul, Nat.add_mul, Nat.mul_add, Nat.mul_one, Nat.one_mul] <;> omega
  have e4 : 2 * s * (2 * s) = 4 * (s * s) := by
    simp only [Nat.two_mul, Nat.add_mul, Nat.mul_add, Nat.mul_one, Nat.one_mul] <;> omega
  by_cases h : n < (2 * s + 1) * (2 * s + 1)
  · rw [isqrtAux, if_pos h]
    omega
  · rw [isqrtAux, if_neg h]
    omega

theorem isqrt_spec : ∀ n : Nat, isqrt n * isqrt n ≤ n ∧ n < (isqrt n + 1) * (isqrt n + 1) := by
  intro n
  refine Nat.strong_induction_on n ?_
  intro n ih
  by_cases h : n < 2
  · have e : isqrt n = n := by
      conv_lhs => rw [isqrt]
      rw [dif_pos h]
    rw [e]
    have : n = 0 ∨ n = 1 := by omega
    rcases this with rfl | rfl <;> decide
  · have e : isqrt n = isqrtAux n (2 * isqrt (n / 4)) := by
      conv_lhs => rw [isqrt]
      rw [dif_neg h]
    have ih' := ih (n / 4) (by omega)
    rw [e]
    exact isqrtAux_spec n _ ih'.1 ih'.2
```

Sent back:
```
line 32:7: error: unknown tactic
`isqrt_spec` depends on ['sorryAx'] (sorry, an axiom or native_decide)
```

### attempt 3: errors (Lean 5.4 s)

```lean
def isqrtAux (n r : Nat) : Nat :=
  if n < (r + 1) * (r + 1) then r else r + 1

def isqrt (n : Nat) : Nat :=
  if h : n < 2 then n else isqrtAux n (2 * isqrt (n / 4))
termination_by n
decreasing_by omega

theorem isqrtAux_spec (n s : Nat) (hs1 : s * s ≤ n / 4) (hs2 : n / 4 < (s + 1) * (s + 1)) :
    isqrtAux n (2 * s) * isqrtAux n (2 * s) ≤ n ∧
    n < (isqrtAux n (2 * s) + 1) * (isqrtAux n (2 * s) + 1) := by
  have e1 : (s + 1) * (s + 1) = s * s + 2 * s + 1 := by
    simp only [Nat.two_mul, Nat.add_mul, Nat.mul_add, Nat.mul_one, Nat.one_mul] <;> omega
  have e2 : (2 * s + 1) * (2 * s + 1) = 4 * (s * s) + 4 * s + 1 := by
    simp only [Nat.two_mul, Nat.add_mul, Nat.mul_add, Nat.mul_one, Nat.one_mul] <;> omega
  have e3 : (2 * s + 1 + 1) * (2 * s + 1 + 1) = 4 * (s * s) + 8 * s + 4 := by
    simp only [Nat.two_mul, Nat.add_mul, Nat.mul_add, Nat.mul_one, Nat.one_mul] <;> omega
  have e4 : 2 * s * (2 * s) = 4 * (s * s) := by
    simp only [Nat.two_mul, Nat.add_mul, Nat.mul_add, Nat.mul_one, Nat.one_mul] <;> omega
  by_cases h : n < (2 * s + 1) * (2 * s + 1)
  · rw [isqrtAux, if_pos h]
    omega
  · rw [isqrtAux, if_neg h]
    omega

theorem isqrt_spec : ∀ n : Nat, isqrt n * isqrt n ≤ n ∧ n < (isqrt n + 1) * (isqrt n + 1) := by
  intro n
  refine Nat.strong_induction_on n ?_
  intro n ih
  by_cases h : n < 2
  · have e : isqrt n = n := by
      conv => lhs; rw [isqrt]
      rw [dif_pos h]
    rw [e]
    have : n = 0 ∨ n = 1 := by omega
    rcases this with rfl | rfl <;> decide
  · have e : isqrt n = isqrtAux n (2 * isqrt (n / 4)) := by
      conv => lhs; rw [isqrt]
      rw [dif_neg h]
    have ih' := ih (n / 4) (by omega)
    rw [e]
    exact isqrtAux_spec n _ ih'.1 ih'.2
```

Sent back:
```
line 28:9: error: Unknown constant `Nat.strong_induction_on`
line 29:8: error: No goals to be solved
`isqrt_spec` depends on ['sorryAx'] (sorry, an axiom or native_decide)
```

## max

```
    theorem maxList_ge : ∀ (x : Int) (xs : List Int), ∀ y ∈ x :: xs, y ≤ maxList x xs
    theorem maxList_mem : ∀ (x : Int) (xs : List Int), maxList x xs ∈ x :: xs
```

### attempt 1: ok (Lean 1.5 s)

```lean
def maxList : Int → List Int → Int
  | x, [] => x
  | x, y :: ys => maxList (if y ≤ x then x else y) ys

theorem maxList_cons_eq (x z : Int) (zs : List Int) :
    maxList x (z :: zs) = maxList (if z ≤ x then x else z) zs := by
  simp [maxList]

theorem maxList_ge_aux : ∀ (xs : List Int) (x : Int),
    x ≤ maxList x xs ∧ ∀ y ∈ xs, y ≤ maxList x xs := by
  intro xs
  induction xs with
  | nil =>
    intro x
    simp [maxList]
  | cons z zs ih =>
    intro x
    have h := ih (if z ≤ x then x else z)
    rw [maxList_cons_eq]
    by_cases hz : z ≤ x
    · rw [if_pos hz] at h ⊢
      obtain ⟨h1, h2⟩ := h
      refine ⟨h1, ?_⟩
      intro y hy
      rcases List.mem_cons.mp hy with h | h
      · rw [h]; exact Int.le_trans hz h1
      · exact h2 y h
    · have hxz : x ≤ z := by omega
      rw [if_neg hz] at h ⊢
      obtain ⟨h1, h2⟩ := h
      refine ⟨Int.le_trans hxz h1, ?_⟩
      intro y hy
      rcases List.mem_cons.mp hy with h | h
      · rw [h]; exact h1
      · exact h2 y h

theorem maxList_mem_aux : ∀ (xs : List Int) (x : Int),
    maxList x xs = x ∨ maxList x xs ∈ xs := by
  intro xs
  induction xs with
  | nil =>
    intro x
    simp [maxList]
  | cons z zs ih =>
    intro x
    have h := ih (if z ≤ x then x else z)
    rw [maxList_cons_eq]
    by_cases hz : z ≤ x
    · rw [if_pos hz] at h ⊢
      rcases h with h | h
      · exact Or.inl h
      · exact Or.inr (List.mem_cons_of_mem z h)
    · rw [if_neg hz] at h ⊢
      rcases h with h | h
      · right
        rw [h]
        simp
      · exact Or.inr (List.mem_cons_of_mem z h)

theorem maxList_ge : ∀ (x : Int) (xs : List Int), ∀ y ∈ x :: xs, y ≤ maxList x xs := by
  intro x xs y hy
  rcases List.mem_cons.mp hy with h | h
  · rw [h]; exact (maxList_ge_aux xs x).1
  · exact (maxList_ge_aux xs x).2 y h

theorem maxList_mem : ∀ (x : Int) (xs : List Int), maxList x xs ∈ x :: xs := by
  intro x xs
  rcases maxList_mem_aux xs x with h | h
  · rw [h]; simp
  · exact List.mem_cons_of_mem x h
```

## isort

```
    theorem isort_sorted : ∀ xs : List Int, (isort xs).Pairwise (· ≤ ·)
    theorem isort_perm : ∀ xs : List Int, (isort xs).Perm xs
```

### attempt 1: errors (Lean 1.9 s)

```lean
def ins (x : Int) : List Int → List Int
  | [] => [x]
  | y :: ys => if x ≤ y then x :: y :: ys else y :: ins x ys

def isort : List Int → List Int
  | [] => []
  | x :: xs => ins x (isort xs)

theorem ins_perm (x : Int) (l : List Int) : (ins x l).Perm (x :: l) := by
  induction l with
  | nil => simp [ins]
  | cons y ys ih =>
    unfold ins
    split
    · exact List.Perm.refl _
    · exact (List.Perm.cons y ih).trans (List.Perm.swap x y ys)

theorem ins_sorted (x : Int) (l : List Int) (h : l.Pairwise (· ≤ ·)) :
    (ins x l).Pairwise (· ≤ ·) := by
  induction l with
  | nil => simp [ins]
  | cons y ys ih =>
    have h' := List.pairwise_cons.mp h
    obtain ⟨h1, h2⟩ := h'
    unfold ins
    split
    · rename_i hxy
      refine List.pairwise_cons.mpr ⟨?_, h⟩
      intro b hb
      rcases List.mem_cons.mp hb with hb | hb
      · omega
      · rcases List.mem_cons.mp hb with hb | hb
        · omega
        · exact Int.le_trans hxy (h1 b hb)
    · rename_i hxy
      refine List.pairwise_cons.mpr ⟨?_, ih h2⟩
      intro b hb
      have hm := (ins_perm x ys).mem_iff.mp hb
      rcases List.mem_cons.mp hm with hb' | hb'
      · omega
      · exact h1 b hb'

theorem isort_sorted : ∀ xs : List Int, (isort xs).Pairwise (· ≤ ·) := by
  intro xs
  induction xs with
  | nil => simp [isort]
  | cons x xs ih =>
    unfold isort
    exact ins_sorted x _ ih

theorem isort_perm : ∀ xs : List Int, (isort xs).Perm xs := by
  intro xs
  induction xs with
  | nil => simp [isort]
  | cons x xs ih =>
    unfold isort
    exact (ins_perm x _).trans (List.Perm.cons x ih)
```

Sent back:
```
line 32:32: error: Application type mismatch: The argument
  hb
has type
  b ∈ ys
but is expected to have type
  ?m.100 ∈ ?m.98 :: ?m.99
in the application
  List.mem_cons.mp hb
`isort_sorted` depends on ['sorryAx'] (sorry, an axiom or native_decide)
```

### attempt 2: ok (Lean 2.0 s)

```lean
def ins (x : Int) : List Int → List Int
  | [] => [x]
  | y :: ys => if x ≤ y then x :: y :: ys else y :: ins x ys

def isort : List Int → List Int
  | [] => []
  | x :: xs => ins x (isort xs)

theorem ins_perm (x : Int) (l : List Int) : (ins x l).Perm (x :: l) := by
  induction l with
  | nil => simp [ins]
  | cons y ys ih =>
    unfold ins
    split
    · exact List.Perm.refl _
    · exact (List.Perm.cons y ih).trans (List.Perm.swap x y ys)

theorem ins_sorted (x : Int) (l : List Int) (h : l.Pairwise (· ≤ ·)) :
    (ins x l).Pairwise (· ≤ ·) := by
  induction l with
  | nil => simp [ins]
  | cons y ys ih =>
    have h' := List.pairwise_cons.mp h
    obtain ⟨h1, h2⟩ := h'
    unfold ins
    split
    · rename_i hxy
      refine List.pairwise_cons.mpr ⟨?_, h⟩
      intro b hb
      rcases List.mem_cons.mp hb with hb | hb
      · omega
      · exact Int.le_trans hxy (h1 b hb)
    · rename_i hxy
      refine List.pairwise_cons.mpr ⟨?_, ih h2⟩
      intro b hb
      have hm := (ins_perm x ys).mem_iff.mp hb
      rcases List.mem_cons.mp hm with hb' | hb'
      · omega
      · exact h1 b hb'

theorem isort_sorted : ∀ xs : List Int, (isort xs).Pairwise (· ≤ ·) := by
  intro xs
  induction xs with
  | nil => simp [isort]
  | cons x xs ih =>
    unfold isort
    exact ins_sorted x _ ih

theorem isort_perm : ∀ xs : List Int, (isort xs).Perm xs := by
  intro xs
  induction xs with
  | nil => simp [isort]
  | cons x xs ih =>
    unfold isort
    exact (ins_perm x _).trans (List.Perm.cons x ih)
```

## tax

```
    theorem tax_mono : ∀ a b : Nat, a ≤ b → tax a ≤ tax b
```

### attempt 1: ok (Lean 5.7 s)

```lean
def tax (income : Nat) : Nat :=
  ((min income 40000 - min income 10000) / 10
    + (min income 100000 - min income 40000) * 25 / 100
    + (income - min income 100000) * 40 / 100) - 500

theorem tax_mono : ∀ a b : Nat, a ≤ b → tax a ≤ tax b := by
  intro a b h
  unfold tax
  omega
```

## parking

```
    theorem parkingFee_le : ∀ m : Nat, parkingFee m ≤ 20 * (m / 1440 + 1)
    theorem parkingFee_mono : ∀ a b : Nat, a ≤ b → parkingFee a ≤ parkingFee b
```

### attempt 1: ok (Lean 3.5 s)

```lean
def dayFee (r : Nat) : Nat :=
  if r ≤ 15 then 0 else min 20 (3 * ((r + 59) / 60))

def parkingFee (minutes : Nat) : Nat :=
  20 * (minutes / 1440) + dayFee (minutes % 1440)

theorem dayFee_le (r : Nat) : dayFee r ≤ 20 := by
  unfold dayFee
  split <;> omega

theorem dayFee_mono (a b : Nat) (h : a ≤ b) : dayFee a ≤ dayFee b := by
  unfold dayFee
  split <;> split <;> omega

theorem parkingFee_le : ∀ m : Nat, parkingFee m ≤ 20 * (m / 1440 + 1) := by
  intro m
  have h := dayFee_le (m % 1440)
  unfold parkingFee
  omega

theorem parkingFee_mono : ∀ a b : Nat, a ≤ b → parkingFee a ≤ parkingFee b := by
  intro a b hab
  have h1 := dayFee_le (a % 1440)
  have h2 := dayFee_le (b % 1440)
  unfold parkingFee
  rcases Nat.lt_or_ge (a / 1440) (b / 1440) with h | h
  · omega
  · have hq : a / 1440 = b / 1440 := by omega
    have hr : a % 1440 ≤ b % 1440 := by omega
    have h3 := dayFee_mono _ _ hr
    omega
```
