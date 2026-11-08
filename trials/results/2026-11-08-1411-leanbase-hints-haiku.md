# Lean-direct baseline 2026-11-08-1411 (haiku)

| task | result | lines | Lean s per attempt |
|---|---|---|---|
| sum | first try | 11 | [5.9] |
| isqrt | after 1 fix | 54 | [5.5, 6.2] |
| max | after 1 fix | 44 | [5.2, 6.2] |
| isort | first try | 43 | [5.8] |
| tax | after 2 fixes | 20 | [3.0, 7.0, 5.5] |
| parking | first try | 28 | [3.8] |

## sum

```
    theorem sumTo_spec : ∀ n : Nat, 2 * sumTo n = n * (n + 1)
```

### attempt 1: ok (Lean 5.9 s)

```lean
def sumTo : Nat → Nat
  | 0 => 0
  | n + 1 => sumTo n + (n + 1)

theorem sumTo_spec : ∀ n : Nat, 2 * sumTo n = n * (n + 1) := by
  intro n
  induction n with
  | zero => simp [sumTo]
  | succ k ih =>
    simp only [sumTo]
    rw [Nat.mul_add, ih]
    grind
```

## isqrt

```
    theorem isqrt_spec : ∀ n : Nat, isqrt n * isqrt n ≤ n ∧ n < (isqrt n + 1) * (isqrt n + 1)
```

### attempt 1: errors (Lean 5.5 s)

```lean
def isqrtAux (n : Nat) : Nat → Nat
  | 0 => 0
  | k+1 => if (k+1)*(k+1) ≤ n then k+1 else isqrtAux n k

def isqrt (n : Nat) : Nat := isqrtAux n n

theorem isqrtAux_spec (n : Nat) : ∀ m : Nat,
    isqrtAux n m ≤ m ∧ isqrtAux n m * isqrtAux n m ≤ n ∧
    ∀ s, s ≤ m → s * s ≤ n → s ≤ isqrtAux n m := by
  intro m
  induction m with
  | zero =>
    refine ⟨?_, ?_, ?_⟩
    · simp only [isqrtAux]; omega
    · simp only [isqrtAux]; omega
    · intro s hs _
      simp only [isqrtAux]
      omega
  | succ k ih =>
    obtain ⟨h1, h2, h3⟩ := ih
    by_cases hc : (k+1)*(k+1) ≤ n
    · have e : isqrtAux n (k+1) = k+1 := by
        rw [isqrtAux, if_pos hc]
      rw [e]
      exact ⟨Nat.le_refl _, hc, fun s hs _ => hs⟩
    · have e : isqrtAux n (k+1) = isqrtAux n k := by
        rw [isqrtAux, if_neg hc]
      rw [e]
      refine ⟨by omega, h2, ?_⟩
      intro s hs hss
      have hsk : s ≤ k := by
        by_contra hlt
        have hs' : s = k+1 := by omega
        subst hs'
        exact hc hss
      exact h3 s hsk hss

theorem isqrt_spec : ∀ n : Nat, isqrt n * isqrt n ≤ n ∧ n < (isqrt n + 1) * (isqrt n + 1) := by
  intro n
  unfold isqrt
  obtain ⟨h1, h2, h3⟩ := isqrtAux_spec n n
  refine ⟨h2, ?_⟩
  by_contra hne
  have hle := Nat.le_of_not_lt hne
  have hl : 1 * (isqrtAux n n + 1) ≤ (isqrtAux n n + 1) * (isqrtAux n n + 1) :=
    Nat.mul_le_mul_right (isqrtAux n n + 1) (by omega)
  have key := h3 (isqrtAux n n + 1) (by omega) hle
  omega
```

