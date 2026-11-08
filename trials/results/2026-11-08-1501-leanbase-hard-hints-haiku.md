# Lean-direct baseline 2026-11-08-1501 (haiku)

| task | result | lines | Lean s per attempt |
|---|---|---|---|
| loop | after 2 fixes | 40 | [5.4, 5.9, 4.4] |
| bsearch | after 2 fixes | 87 | [7.2, 7.5, 5.5] |
| gcd | after 1 fix | 52 | [1.3, 2.5] |
| rle | first try | 61 | [4.6] |

## loop

```
    theorem sumSq_spec : ∀ xs : List Nat, sumSq xs = (xs.map (fun x => x * x)).sum
```

### attempt 1: errors (Lean 5.4 s)

```lean
def sumSq (xs : List Nat) : Nat :=
  Id.run do
    let mut acc := 0
    for x in xs do
      acc := acc + x * x
    return acc

theorem sumSq_spec : ∀ xs : List Nat, sumSq xs = (xs.map (fun x => x * x)).sum := by
  intro xs
  have gen : ∀ (ys : List Nat) (n : Nat),
      (Id.run do
        let mut acc := n
        for x in ys do
          acc := acc + x * x
        return acc) = n + (ys.map (fun x => x * x)).sum := by
    intro ys
    induction ys with
    | nil => intro n; rfl
    | cons y ys ih =>
      intro n
      exact (ih (n + y * y)).trans (by simp [List.map_cons, List.sum_cons, Nat.add_assoc])
  exact (gen xs 0).trans (Nat.zero_add _)

#eval sumSq [1, 2, 3]
```

Sent back:
```
line 21:36: error: unsolved goals
xs : List Nat
y : Nat
ys : List Nat
ih :
  ∀ (n : Nat),
    (let acc := n;
        do
        let __s ←
          forIn ys acc fun x __s =>
              let acc := __s;
              let acc := acc + x * x;
              pure (ForInStep.yield acc)
        let acc : Nat := __s
        pure acc).run =
      n + (List.map (fun x => x * x) ys).sum
n : Nat
⊢ n + (y * y + (List.map (fun x => x * x) ys).sum) = ?m.85
`sumSq_spec` depends on ['sorryAx'] (sorry, an axiom or native_decide)
```

### attempt 2: errors (Lean 5.9 s)

```lean
def sumSq (xs : List Nat) : Nat :=
  Id.run do
    let mut acc := 0
    for x in xs do
      acc := acc + x * x
    return acc

def loopSum (ys : List Nat) (n : Nat) : Nat :=
  Id.run do
    let mut acc := n
    for x in ys do
      acc := acc + x * x
    return acc

theorem loopSum_eq (ys : List Nat) :
    ∀ n : Nat, loopSum ys n = n + (ys.map (fun x => x * x)).sum := by
  induction ys with
  | nil =>
    intro n
    rfl
  | cons y ys ih =>
    intro n
    have h := ih (n + y * y)
    show loopSum ys (n + y * y) = n + ((y :: ys).map (fun x => x * x)).sum
    rw [h]
    simp only [List.map_cons, List.sum_cons]
    simp [Nat.add_assoc]

theorem sumSq_spec : ∀ xs : List Nat, sumSq xs = (xs.map (fun x => x * x)).sum := by
  intro xs
  show loopSum xs 0 = _
  exact (loopSum_eq xs 0).trans (Nat.zero_add _)

#eval sumSq [1, 2, 3]
```

Sent back:
```
line 24:4: error: 'show' tactic failed, pattern
  loopSum ys (n + y * y) = n + (List.map (fun x => x * x) (y :: ys)).sum
is not definitionally equal to target
  loopSum (y :: ys) n = n + (List.map (fun x => x * x) (y :: ys)).sum
`sumSq_spec` depends on ['sorryAx'] (sorry, an axiom or native_decide)
```

### attempt 3: ok (Lean 4.4 s)

