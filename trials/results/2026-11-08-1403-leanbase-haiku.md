# Lean-direct baseline 2026-11-08-1403 (haiku)

| task | result | lines | Lean s per attempt |
|---|---|---|---|
| sum | first try | 12 | [5.6] |
| isqrt | first try | 49 | [5.7] |
| max | after 1 fix | 50 | [4.3, 4.0] |
| isort | first try | 53 | [5.8] |
| tax | first try | 8 | [10.5] |
| parking | fail | 26 | [5.8, 5.4, 5.1] |

## sum

```
    theorem sumTo_spec : ∀ n : Nat, 2 * sumTo n = n * (n + 1)
```

### attempt 1: ok (Lean 5.6 s)

```lean
def sumTo : Nat → Nat
  | 0 => 0
  | n + 1 => sumTo n + (n + 1)

theorem sumTo_spec : ∀ n : Nat, 2 * sumTo n = n * (n + 1) := by
  intro n
  induction n with
  | zero => rfl
  | succ k ih =>
    show 2 * (sumTo k + (k + 1)) = (k + 1) * (k + 1 + 1)
    rw [Nat.mul_add, ih]
    simp only [Nat.mul_add, Nat.add_mul, Nat.mul_one, Nat.one_mul]
    omega
```

## isqrt

```
    theorem isqrt_spec : ∀ n : Nat, isqrt n * isqrt n ≤ n ∧ n < (isqrt n + 1) * (isqrt n + 1)
```

### attempt 1: ok (Lean 5.7 s)

```lean
def sqrtBest (n : Nat) : Nat → Nat
  | 0 => 0
  | m + 1 => if (m + 1) * (m + 1) ≤ n then m + 1 else sqrtBest n m

def isqrt (n : Nat) : Nat := sqrtBest n n

theorem sqrtBest_le (n : Nat) : ∀ m, sqrtBest n m ≤ m := by
  intro m
  induction m with
  | zero => simp [sqrtBest]
  | succ k ih =>
    simp only [sqrtBest]
    split <;> omega

theorem sqrtBest_sound (n : Nat) : ∀ m, sqrtBest n m * sqrtBest n m ≤ n := by
  intro m
  induction m with
  | zero => simp [sqrtBest]
  | succ k ih =>
    simp only [sqrtBest]
    split
    · assumption
    · exact ih

theorem sqrtBest_max (n : Nat) : ∀ m r, r ≤ m → r * r ≤ n → r ≤ sqrtBest n m := by
  intro m
  induction m with
  | zero =>
    intro r hr _
    have h0 : r = 0 := by omega
    subst h0
    simp [sqrtBest]
  | succ k ih =>
    intro r hr hrr
    simp only [sqrtBest]
    split
    · exact hr
    · by_cases hk : r ≤ k
      · exact ih r hk hrr
      · have h1 : r = k + 1 := by omega
        subst h1
        exact absurd hrr (by assumption)

theorem isqrt_spec : ∀ n : Nat, isqrt n * isqrt n ≤ n ∧ n < (isqrt n + 1) * (isqrt n + 1) := by
  intro n
  unfold isqrt
  refine ⟨sqrtBest_sound n n, ?_⟩
  by_cases h : sqrtBest n n + 1 ≤ n
  · have hmax : ¬ (sqrtBest n n + 1) * (sqrtBest n n + 1) ≤ n := by
      intro hh
      have := sqrtBest_max n n (sqrtBest n n + 1) h hh
      omega
    exact Nat.not_le.mp hmax
  · exact Nat.lt_of_lt_of_le (by omega) (Nat.le_mul_self _)
```

## max

```
    theorem maxList_ge : ∀ (x : Int) (xs : List Int), ∀ y ∈ x :: xs, y ≤ maxList x xs
    theorem maxList_mem : ∀ (x : Int) (xs : List Int), maxList x xs ∈ x :: xs
```

### attempt 1: errors (Lean 4.3 s)