Sent back:
```
line 32:9: error: unknown tactic
line 31:26: error: unsolved goals
n k : Nat
h1 : isqrtAux n k ≤ k
h2 : isqrtAux n k * isqrtAux n k ≤ n
h3 : ∀ (s : Nat), s ≤ k → s * s ≤ n → s ≤ isqrtAux n k
hc : ¬(k + 1) * (k + 1) ≤ n
e : isqrtAux n (k + 1) = isqrtAux n k
s : Nat
hs : s ≤ k + 1
hss : s * s ≤ n
⊢ s ≤ k
line 26:4: error: unsolved goals
case neg
n k : Nat
h1 : isqrtAux n k ≤ k
h2 : isqrtAux n k * isqrtAux n k ≤ n
h3 : ∀ (s : Nat), s ≤ k → s * s ≤ n → s ≤ isqrtAux n k
hc : ¬(k + 1) * (k + 1) ≤ n
e : isqrtAux n (k + 1) = isqrtAux n k
s : Nat
hs : s ≤ k + 1
hss : s * s ≤ n
hsk : s ≤ k
⊢ s ≤ isqrtAux n k
line 43:3: error: unknown tactic
line 38:93: error: unsolved goals
n : Nat
h1 : isqrtAux n n ≤ n
h2 : isqrtAux n n * isqrtAux n n ≤ n
h3 : ∀ (s : Nat), s ≤ n → s * s ≤ n → s ≤ isqrtAux n n
⊢ n < (isqrtAux n n + 1) * (isqrtAux n n + 1)
`isqrt_spec` depends on ['sorryAx'] (sorry, an axiom or native_decide)
```

### attempt 2: ok (Lean 6.2 s)

```lean
def isqrtAux (n : Nat) : Nat → Nat
  | 0 => 0
  | k+1 => if (k+1)*(k+1) ≤ n then k+1 else isqrtAux n k

def isqrt (n : Nat) : Nat := isqrtAux n n

theorem isqrtAux_spec (n : Nat) : ∀ m : Nat,
    isqrtAux n m ≤ m ∧ isqrtAux n m * isqrtAux n m ≤ n ∧
    ∀ s, s ≤ m → s * s ≤ n → s ≤ isqrtAux n m := by
  intro m
  induction m with
  | zero =>
    have e0 : isqrtAux n 0 = 0 := rfl
    rw [e0]
    refine ⟨Nat.le_refl _, by simp, ?_⟩
    intro s hs _
    omega
  | succ k ih =>
    obtain ⟨h1, h2, h3⟩ := ih
    by_cases hc : (k+1)*(k+1) ≤ n
    · have e : isqrtAux n (k+1) = k+1 := by
        rw [isqrtAux, if_pos hc]
      rw [e]
      exact ⟨Nat.le_refl _, hc, fun s hs _ => hs⟩
    · have e : isqrtAux n (k+1) = isqrtAux n k := by
        rw [isqrtAux, if_neg hc]
      rw [e]
      refine ⟨by omega, h2, ?_⟩
      intro s hs hss
      have hsk : s ≤ k := by
        by_cases hsk' : s ≤ k
        · exact hsk'
        · have hs' : s = k+1 := by omega
          subst hs'
          exact absurd hss hc
      exact h3 s hsk hss

theorem le_self_mul_self' : ∀ x : Nat, x ≤ x * x := by
  intro x
  rcases Nat.eq_zero_or_pos x with h | h
  · subst h
    simp
  · have := Nat.mul_le_mul_right x (by omega : 1 ≤ x)
    omega

theorem isqrt_spec : ∀ n : Nat, isqrt n * isqrt n ≤ n ∧ n < (isqrt n + 1) * (isqrt n + 1) := by
  intro n
  unfold isqrt
  obtain ⟨h1, h2, h3⟩ := isqrtAux_spec n n
  refine ⟨h2, ?_⟩
  by_cases hlt : n < (isqrtAux n n + 1) * (isqrtAux n n + 1)
  · exact hlt
  · have hle : (isqrtAux n n + 1) * (isqrtAux n n + 1) ≤ n := by omega
    have hn : isqrtAux n n + 1 ≤ n := by
      have := le_self_mul_self' (isqrtAux n n + 1)
      omega
    have key := h3 (isqrtAux n n + 1) hn hle
    omega
```