```lean
def sumSq (xs : List Nat) : Nat :=
  Id.run do
    let mut acc := 0
    for x in xs do
      acc := acc + x * x
    return acc

def loopSum (ys : List Nat) (n : Nat) : Nat :=
  Id.run do
    let mut acc := n
    for x in ys do
      acc := acc + x * x
    return acc

theorem loopSum_cons (y : Nat) (ys : List Nat) (n : Nat) :
    loopSum (y :: ys) n = loopSum ys (n + y * y) := by
  first
  | rfl
  | (unfold loopSum; rfl)
  | simp [loopSum]

theorem loopSum_eq (ys : List Nat) :
    ∀ n : Nat, loopSum ys n = n + (ys.map (fun x => x * x)).sum := by
  induction ys with
  | nil =>
    intro n
    first
    | rfl
    | simp [loopSum]
  | cons y ys ih =>
    intro n
    rw [loopSum_cons, ih]
    simp only [List.map_cons, List.sum_cons]
    rw [Nat.add_assoc]

theorem sumSq_eq_loopSum (xs : List Nat) : sumSq xs = loopSum xs 0 := by
  first
  | rfl
  | (unfold sumSq loopSum; rfl)
  | simp [sumSq, loopSum]

theorem sumSq_spec : ∀ xs : List Nat, sumSq xs = (xs.map (fun x => x * x)).sum := by
  intro xs
  rw [sumSq_eq_loopSum, loopSum_eq, Nat.zero_add]

#eval sumSq [1, 2, 3]
```

## bsearch

```
    theorem lowerBound_le : ∀ (xs : Array Int) (x : Int), lowerBound xs x ≤ xs.size
    theorem lowerBound_spec : ∀ (xs : Array Int) (x : Int), xs.toList.Pairwise (· ≤ ·) → (∀ i (h : i < xs.size), i < lowerBound xs x → xs[i] < x) ∧ (∀ i (h : i < xs.size), lowerBound xs x ≤ i → x ≤ xs[i])
```

### attempt 1: errors (Lean 7.2 s)