```lean
def maxList (x : Int) (xs : List Int) : Int := xs.foldl max x

theorem foldl_max_ge_aux (xs : List Int) :
    ∀ (a y : Int), (y ≤ a ∨ y ∈ xs) → y ≤ xs.foldl max a := by
  induction xs with
  | nil =>
    intro a y h
    rcases h with h | h
    · simpa using h
    · simp at h
  | cons z zs ih =>
    intro a y h
    simp only [List.foldl_cons]
    apply ih
    have h1 : a ≤ max a z ∧ z ≤ max a z := by
      by_cases hc : a ≤ z <;> simp [Int.max_def, hc] <;> omega
    rcases h with h | h | h
    · left
      exact Int.le_trans h h1.1
    · left
      rw [h]
      exact h1.2
    · right
      exact h

theorem foldl_max_mem_aux (xs : List Int) :
    ∀ a : Int, xs.foldl max a ∈ a :: xs := by
  induction xs with
  | nil =>
    intro a
    simp
  | cons z zs ih =>
    intro a
    simp only [List.foldl_cons]
    have h := ih (max a z)
    have hm : max a z = a ∨ max a z = z := by
      by_cases hc : a ≤ z <;> simp [Int.max_def, hc]
    rcases List.mem_cons.mp h with h1 | h1
    · rcases hm with hm | hm
      · exact List.mem_cons.mpr (Or.inl (h1.trans hm))
      · exact List.mem_cons.mpr (Or.inr (List.mem_cons.mpr (Or.inl (h1.trans hm))))
    · exact List.mem_cons.mpr (Or.inr (List.mem_cons.mpr (Or.inr h1)))

theorem maxList_ge : ∀ (x : Int) (xs : List Int), ∀ y ∈ x :: xs, y ≤ maxList x xs := by
  intro x xs y hy
  unfold maxList
  apply foldl_max_ge_aux
  rcases List.mem_cons.mp hy with h | h
  · left
    omega
  · right
    exact h

theorem maxList_mem : ∀ (x : Int) (xs : List Int), maxList x xs ∈ x :: xs := by
  intro x xs
  unfold maxList
  exact foldl_max_mem_aux xs x
```

Sent back:
```
line 21:10: error: Unknown identifier `h`
line 24:12: error: Unknown identifier `h`
`maxList_ge` depends on ['sorryAx'] (sorry, an axiom or native_decide)
```

### attempt 2: ok (Lean 4.0 s)

```lean
def maxList (x : Int) (xs : List Int) : Int := xs.foldl max x

theorem foldl_max_ge_aux (xs : List Int) :
    ∀ (a y : Int), (y ≤ a ∨ y ∈ xs) → y ≤ xs.foldl max a := by
  induction xs with
  | nil =>
    intro a y h
    rcases h with h | h
    · simpa using h
    · simp at h
  | cons z zs ih =>
    intro a y h
    simp only [List.foldl_cons]
    apply ih
    rcases h with h | h
    · left
      omega
    · rcases List.mem_cons.mp h with h' | h'
      · left
        omega
      · right
        exact h'

theorem foldl_max_mem_aux (xs : List Int) :
    ∀ a : Int, xs.foldl max a ∈ a :: xs := by
  induction xs with
  | nil =>
    intro a
    simp
  | cons z zs ih =>
    intro a
    simp only [List.foldl_cons]
    have h := ih (max a z)
    rcases List.mem_cons.mp h with h1 | h1
    · rw [h1]
      have hm : max a z = a ∨ max a z = z := by
        by_cases hc : a ≤ z <;> simp [Int.max_def, hc]
      rcases hm with hm | hm <;> rw [hm] <;> simp
    · exact List.mem_cons.mpr (Or.inr (List.mem_cons.mpr (Or.inr h1)))

theorem maxList_ge : ∀ (x : Int) (xs : List Int), ∀ y ∈ x :: xs, y ≤ maxList x xs := by
  intro x xs y hy
  unfold maxList
  apply foldl_max_ge_aux
  rcases List.mem_cons.mp hy with h | h
  · left
    omega
  · right
    exact h

theorem maxList_mem : ∀ (x : Int) (xs : List Int), maxList x xs ∈ x :: xs := by
  intro x xs
  unfold maxList
  exact foldl_max_mem_aux xs x
```

## isort

```
    theorem isort_sorted : ∀ xs : List Int, (isort xs).Pairwise (· ≤ ·)
    theorem isort_perm : ∀ xs : List Int, (isort xs).Perm xs
```

### attempt 1: ok (Lean 5.8 s)