## max

```
    theorem maxList_ge : ∀ (x : Int) (xs : List Int), ∀ y ∈ x :: xs, y ≤ maxList x xs
    theorem maxList_mem : ∀ (x : Int) (xs : List Int), maxList x xs ∈ x :: xs
```

### attempt 1: errors (Lean 5.2 s)

```lean
def maxList (x : Int) (xs : List Int) : Int :=
  match xs with
  | [] => x
  | y :: ys => maxList (max x y) ys

theorem maxList_ge : ∀ (x : Int) (xs : List Int), ∀ y ∈ x :: xs, y ≤ maxList x xs := by
  intro x xs
  induction xs generalizing x with
  | nil =>
    intro y hy
    simp at hy
    rw [hy]
    simp [maxList]
  | cons z zs ih =>
    intro y hy
    simp only [maxList]
    rcases List.mem_cons.mp hy with h | h
    · have hm : y ≤ max x z := by
        rw [h]
        simp
      exact le_trans hm (ih (max x z) (max x z) (by simp))
    · rcases List.mem_cons.mp h with h' | h'
      · have hm : y ≤ max x z := by
          rw [h']
          simp
        exact le_trans hm (ih (max x z) (max x z) (by simp))
      · exact ih (max x z) y (List.mem_cons_of_mem _ h')

theorem maxList_mem : ∀ (x : Int) (xs : List Int), maxList x xs ∈ x :: xs := by
  intro x xs
  induction xs generalizing x with
  | nil =>
    simp [maxList]
  | cons y ys ih =>
    simp only [maxList]
    have h := ih (max x y)
    rcases List.mem_cons.mp h with h1 | h1
    · rw [h1]
      simp only [max_def]
      split <;> simp
    · simp [h1]
```

Sent back:
```
line 20:8: error: `simp` made no progress
line 21:12: error: Unknown identifier `le_trans`
line 25:10: error: `simp` made no progress
line 26:14: error: Unknown identifier `le_trans`
line 39:17: error: Unknown identifier `max_def`
line 39:6: error: `simp` made no progress
`maxList_ge` depends on ['sorryAx'] (sorry, an axiom or native_decide)
`maxList_mem` depends on ['sorryAx'] (sorry, an axiom or native_decide)
```

### attempt 2: ok (Lean 6.2 s)

```lean
def maxList (x : Int) (xs : List Int) : Int :=
  match xs with
  | [] => x
  | y :: ys => maxList (max x y) ys

theorem maxList_aux : ∀ (xs : List Int) (x y : Int), (y = x ∨ y ∈ xs) → y ≤ maxList x xs := by
  intro xs
  induction xs with
  | nil =>
    intro x y h
    rcases h with h | h
    · subst h
      simp [maxList]
    · simp at h
  | cons z zs ih =>
    intro x y h
    show y ≤ maxList (max x z) zs
    have key : max x z ≤ maxList (max x z) zs := ih (max x z) (max x z) (Or.inl rfl)
    rcases h with h | h
    · have : y ≤ max x z := by omega
      omega
    · rcases List.mem_cons.mp h with h' | h'
      · have : y ≤ max x z := by omega
        omega
      · exact ih (max x z) y (Or.inr h')

theorem maxList_ge : ∀ (x : Int) (xs : List Int), ∀ y ∈ x :: xs, y ≤ maxList x xs := by
  intro x xs y hy
  exact maxList_aux xs x y (List.mem_cons.mp hy)

theorem maxList_mem : ∀ (x : Int) (xs : List Int), maxList x xs ∈ x :: xs := by
  intro x xs
  induction xs generalizing x with
  | nil =>
    simp [maxList]
  | cons z zs ih =>
    show maxList (max x z) zs ∈ x :: z :: zs
    have h := ih (max x z)
    rcases List.mem_cons.mp h with h1 | h1
    · rw [h1]
      have hc : max x z = x ∨ max x z = z := by omega
      rcases hc with h2 | h2
      · rw [h2]
        simp
      · rw [h2]
        simp
    · exact List.mem_cons_of_mem x (List.mem_cons_of_mem z h1)
```