```lean
def lowerBoundAux (xs : Array Int) (x : Int) (lo hi : Nat) (hhi : hi ≤ xs.size) : Nat :=
  if h : lo < hi then
    if xs[(lo + hi) / 2]'(by omega) < x then
      lowerBoundAux xs x ((lo + hi) / 2 + 1) hi hhi
    else
      lowerBoundAux xs x lo ((lo + hi) / 2) (by omega)
  else lo
termination_by hi - lo
decreasing_by all_goals omega

def lowerBound (xs : Array Int) (x : Int) : Nat :=
  lowerBoundAux xs x 0 xs.size (Nat.le_refl _)

theorem sorted_le (xs : Array Int) (hs : xs.toList.Pairwise (· ≤ ·))
    (i j : Nat) (hi : i < xs.size) (hj : j < xs.size) (hij : i ≤ j) : xs[i] ≤ xs[j] := by
  rcases Nat.lt_or_eq_of_le hij with h | h
  · have := List.pairwise_iff_getElem.mp hs i j (by simpa using hi) (by simpa using hj) h
    simpa using this
  · subst h
    exact Int.le_refl _

theorem aux_le (xs : Array Int) (x : Int) : ∀ n (lo hi : Nat) (hhi : hi ≤ xs.size),
    hi - lo = n → lo ≤ hi → ∀ r, r = lowerBoundAux xs x lo hi hhi → r ≤ hi := by
  intro n
  induction n using Nat.strongRecOn with
  | ind n ih =>
  intro lo hi hhi hn hle r hr
  rw [lowerBoundAux] at hr
  by_cases h : lo < hi
  · rw [dif_pos h] at hr
    by_cases hc : xs[(lo + hi) / 2]'(by omega) < x
    · rw [if_pos hc] at hr
      subst hr
      exact ih (hi - ((lo + hi) / 2 + 1)) (by omega) ((lo + hi) / 2 + 1) hi hhi rfl
        (by omega) _ rfl
    · rw [if_neg hc] at hr
      subst hr
      exact ih ((lo + hi) / 2 - lo) (by omega) lo ((lo + hi) / 2) (by omega) rfl
        (by omega) _ rfl
  · rw [dif_neg h] at hr
    subst hr
    omega

theorem aux_spec (xs : Array Int) (x : Int) (hs : xs.toList.Pairwise (· ≤ ·)) :
    ∀ n (lo hi : Nat) (hhi : hi ≤ xs.size),
    hi - lo = n → lo ≤ hi →
    (∀ i (h : i < xs.size), i < lo → xs[i] < x) →
    (∀ i (h : i < xs.size), hi ≤ i → x ≤ xs[i]) →
    ∀ r, r = lowerBoundAux xs x lo hi hhi →
      r ≤ hi ∧ (∀ i (h : i < xs.size), i < r → xs[i] < x) ∧
      (∀ i (h : i < xs.size), r ≤ i → x ≤ xs[i]) := by
  intro n
  induction n using Nat.strongRecOn with
  | ind n ih =>
  intro lo hi hhi hn hle hL hR r hr
  rw [lowerBoundAux] at hr
  by_cases h : lo < hi
  · rw [dif_pos h] at hr
    by_cases hc : xs[(lo + hi) / 2]'(by omega) < x
    · rw [if_pos hc] at hr
      subst hr
      refine ih (hi - ((lo + hi) / 2 + 1)) (by omega) ((lo + hi) / 2 + 1) hi hhi rfl
        (by omega) ?_ ?_ _ rfl
      · intro i hiy hlt
        exact Int.lt_of_le_of_lt (sorted_le xs hs i ((lo + hi) / 2) hiy (by omega) (by omega)) hc
      · exact hR
    · rw [if_neg hc] at hr
      subst hr
      refine ih ((lo + hi) / 2 - lo) (by omega) lo ((lo + hi) / 2) (by omega) rfl
        (by omega) hL ?_ _ rfl
      intro i hiy hge
      exact Int.le_trans (not_lt.mp hc) (sorted_le xs hs ((lo + hi) / 2) i (by omega) hiy hge)
  · rw [dif_neg h] at hr
    subst hr
    refine ⟨by omega, fun i hiy hlt => hL i hiy hlt, fun i hiy hge => hR i hiy (by omega)⟩

theorem lowerBound_le : ∀ (xs : Array Int) (x : Int), lowerBound xs x ≤ xs.size := by
  intro xs x
  unfold lowerBound
  exact aux_le xs x (xs.size - 0) 0 xs.size (Nat.le_refl _) rfl (Nat.zero_le _) _ rfl

theorem lowerBound_spec : ∀ (xs : Array Int) (x : Int), xs.toList.Pairwise (· ≤ ·) →
    (∀ i (h : i < xs.size), i < lowerBound xs x → xs[i] < x) ∧
    (∀ i (h : i < xs.size), lowerBound xs x ≤ i → x ≤ xs[i]) := by
  intro xs x hs
  have key := aux_spec xs x hs (xs.size - 0) 0 xs.size (Nat.le_refl _) rfl (Nat.zero_le _)
    (fun i hiy hlt => by omega) (fun i hiy hge => by omega) _ rfl
  unfold lowerBound
  exact ⟨key.2.1, key.2.2⟩
```

Sent back:
```
line 38:6: error: Type mismatch
  ih ((lo + hi) / 2 - lo) (Decidable.byContradiction fun a => aux_le._proof_1_5 xs x n lo hi hhi hn h a) lo
    ((lo + hi) / 2) (Decidable.byContradiction fun a => aux_le._proof_1_6 xs x n lo hi hhi h a) rfl
    (Decidable.byContradiction fun a => aux_le._proof_1_7 xs x n lo hi hhi h a)
    (lowerBoundAux xs x lo ((lo + hi) / 2) (Decidable.byContradiction fun a => aux_le._proof_1_6 xs x n lo hi hhi h a))
    rfl
has type
  lowerBoundAux xs x lo ((lo + hi) / 2) ⋯ ≤ (lo + hi) / 2
but is expected to have type
  lowerBoundAux xs x lo ((lo + hi) / 2) ⋯ ≤ hi
line 69:6: error: Type mismatch
  ih ((lo + hi) / 2 - lo) (Decidable.byContradiction fun a => aux_spec._proof_1_7 xs x n lo hi hhi hn h a) lo
    ((lo + hi) / 2) (Decidable.byContradiction fun a => aux_spec._proof_1_8 xs x n lo hi hhi h a) rfl
    (Decidable.byContradiction fun a => aux_spec._proof_1_9 xs x n lo hi hhi h a) hL ?m.345
    (lowerBoundAux xs x lo ((lo + hi) / 2)
      (Decidable.byContradiction fun a => aux_spec._proof_1_8 xs x n lo hi hhi h a))
    rfl
has type
  lowerBoundAux xs x lo ((lo + hi) / 2) ⋯ ≤ (lo + hi) / 2 ∧
    (∀ (i : Nat) (h_1 : i < xs.size), i < lowerBoundAux xs x lo ((lo + hi) / 2) ⋯ → xs[i] < x) ∧
      ∀ (i : Nat) (h_1 : i < xs.size), lowerBoundAux xs x lo ((lo + hi) / 2) ⋯ ≤ i → x ≤ xs[i]
but is expected to have type
  lowerBoundAux xs x lo ((lo + hi) / 2) ⋯ ≤ hi ∧
    (∀ (i : Nat) (h_1 : i < xs.size), i < lowerBoundAux xs x lo ((lo + hi) / 2) ⋯ → xs[i] < x) ∧
      ∀ (i : Nat) (h_1 : i < xs.size), lowerBoundAux xs x lo ((lo + hi) / 2) ⋯ ≤ i → x ≤ xs[i]
`lowerBound_le` depends on ['sorryAx'] (sorry, an axiom or native_decide)
`lowerBound_spec` depends on ['sorryAx'] (sorry, an axiom or native_decide)
```