```lean
def isortInsert (x : Int) : List Int → List Int
  | [] => [x]
  | y :: ys => if x ≤ y then x :: y :: ys else y :: isortInsert x ys

def isort : List Int → List Int
  | [] => []
  | x :: xs => isortInsert x (isort xs)

theorem isortInsert_perm (x : Int) (l : List Int) :
    (isortInsert x l).Perm (x :: l) := by
  induction l with
  | nil => exact List.Perm.refl _
  | cons y ys ih =>
    simp only [isortInsert]
    split
    · exact List.Perm.refl _
    · exact (ih.cons y).trans (List.Perm.swap x y ys)

theorem isortInsert_sorted (x : Int) (l : List Int) (h : l.Pairwise (· ≤ ·)) :
    (isortInsert x l).Pairwise (· ≤ ·) := by
  induction l with
  | nil => simp [isortInsert]
  | cons y ys ih =>
    obtain ⟨hy, hys⟩ := List.pairwise_cons.mp h
    simp only [isortInsert]
    split
    · rename_i hxy
      apply List.pairwise_cons.mpr
      constructor
      · intro a ha
        rcases List.mem_cons.mp ha with h1 | h1
        · rw [h1]; exact hxy
        · exact Int.le_trans hxy (hy a h1)
      · exact h
    · rename_i hxy
      apply List.pairwise_cons.mpr
      constructor
      · intro a ha
        rcases List.mem_cons.mp ((isortInsert_perm x ys).mem_iff.mp ha) with h1 | h1
        · rw [h1]; exact Int.le_of_lt (Int.not_le.mp hxy)
        · exact hy a h1
      · exact ih hys

theorem isort_sorted : ∀ xs : List Int, (isort xs).Pairwise (· ≤ ·) := by
  intro xs
  induction xs with
  | nil => simp [isort]
  | cons x xs ih =>
    simp only [isort]
    exact isortInsert_sorted x (isort xs) ih

theorem isort_perm : ∀ xs : List Int, (isort xs).Perm xs := by
  intro xs
  induction xs with
  | nil => exact List.Perm.refl _
  | cons x xs ih =>
    simp only [isort]
    exact (isortInsert_perm x (isort xs)).trans (ih.cons x)
```

## tax

```
    theorem tax_mono : ∀ a b : Nat, a ≤ b → tax a ≤ tax b
```

### attempt 1: ok (Lean 10.5 s)

```lean
def tax (income : Nat) : Nat :=
  ((min income 40000 - 10000) * 10 / 100
    + (min income 100000 - 40000) * 25 / 100
    + (income - 100000) * 40 / 100) - 500

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

### attempt 1: errors (Lean 5.8 s)

```lean
def partialFee (t : Nat) : Nat :=
  if t ≤ 15 then 0 else min 20 (3 * ((t + 59) / 60))

def parkingFee (minutes : Nat) : Nat :=
  20 * (minutes / 1440) + partialFee (minutes % 1440)

theorem partialFee_le (t : Nat) : partialFee t ≤ 20 := by
  unfold partialFee
  simp only [Nat.min_def]
  split_ifs <;> omega

theorem partialFee_mono (s t : Nat) (h : s ≤ t) : partialFee s ≤ partialFee t := by
  unfold partialFee
  have h1 : (s + 59) / 60 ≤ (t + 59) / 60 := by omega
  simp only [Nat.min_def]
  split_ifs <;> omega

theorem parkingFee_le : ∀ m : Nat, parkingFee m ≤ 20 * (m / 1440 + 1) := by
  intro m
  have h := partialFee_le (m % 1440)
  unfold parkingFee
  omega

theorem parkingFee_mono : ∀ a b : Nat, a ≤ b → parkingFee a ≤ parkingFee b := by
  intro a b hab
  unfold parkingFee
  by_cases hq : a / 1440 = b / 1440
  · have hr : a % 1440 ≤ b % 1440 := by omega
    have := partialFee_mono (a % 1440) (b % 1440) hr
    omega
  · have hlt : a / 1440 < b / 1440 := by omega
    have h1 := partialFee_le (a % 1440)
    omega
```

Sent back:
```
line 10:3: error: unknown tactic
line 7:55: error: unsolved goals
t : Nat
⊢ (if t ≤ 15 then 0 else if 20 ≤ 3 * ((t + 59) / 60) then 20 else 3 * ((t + 59) / 60)) ≤ 20
line 16:3: error: unknown tactic
line 12:81: error: unsolved goals
s t : Nat
h : s ≤ t
h1 : (s + 59) / 60 ≤ (t + 59) / 60
⊢ (if s ≤ 15 then 0 else if 20 ≤ 3 * ((s + 59) / 60) then 20 else 3 * ((s + 59) / 60)) ≤
    if t ≤ 15 then 0 else if 20 ≤ 3 * ((t + 59) / 60) then 20 else 3 * ((t + 59) / 60)
`parkingFee_le` depends on ['sorryAx'] (sorry, an axiom or native_decide)
`parkingFee_mono` depends on ['sorryAx'] (sorry, an axiom or native_decide)
```

### attempt 2: errors (Lean 5.4 s)

```lean
def partialFee (t : Nat) : Nat :=
  if t ≤ 15 then 0 else if 20 ≤ 3 * ((t + 59) / 60) then 20 else 3 * ((t + 59) / 60)