## isort

```
    theorem isort_sorted : ∀ xs : List Int, (isort xs).Pairwise (· ≤ ·)
    theorem isort_perm : ∀ xs : List Int, (isort xs).Perm xs
```

### attempt 1: ok (Lean 5.8 s)

```lean
def ins (x : Int) : List Int → List Int
  | [] => [x]
  | y :: ys => if x ≤ y then x :: y :: ys else y :: ins x ys

def isort : List Int → List Int
  | [] => []
  | x :: xs => ins x (isort xs)

theorem ins_of_le {x y : Int} {ys : List Int} (h : x ≤ y) :
    ins x (y :: ys) = x :: y :: ys := by
  simp [ins, h]

theorem ins_of_not_le {x y : Int} {ys : List Int} (h : ¬ x ≤ y) :
    ins x (y :: ys) = y :: ins x ys := by
  simp [ins, h]

theorem ins_perm (x : Int) : ∀ l : List Int, (ins x l).Perm (x :: l)
  | [] => List.Perm.refl _
  | y :: ys => by
    by_cases hxy : x ≤ y
    · rw [ins_of_le hxy] <;> exact List.Perm.refl _
    · rw [ins_of_not_le hxy]
      exact (List.Perm.cons y (ins_perm x ys)).trans (List.Perm.swap x y ys)

theorem ins_pairwise (x : Int) : ∀ l : List Int, l.Pairwise (· ≤ ·) → (ins x l).Pairwise (· ≤ ·)
  | [], _ => List.Pairwise.cons (fun _ h => by simp at h) List.Pairwise.nil
  | y :: ys, h => by
    obtain ⟨hy, hys⟩ := List.pairwise_cons.mp h
    by_cases hxy : x ≤ y
    · rw [ins_of_le hxy]
      refine List.pairwise_cons.mpr ⟨?_, h⟩
      intro a ha
      rcases List.mem_cons.mp ha with rfl | ha'
      · exact hxy
      · exact Int.le_trans hxy (hy a ha')
    · rw [ins_of_not_le hxy]
      refine List.pairwise_cons.mpr ⟨?_, ins_pairwise x ys hys⟩
      intro a ha
      have hmem : a ∈ x :: ys := (ins_perm x ys).mem_iff.mp ha
      rcases List.mem_cons.mp hmem with rfl | ha'
      · omega
      · exact hy a ha'

theorem isort_sorted : ∀ xs : List Int, (isort xs).Pairwise (· ≤ ·)
  | [] => List.Pairwise.nil
  | x :: xs => ins_pairwise x (isort xs) (isort_sorted xs)

theorem isort_perm : ∀ xs : List Int, (isort xs).Perm xs
  | [] => List.Perm.refl _
  | x :: xs => (ins_perm x (isort xs)).trans (List.Perm.cons x (isort_perm xs))
```

## tax

```
    theorem tax_mono : ∀ a b : Nat, a ≤ b → tax a ≤ tax b
```

### attempt 1: errors (Lean 3.0 s)

```lean
def tax (income : Nat) : Nat :=
  let b2 := (min income 40000 - 10000) * 10 / 100
  let b3 := (min income 100000 - 40000) * 25 / 100
  let b4 := (income - 100000) * 40 / 100
  (b2 + b3 + b4) - 500

theorem tax_mono : ∀ a b : Nat, a ≤ b → tax a ≤ tax b := by
  intro a b h
  simp only [tax]
  omega
```

Sent back:
```
line 7:57: error: maximum recursion depth has been reached
use `set_option maxRecDepth <num>` to increase limit
use `set_option diagnostics true` to get diagnostic information
`tax_mono` depends on ['sorryAx'] (sorry, an axiom or native_decide)
```

### attempt 2: errors (Lean 7.0 s)