### attempt 2: errors (Lean 7.5 s)

```lean
def lowerBoundAux (xs : Array Int) (x : Int) (lo hi : Nat) (hhi : hi ≤ xs.size) : Nat :=
  if h : lo < hi then
    if xs[(lo + hi) / 2]'(by omega) < x then
      lowerBoundAux xs x ((lo + hi) / 2 + 1) hi hhi
    else
      lowerBoundAux xs x lo ((lo + hi) / 2) (by omega)
  else lo
termination_by hi - lo
decreasing_by all_goals omega

def lowerBound (xs : Array Int) (x : Int) : Nat :=
  lowerBoundAux xs x 0 xs.size (Nat.le_refl _)

theorem sorted_le (xs : Array Int) (hs : xs.toList.Pairwise (· ≤ ·))
    (i j : Nat) (hi : i < xs.size) (hj : j < xs.size) (hij : i ≤ j) : xs[i] ≤ xs[j] := by
  rcases Nat.lt_or_eq_of_le hij with h | h
  · have := List.pairwise_iff_getElem.mp hs i j (by simpa using hi) (by simpa using hj) h
    simpa using this
  · subst h
    exact Int.le_refl _

theorem aux_le (xs : Array Int) (x : Int) : ∀ n (lo hi : Nat) (hhi : hi ≤ xs.size),
    hi - lo = n → lo ≤ hi → ∀ r, r = lowerBoundAux xs x lo hi hhi → r ≤ hi := by
  intro n
  induction n using Nat.strongRecOn with
  | ind n ih =>
  intro lo hi hhi hn hle r hr
  rw [lowerBoundAux] at hr
  by_cases h : lo < hi
  · rw [dif_pos h] at hr
    by_cases hc : xs[(lo + hi) / 2]'(by omega) < x
    · rw [if_pos hc] at hr
      subst hr
      exact ih (hi - ((lo + hi) / 2 + 1)) (by omega) ((lo + hi) / 2 + 1) hi hhi rfl
        (by omega) _ rfl
    · rw [if_neg hc] at hr
      subst hr
      exact Nat.le_trans
        (ih ((lo + hi) / 2 - lo) (by omega) lo ((lo + hi) / 2) (by omega) rfl
          (by omega) _ rfl)
        (by omega)
  · rw [dif_neg h] at hr
    subst hr
    omega

theorem aux_spec (xs : Array Int) (x : Int) (hs : xs.toList.Pairwise (· ≤ ·)) :
    ∀ n (lo hi : Nat) (hhi : hi ≤ xs.size),
    hi - lo = n → lo ≤ hi →
    (∀ i (h : i < xs.size), i < lo → xs[i] < x) →
    (∀ i (h : i < xs.size), hi ≤ i → x ≤ xs[i]) →
    ∀ r, r = lowerBoundAux xs x lo hi hhi →
      r ≤ hi ∧ (∀ i (h : i < xs.size), i < r → xs[i] < x) ∧
      (∀ i (h : i < xs.size), r ≤ i → x ≤ xs[i]) := by
  intro n
  induction n using Nat.strongRecOn with
  | ind n ih =>
  intro lo hi hhi hn hle hL hR r hr
  rw [lowerBoundAux] at hr
  by_cases h : lo < hi
  · rw [dif_pos h] at hr
    by_cases hc : xs[(lo + hi) / 2]'(by omega) < x
    · rw [if_pos hc] at hr
      subst hr
      refine ih (hi - ((lo + hi) / 2 + 1)) (by omega) ((lo + hi) / 2 + 1) hi hhi rfl
        (by omega) ?_ ?_ _ rfl
      · intro i hiy hlt
        exact Int.lt_of_le_of_lt (sorted_le xs hs i ((lo + hi) / 2) hiy (by omega) (by omega)) hc
      · exact hR
    · rw [if_neg hc] at hr
      subst hr
      have hR' : ∀ i (h : i < xs.size), (lo + hi) / 2 ≤ i → x ≤ xs[i] := by
        intro i hiy hge
        exact Int.le_trans (not_lt.mp hc) (sorted_le xs hs ((lo + hi) / 2) i (by omega) hiy hge)
      obtain ⟨h1, h2, h3⟩ := ih ((lo + hi) / 2 - lo) (by omega) lo ((lo + hi) / 2) (by omega) rfl
        (by omega) hL hR' _ rfl
      exact ⟨Nat.le_trans h1 (by omega), h2, h3⟩
  · rw [dif_neg h] at hr
    subst hr
    refine ⟨by omega, fun i hiy hlt => hL i hiy hlt, fun i hiy hge => hR i hiy (by omega)⟩

theorem lowerBound_le : ∀ (xs : Array Int) (x : Int), lowerBound xs x ≤ xs.size := by
  intro xs x
  unfold lowerBound
  exact aux_le xs x (xs.size - 0) 0 xs.size (Nat.le_refl _) rfl (Nat.zero_le _) _ rfl

theorem lowerBound_spec : ∀ (xs : Array Int) (x : Int), xs.toList.Pairwise (· ≤ ·) →
    (∀ i (h : i < xs.size), i < lowerBound xs x → xs[i] < x) ∧
    (∀ i (h : i < xs.size), lowerBound xs x ≤ i → x ≤ xs[i]) := by
  intro xs x hs
  have key := aux_spec xs x hs (xs.size - 0) 0 xs.size (Nat.le_refl _) rfl (Nat.zero_le _)
    (fun i hiy hlt => by omega) (fun i hiy hge => by omega) _ rfl
  unfold lowerBound
  exact ⟨key.2.1, key.2.2⟩
```