def parkingFee (minutes : Nat) : Nat :=
  20 * (minutes / 1440) + partialFee (minutes % 1440)

theorem partialFee_le (t : Nat) : partialFee t ≤ 20 := by
  unfold partialFee
  repeat' split <;> omega

theorem partialFee_mono (s t : Nat) (h : s ≤ t) : partialFee s ≤ partialFee t := by
  have h1 : (s + 59) / 60 ≤ (t + 59) / 60 := by omega
  unfold partialFee
  repeat' split <;> omega

theorem parkingFee_le : ∀ m : Nat, parkingFee m ≤ 20 * (m / 1440 + 1) := by
  intro m
  have h := partialFee_le (m % 1440)
  unfold parkingFee
  omega

theorem parkingFee_mono : ∀ a b : Nat, a ≤ b → parkingFee a ≤ parkingFee b := by
  intro a b hab
  unfold parkingFee
  by_cases hq : a / 1440 = b / 1440
  · have hr : a % 1440 ≤ b % 1440 := by omega
    have := partialFee_mono (a % 1440) (b % 1440) hr
    omega
  · have hlt : a / 1440 < b / 1440 := by omega
    have h1 := partialFee_le (a % 1440)
    omega
```

Sent back:
```
line 7:55: error: unsolved goals
t : Nat
⊢ (if t ≤ 15 then 0 else if 20 ≤ 3 * ((t + 59) / 60) then 20 else 3 * ((t + 59) / 60)) ≤ 20
line 11:81: error: unsolved goals
s t : Nat
h : s ≤ t
h1 : (s + 59) / 60 ≤ (t + 59) / 60
⊢ (if s ≤ 15 then 0 else if 20 ≤ 3 * ((s + 59) / 60) then 20 else 3 * ((s + 59) / 60)) ≤
    if t ≤ 15 then 0 else if 20 ≤ 3 * ((t + 59) / 60) then 20 else 3 * ((t + 59) / 60)
`parkingFee_le` depends on ['sorryAx'] (sorry, an axiom or native_decide)
`parkingFee_mono` depends on ['sorryAx'] (sorry, an axiom or native_decide)
```

### attempt 3: errors (Lean 5.1 s)

```lean
def partialFee (t : Nat) : Nat :=
  if t ≤ 15 then 0 else if 20 ≤ 3 * ((t + 59) / 60) then 20 else 3 * ((t + 59) / 60)

def parkingFee (minutes : Nat) : Nat :=
  20 * (minutes / 1440) + partialFee (minutes % 1440)

theorem partialFee_le (t : Nat) : partialFee t ≤ 20 := by
  unfold partialFee
  split_ifs <;> omega

theorem partialFee_mono (s t : Nat) (h : s ≤ t) : partialFee s ≤ partialFee t := by
  have h1 : (s + 59) / 60 ≤ (t + 59) / 60 := by omega
  unfold partialFee
  split_ifs <;> omega

theorem parkingFee_le : ∀ m : Nat, parkingFee m ≤ 20 * (m / 1440 + 1) := by
  intro m
  have h := partialFee_le (m % 1440)
  unfold parkingFee
  omega

theorem parkingFee_mono : ∀ a b : Nat, a ≤ b → parkingFee a ≤ parkingFee b := by
  intro a b hab
  unfold parkingFee
  by_cases hq : a / 1440 = b / 1440
  · have hr : a % 1440 ≤ b % 1440 := by omega
    have := partialFee_mono (a % 1440) (b % 1440) hr
    omega
  · have hlt : a / 1440 < b / 1440 := by omega
    have h1 := partialFee_le (a % 1440)
    omega
```

Sent back:
```
line 9:3: error: unknown tactic
line 7:55: error: unsolved goals
t : Nat
⊢ (if t ≤ 15 then 0 else if 20 ≤ 3 * ((t + 59) / 60) then 20 else 3 * ((t + 59) / 60)) ≤ 20
line 14:3: error: unknown tactic
line 11:81: error: unsolved goals
s t : Nat
h : s ≤ t
h1 : (s + 59) / 60 ≤ (t + 59) / 60
⊢ (if s ≤ 15 then 0 else if 20 ≤ 3 * ((s + 59) / 60) then 20 else 3 * ((s + 59) / 60)) ≤
    if t ≤ 15 then 0 else if 20 ≤ 3 * ((t + 59) / 60) then 20 else 3 * ((t + 59) / 60)
`parkingFee_le` depends on ['sorryAx'] (sorry, an axiom or native_decide)
`parkingFee_mono` depends on ['sorryAx'] (sorry, an axiom or native_decide)
```