```lean
def tax (income : Nat) : Nat :=
  ((min income 40000 - 10000) * 10 / 100
    + (min income 100000 - 40000) * 25 / 100
    + (income - 100000) * 40 / 100) - 500

set_option maxRecDepth 10000 in
theorem tax_mono : ∀ a b : Nat, a ≤ b → tax a ≤ tax b := by
  intro a b h
  unfold tax
  have h2 : (min a 40000 - 10000) * 10 / 100 ≤ (min b 40000 - 10000) * 10 / 100 := by
    omega
  have h3 : (min a 100000 - 40000) * 25 / 100 ≤ (min b 100000 - 40000) * 25 / 100 := by
    omega
  have h4 : (a - 100000) * 40 / 100 ≤ (b - 100000) * 40 / 100 := by
    omega
  omega
```

Sent back:
```
line 13:4: error: maximum recursion depth has been reached
use `set_option maxRecDepth <num>` to increase limit
use `set_option diagnostics true` to get diagnostic information
line 15:4: error: maximum recursion depth has been reached
use `set_option maxRecDepth <num>` to increase limit
use `set_option diagnostics true` to get diagnostic information
`tax_mono` depends on ['sorryAx'] (sorry, an axiom or native_decide)
```

### attempt 3: ok (Lean 5.5 s)

```lean
def tax (income : Nat) : Nat :=
  ((min income 40000 - 10000) * 10 / 100
    + (min income 100000 - 40000) * 25 / 100
    + (income - 100000) * 40 / 100) - 500

theorem tax_mono : ∀ a b : Nat, a ≤ b → tax a ≤ tax b := by
  intro a b h
  unfold tax
  have h2 : (min a 40000 - 10000) * 10 / 100 ≤ (min b 40000 - 10000) * 10 / 100 := by
    apply Nat.div_le_div_right
    apply Nat.mul_le_mul_right
    omega
  have h3 : (min a 100000 - 40000) * 25 / 100 ≤ (min b 100000 - 40000) * 25 / 100 := by
    apply Nat.div_le_div_right
    apply Nat.mul_le_mul_right
    omega
  have h4 : (a - 100000) * 40 / 100 ≤ (b - 100000) * 40 / 100 := by
    apply Nat.div_le_div_right
    apply Nat.mul_le_mul_right
    omega
  exact Nat.sub_le_sub_right (Nat.add_le_add (Nat.add_le_add h2 h3) h4) 500
```

## parking

```
    theorem parkingFee_le : ∀ m : Nat, parkingFee m ≤ 20 * (m / 1440 + 1)
    theorem parkingFee_mono : ∀ a b : Nat, a ≤ b → parkingFee a ≤ parkingFee b
```

### attempt 1: ok (Lean 3.8 s)

```lean
def partFee (r : Nat) : Nat :=
  if r ≤ 15 then 0 else min 20 (3 * ((r + 59) / 60))

def parkingFee (minutes : Nat) : Nat :=
  20 * (minutes / 1440) + partFee (minutes % 1440)

theorem partFee_le_twenty : ∀ r : Nat, partFee r ≤ 20 := by
  intro r
  unfold partFee
  split
  · omega
  · exact Nat.min_le_left _ _

theorem partFee_mono : ∀ x y : Nat, x ≤ y → partFee x ≤ partFee y := by
  intro x y hxy
  unfold partFee
  split <;> split <;> omega

theorem parkingFee_le : ∀ m : Nat, parkingFee m ≤ 20 * (m / 1440 + 1) := by
  intro m
  unfold parkingFee
  have h := partFee_le_twenty (m % 1440)
  omega

theorem parkingFee_mono : ∀ a b : Nat, a ≤ b → parkingFee a ≤ parkingFee b := by
  intro a b hab
  unfold parkingFee
  have h1 := partFee_le_twenty (a % 1440)
  by_cases hd : a / 1440 = b / 1440
  · have hr : a % 1440 ≤ b % 1440 := by omega
    have h2 := partFee_mono (a % 1440) (b % 1440) hr
    omega
  · omega
```