Sent back:
```
line 73:28: error: Unknown identifier `not_lt.mp`
`lowerBound_spec` depends on ['sorryAx'] (sorry, an axiom or native_decide)
```

### attempt 3: ok (Lean 5.5 s)

```lean
def lowerBoundAux (xs : Array Int) (x : Int) (lo hi : Nat) (hhi : hi ≤ xs.size) : Nat :=
  if h : lo < hi then
    if xs[(lo + hi) / 2]'(by omega) < x then
      lowerBoundAux xs x ((lo + hi) / 2 + 1) hi hhi
    else
      lowerBoundAux xs x lo ((lo + hi) / 2) (by omega)
  else lo
termination_by hi - lo
decreasing_by all_goals omega

def lowerBound (xs : Array Int) (x : Int) : Nat :=
  lowerBoundAux xs x 0 xs.size (Nat.le_refl _)

theorem sorted_le (xs : Array Int) (hs : xs.toList.Pairwise (· ≤ ·))
    (i j : Nat) (hi : i < xs.size) (hj : j < xs.size) (hij : i ≤ j) : xs[i] ≤ xs[j] := by
  rcases Nat.lt_or_eq_of_le hij with h | h
  · have := List.pairwise_iff_getElem.mp hs i j (by simpa using hi) (by simpa using hj) h
    simpa using this
  · subst h
    exact Int.le_refl _

theorem aux_le (xs : Array Int) (x : Int) : ∀ n (lo hi : Nat) (hhi : hi ≤ xs.size),
    hi - lo = n → lo ≤ hi → ∀ r, r = lowerBoundAux xs x lo hi hhi → r ≤ hi := by
  intro n
  induction n using Nat.strongRecOn with
  | ind n ih =>
  intro lo hi hhi hn hle r hr
  rw [lowerBoundAux] at hr
  by_cases h : lo < hi
  · rw [dif_pos h] at hr
    by_cases hc : xs[(lo + hi) / 2]'(by omega) < x
    · rw [if_pos hc] at hr
      subst hr
      exact ih (hi - ((lo + hi) / 2 + 1)) (by omega) ((lo + hi) / 2 + 1) hi hhi rfl
        (by omega) _ rfl
    · rw [if_neg hc] at hr
      subst hr
      exact Nat.le_trans
        (ih ((lo + hi) / 2 - lo) (by omega) lo ((lo + hi) / 2) (by omega) rfl
          (by omega) _ rfl)
        (by omega)
  · rw [dif_neg h] at hr
    subst hr
    omega

theorem aux_spec (xs : Array Int) (x : Int) (hs : xs.toList.Pairwise (· ≤ ·)) :
    ∀ n (lo hi : Nat) (hhi : hi ≤ xs.size),
    hi - lo = n → lo ≤ hi →
    (∀ i (h : i < xs.size), i < lo → xs[i] < x) →
    (∀ i (h : i < xs.size), hi ≤ i → x ≤ xs[i]) →
    ∀ r, r = lowerBoundAux xs x lo hi hhi →
      r ≤ hi ∧ (∀ i (h : i < xs.size), i < r → xs[i] < x) ∧
      (∀ i (h : i < xs.size), r ≤ i → x ≤ xs[i]) := by
  intro n
  induction n using Nat.strongRecOn with
  | ind n ih =>
  intro lo hi hhi hn hle hL hR r hr
  rw [lowerBoundAux] at hr
  by_cases h : lo < hi
  · rw [dif_pos h] at hr
    by_cases hc : xs[(lo + hi) / 2]'(by omega) < x
    · rw [if_pos hc] at hr
      subst hr
      refine ih (hi - ((lo + hi) / 2 + 1)) (by omega) ((lo + hi) / 2 + 1) hi hhi rfl
        (by omega) ?_ ?_ _ rfl
      · intro i hiy hlt
        exact Int.lt_of_le_of_lt (sorted_le xs hs i ((lo + hi) / 2) hiy (by omega) (by omega)) hc
      · exact hR
    · rw [if_neg hc] at hr
      subst hr
      have hR' : ∀ i (h : i < xs.size), (lo + hi) / 2 ≤ i → x ≤ xs[i] := by
        intro i hiy hge
        exact Int.le_trans (Int.not_lt.mp hc) (sorted_le xs hs ((lo + hi) / 2) i (by omega) hiy hge)
      obtain ⟨h1, h2, h3⟩ := ih ((lo + hi) / 2 - lo) (by omega) lo ((lo + hi) / 2) (by omega) rfl
        (by omega) hL hR' _ rfl
      exact ⟨Nat.le_trans h1 (by omega), h2, h3⟩
  · rw [dif_neg h] at hr
    subst hr
    refine ⟨by omega, fun i hiy hlt => hL i hiy hlt, fun i hiy hge => hR i hiy (by omega)⟩

theorem lowerBound_le : ∀ (xs : Array Int) (x : Int), lowerBound xs x ≤ xs.size := by
  intro xs x
  unfold lowerBound
  exact aux_le xs x (xs.size - 0) 0 xs.size (Nat.le_refl _) rfl (Nat.zero_le _) _ rfl

theorem lowerBound_spec : ∀ (xs : Array Int) (x : Int), xs.toList.Pairwise (· ≤ ·) →
    (∀ i (h : i < xs.size), i < lowerBound xs x → xs[i] < x) ∧
    (∀ i (h : i < xs.size), lowerBound xs x ≤ i → x ≤ xs[i]) := by
  intro xs x hs
  have key := aux_spec xs x hs (xs.size - 0) 0 xs.size (Nat.le_refl _) rfl (Nat.zero_le _)
    (fun i hiy hlt => by omega) (fun i hiy hge => by omega) _ rfl
  unfold lowerBound
  exact ⟨key.2.1, key.2.2⟩
```

## gcd

```
    theorem gcd'_dvd : ∀ a b : Nat, gcd' a b ∣ a ∧ gcd' a b ∣ b
    theorem gcd'_greatest : ∀ a b d : Nat, d ∣ a → d ∣ b → d ∣ gcd' a b
```

### attempt 1: errors (Lean 1.3 s)

```lean
def gcd' (a b : Nat) : Nat :=
  if h : b = 0 then a else gcd' b (a % b)
termination_by b
decreasing_by
  all_goals (try simp_wf)
  exact Nat.mod_lt _ (Nat.pos_of_ne_zero h)

theorem gcd'_zero (a : Nat) : gcd' a 0 = a := by
  rw [gcd']
  simp

theorem gcd'_succ (a b : Nat) (h : b ≠ 0) : gcd' a b = gcd' b (a % b) := by
  rw [gcd']
  simp [h]

theorem gcd'_dvd : ∀ a b : Nat, gcd' a b ∣ a ∧ gcd' a b ∣ b := by
  intro a b
  induction b using Nat.strongRecOn generalizing a with
  | ind b ih =>
    by_cases hb : b = 0
    · subst hb
      rw [gcd'_zero]
      exact ⟨Nat.dvd_refl a, Nat.dvd_zero a⟩
    · rw [gcd'_succ a b hb]
      have hlt : a % b < b := Nat.mod_lt _ (Nat.pos_of_ne_zero hb)
      obtain ⟨h1, h2⟩ := ih (a % b) hlt b
      refine ⟨?_, h1⟩
      have h3 : gcd' b (a % b) ∣ b * (a / b) := Dvd.dvd.mul_right h1 _
      have h4 : gcd' b (a % b) ∣ a % b + b * (a / b) := Nat.dvd_add h2 h3
      rw [Nat.mod_add_div] at h4
      exact h4

theorem gcd'_greatest : ∀ a b d : Nat, d ∣ a → d ∣ b → d ∣ gcd' a b := by
  intro a b
  induction b using Nat.strongRecOn generalizing a with
  | ind b ih =>
    intro d hda hdb
    by_cases hb : b = 0
    · subst hb
      rw [gcd'_zero]
      exact hda
    · rw [gcd'_succ a b hb]
      have hlt : a % b < b := Nat.mod_lt _ (Nat.pos_of_ne_zero hb)
      have h3 : d ∣ b * (a / b) := Dvd.dvd.mul_right hdb _
      have h4 : d ∣ a % b + b * (a / b) := by
        rw [Nat.mod_add_div]
        exact hda
      have hmod : d ∣ a % b := by
        first
        | exact (Nat.dvd_add_left h3).mp h4
        | exact (Nat.dvd_add_iff_left h3).mpr h4
        | exact (Nat.dvd_add_right h3).mp (by rwa [Nat.add_comm] at h4)
        | simpa using (Nat.dvd_add_left h3).mp h4
      exact ih (a % b) hlt b d hdb hmod
```

Sent back:
```
line 28:48: error: Unknown constant `Dvd.dvd.mul_right`
line 44:35: error: Unknown constant `Dvd.dvd.mul_right`
`gcd'_dvd` depends on ['sorryAx'] (sorry, an axiom or native_decide)
`gcd'_greatest` depends on ['sorryAx'] (sorry, an axiom or native_decide)
```

### attempt 2: ok (Lean 2.5 s)

```lean
def gcd' (a b : Nat) : Nat :=
  if h : b = 0 then a else gcd' b (a % b)
termination_by b
decreasing_by
  all_goals (try simp_wf)
  exact Nat.mod_lt _ (Nat.pos_of_ne_zero h)

theorem gcd'_zero (a : Nat) : gcd' a 0 = a := by
  rw [gcd']
  simp

theorem gcd'_succ (a b : Nat) (h : b ≠ 0) : gcd' a b = gcd' b (a % b) := by
  rw [gcd']
  simp [h]

theorem gcd'_dvd : ∀ a b : Nat, gcd' a b ∣ a ∧ gcd' a b ∣ b := by
  intro a b
  induction b using Nat.strongRecOn generalizing a with
  | ind b ih =>
    by_cases hb : b = 0
    · subst hb
      rw [gcd'_zero]
      exact ⟨Nat.dvd_refl a, Nat.dvd_zero a⟩
    · rw [gcd'_succ a b hb]
      have hlt : a % b < b := Nat.mod_lt _ (Nat.pos_of_ne_zero hb)
      obtain ⟨h1, h2⟩ := ih (a % b) hlt b
      refine ⟨?_, h1⟩
      have h3 : gcd' b (a % b) ∣ b * (a / b) :=
        Nat.dvd_trans h1 (Nat.dvd_mul_right b (a / b))
      have h4 : gcd' b (a % b) ∣ a % b + b * (a / b) := Nat.dvd_add h2 h3
      rw [Nat.mod_add_div] at h4
      exact h4

theorem gcd'_greatest : ∀ a b d : Nat, d ∣ a → d ∣ b → d ∣ gcd' a b := by
  intro a b
  induction b using Nat.strongRecOn generalizing a with
  | ind b ih =>
    intro d hda hdb
    by_cases hb : b = 0
    · subst hb
      rw [gcd'_zero]
      exact hda
    · rw [gcd'_succ a b hb]
      have hlt : a % b < b := Nat.mod_lt _ (Nat.pos_of_ne_zero hb)
      have h3 : d ∣ b * (a / b) :=
        Nat.dvd_trans hdb (Nat.dvd_mul_right b (a / b))
      have h4 : d ∣ a % b + b * (a / b) := by
        rw [Nat.mod_add_div]
        exact hda
      have hmod : d ∣ a % b := by
        first
        | exact (Nat.dvd_add_left h3).mp h4
        | exact (Nat.dvd_add_iff_left h3).mpr h4
        | exact (Nat.dvd_add_right h3).mp (by rwa [Nat.add_comm] at h4)
        | simpa using (Nat.dvd_add_left h3).mp h4
      exact ih (a % b) hlt b d hdb hmod
```

## rle

```
    theorem decode_encode : ∀ xs : List Int, decode (encode xs) = xs
    theorem encode_counts_pos : ∀ xs : List Int, ∀ p ∈ encode xs, 0 < p.2
```

### attempt 1: ok (Lean 4.6 s)

```lean
def pushRun (x : Int) : List (Int × Nat) → List (Int × Nat)
  | [] => [(x, 1)]
  | (y, n) :: rest => if x = y then (y, n + 1) :: rest else (x, 1) :: (y, n) :: rest

def encode (xs : List Int) : List (Int × Nat) :=
  match xs with
  | [] => []
  | x :: rest => pushRun x (encode rest)

def decode (ps : List (Int × Nat)) : List Int :=
  match ps with
  | [] => []
  | (v, n) :: rest => List.replicate n v ++ decode rest

theorem decode_pushRun (x : Int) (ps : List (Int × Nat)) :
    decode (pushRun x ps) = x :: decode ps := by
  cases ps with
  | nil => simp [pushRun, decode]
  | cons q rest =>
    obtain ⟨y, n⟩ := q
    by_cases h : x = y
    · subst h
      simp [pushRun, decode, List.replicate_succ]
    · simp [pushRun, decode, h, List.replicate_succ]

theorem decode_encode : ∀ xs : List Int, decode (encode xs) = xs := by
  intro xs
  induction xs with
  | nil => simp [encode, decode]
  | cons x xs ih => rw [encode, decode_pushRun, ih]

theorem pushRun_pos (x : Int) (ps : List (Int × Nat)) (h : ∀ p ∈ ps, 0 < p.2) :
    ∀ p ∈ pushRun x ps, 0 < p.2 := by
  cases ps with
  | nil =>
    intro p hp
    simp only [pushRun, List.mem_singleton] at hp
    subst hp
    simp
  | cons q rest =>
    obtain ⟨y, n⟩ := q
    have hn : 0 < n := h (y, n) (by simp)
    have hrest : ∀ p ∈ rest, 0 < p.2 := fun p hp => h p (by simp [hp])
    intro p hp
    by_cases hxy : x = y
    · rw [pushRun, if_pos hxy] at hp
      simp only [List.mem_cons] at hp
      rcases hp with rfl | hp
      · simp
      · exact hrest p hp
    · rw [pushRun, if_neg hxy] at hp
      simp only [List.mem_cons] at hp
      rcases hp with rfl | rfl | hp
      · simp
      · exact hn
      · exact hrest p hp

theorem encode_counts_pos : ∀ xs : List Int, ∀ p ∈ encode xs, 0 < p.2 := by
  intro xs
  induction xs with
  | nil =>
    intro p hp
    simp [encode] at hp
  | cons x xs ih =>
    intro p hp
    rw [encode] at hp
    exact pushRun_pos x (encode xs) ih p hp
```
