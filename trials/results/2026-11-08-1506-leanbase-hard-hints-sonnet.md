# Lean-direct baseline 2026-11-08-1506 (sonnet)

| task | result | lines | Lean s per attempt |
|---|---|---|---|
| loop | after 1 fix | 15 | [3.1, 3.7] |
| bsearch | first try | 86 | [4.9] |
| gcd | after 1 fix | 34 | [2.4, 3.3] |
| rle | first try | 58 | [2.3] |

## loop

```
    theorem sumSq_spec : ∀ xs : List Nat, sumSq xs = (xs.map (fun x => x * x)).sum
```

### attempt 1: errors (Lean 3.1 s)

```lean
def sumSq (xs : List Nat) : Nat := Id.run do
  let mut acc := 0
  for x in xs do
    acc := acc + x * x
  return acc

theorem sumSq_aux (xs : List Nat) (acc : Nat) :
    (Id.run do
      let mut a := acc
      for x in xs do
        a := a + x * x
      return a) = acc + (xs.map (fun x => x * x)).sum := by
  induction xs generalizing acc with
  | nil => simp
  | cons x xs ih =>
    simp [ih, Nat.add_assoc]

theorem sumSq_spec : ∀ xs : List Nat, sumSq xs = (xs.map (fun x => x * x)).sum := by
  intro xs
  have h := sumSq_aux xs 0
  simpa [sumSq] using h
```

Sent back:
```
line 15:17: error: unsolved goals
case cons
x : Nat
xs : List Nat
ih :
  ∀ (acc : Nat),
    (let a := acc;
        do
        let __s ←
          forIn xs a fun x __s =>
              let a := __s;
              let a := a + x * x;
              pure (ForInStep.yield a)
        let a : Nat := __s
        pure a).run =
      acc + (List.map (fun x => x * x) xs).sum
acc : Nat
⊢ List.foldl (fun b a => b + a * a) (acc + x * x) xs = acc + (x * x + (List.map (fun x => x * x) xs).sum)
`sumSq_spec` depends on ['sorryAx'] (sorry, an axiom or native_decide)
```

### attempt 2: ok (Lean 3.7 s)

```lean
def sumSq (xs : List Nat) : Nat := Id.run do
  let mut acc := 0
  for x in xs do
    acc := acc + x * x
  return acc

theorem sumSq_aux (xs : List Nat) (acc : Nat) :
    xs.foldl (fun b a => b + a * a) acc = acc + (xs.map (fun x => x * x)).sum := by
  induction xs generalizing acc with
  | nil => simp
  | cons x xs ih =>
    simp only [List.foldl_cons, List.map_cons, List.sum_cons, ih]
    rw [Nat.add_assoc]

theorem sumSq_spec : ∀ xs : List Nat, sumSq xs = (xs.map (fun x => x * x)).sum := by
  intro xs
  simpa [sumSq] using sumSq_aux xs 0
```

## bsearch

```
    theorem lowerBound_le : ∀ (xs : Array Int) (x : Int), lowerBound xs x ≤ xs.size
    theorem lowerBound_spec : ∀ (xs : Array Int) (x : Int), xs.toList.Pairwise (· ≤ ·) → (∀ i (h : i < xs.size), i < lowerBound xs x → xs[i] < x) ∧ (∀ i (h : i < xs.size), lowerBound xs x ≤ i → x ≤ xs[i])
```

### attempt 1: ok (Lean 4.9 s)

```lean
def lbAux (xs : Array Int) (x : Int) (lo hi : Nat) : Nat :=
  if h : lo < hi then
    if hm : (lo + hi) / 2 < xs.size then
      if xs[(lo + hi) / 2] < x then lbAux xs x ((lo + hi) / 2 + 1) hi
      else lbAux xs x lo ((lo + hi) / 2)
    else lo
  else lo
termination_by hi - lo
decreasing_by all_goals omega

def lowerBound (xs : Array Int) (x : Int) : Nat := lbAux xs x 0 xs.size

theorem lbAux_spec (xs : Array Int) (x : Int) (hs : xs.toList.Pairwise (· ≤ ·)) :
    ∀ n lo hi, hi - lo = n → lo ≤ hi → hi ≤ xs.size →
      (∀ i (h : i < xs.size), i < lo → xs[i] < x) →
      (∀ i (h : i < xs.size), hi ≤ i → x ≤ xs[i]) →
      lo ≤ lbAux xs x lo hi ∧ lbAux xs x lo hi ≤ hi ∧
      (∀ i (h : i < xs.size), i < lbAux xs x lo hi → xs[i] < x) ∧
      (∀ i (h : i < xs.size), lbAux xs x lo hi ≤ i → x ≤ xs[i]) := by
  have mono : ∀ i j (hi : i < xs.size) (hj : j < xs.size), i ≤ j → xs[i] ≤ xs[j] := by
    intro i j hi hj hij
    rcases Nat.eq_or_lt_of_le hij with h | h
    · subst h; exact Int.le_refl _
    · have := List.pairwise_iff_getElem.mp hs i j (by simpa using hi) (by simpa using hj) h
      simpa using this
  intro n
  induction n using Nat.strongRecOn with
  | ind n ih =>
    intro lo hi hn h1 h2 hl hh
    rw [lbAux]
    split
    · rename_i hlt
      split
      · rename_i hm
        split
        · rename_i hlx
          have := ih (hi - ((lo + hi) / 2 + 1)) (by omega) ((lo + hi) / 2 + 1) hi rfl
            (by omega) h2
            (by
              intro i hi' hlt'
              exact Int.lt_of_le_of_lt (mono i ((lo + hi) / 2) hi' hm (by omega)) hlx)
            hh
          obtain ⟨a, b, c, d⟩ := this
          exact ⟨by omega, b, c, d⟩
        · rename_i hlx
          have hx : x ≤ xs[(lo + hi) / 2] := Int.not_lt.mp hlx
          have := ih ((lo + hi) / 2 - lo) (by omega) lo ((lo + hi) / 2) rfl
            (by omega) (by omega) hl
            (by
              intro i hi' hle
              exact Int.le_trans hx (mono _ i hm hi' hle))
          obtain ⟨a, b, c, d⟩ := this
          exact ⟨a, by omega, c, d⟩
      · rename_i hm
        exfalso
        omega
    · rename_i hlt
      refine ⟨Nat.le_refl _, by omega, hl, ?_⟩
      intro i h hle
      exact hh i h (by omega)

theorem lowerBound_le : ∀ (xs : Array Int) (x : Int), lowerBound xs x ≤ xs.size := by
  intro xs x
  have key : ∀ n lo hi, hi - lo = n → lo ≤ hi → hi ≤ xs.size →
      lbAux xs x lo hi ≤ hi := by
    intro n
    induction n using Nat.strongRecOn with
    | ind n ih =>
      intro lo hi hn h1 h2
      rw [lbAux]
      split
      · rename_i hlt
        split
        · rename_i hm
          split
          · exact ih (hi - ((lo + hi) / 2 + 1)) (by omega) _ _ rfl (by omega) h2
          · have := ih ((lo + hi) / 2 - lo) (by omega) lo ((lo + hi) / 2) rfl
              (by omega) (by omega)
            omega
        · omega
      · omega
  exact key _ 0 xs.size rfl (by omega) (Nat.le_refl _)

theorem lowerBound_spec : ∀ (xs : Array Int) (x : Int), xs.toList.Pairwise (· ≤ ·) →
    (∀ i (h : i < xs.size), i < lowerBound xs x → xs[i] < x) ∧
    (∀ i (h : i < xs.size), lowerBound xs x ≤ i → x ≤ xs[i]) := by
  intro xs x hs
  have := lbAux_spec xs x hs _ 0 xs.size rfl (by omega) (Nat.le_refl _)
    (by intro i h hlt; omega) (by intro i h hle; omega)
  exact ⟨this.2.2.1, this.2.2.2⟩
```

## gcd

```
    theorem gcd'_dvd : ∀ a b : Nat, gcd' a b ∣ a ∧ gcd' a b ∣ b
    theorem gcd'_greatest : ∀ a b d : Nat, d ∣ a → d ∣ b → d ∣ gcd' a b
```

### attempt 1: errors (Lean 2.4 s)

```lean
def gcd' (a b : Nat) : Nat :=
  if h : b = 0 then a else gcd' b (a % b)
termination_by b
decreasing_by exact Nat.mod_lt _ (Nat.pos_of_ne_zero h)

theorem gcd'_zero (a : Nat) : gcd' a 0 = a := by
  rw [gcd', dif_pos rfl]

theorem gcd'_step (a b : Nat) (h : b ≠ 0) : gcd' a b = gcd' b (a % b) := by
  rw [gcd', dif_neg h]

theorem gcd'_dvd : ∀ a b : Nat, gcd' a b ∣ a ∧ gcd' a b ∣ b := by
  intro a b
  induction b using Nat.strongRecOn generalizing a with
  | ind b ih =>
    by_cases h : b = 0
    · subst h
      rw [gcd'_zero]
      exact ⟨Nat.dvd_refl _, Nat.dvd_zero _⟩
    · rw [gcd'_step a b h]
      obtain ⟨h1, h2⟩ := ih (a % b) (Nat.mod_lt _ (Nat.pos_of_ne_zero h)) b
      refine ⟨?_, h1⟩
      have h3 := Nat.dvd_add (Dvd.dvd.mul_right h1 (a / b)) h2
      rw [Nat.div_add_mod] at h3
      exact h3

theorem gcd'_greatest : ∀ a b d : Nat, d ∣ a → d ∣ b → d ∣ gcd' a b := by
  intro a b d
  induction b using Nat.strongRecOn generalizing a with
  | ind b ih =>
    intro ha hb
    by_cases h : b = 0
    · subst h
      rw [gcd'_zero]
      exact ha
    · rw [gcd'_step a b h]
      exact ih (a % b) (Nat.mod_lt _ (Nat.pos_of_ne_zero h)) b hb
        ((Nat.dvd_mod_iff hb).mpr ha)
```

Sent back:
```
line 23:30: error: Unknown constant `Dvd.dvd.mul_right`
`gcd'_dvd` depends on ['sorryAx'] (sorry, an axiom or native_decide)
```

### attempt 2: ok (Lean 3.3 s)

```lean
def gcd' (a b : Nat) : Nat :=
  if h : b = 0 then a else gcd' b (a % b)
termination_by b
decreasing_by exact Nat.mod_lt _ (Nat.pos_of_ne_zero h)

theorem gcd'_zero (a : Nat) : gcd' a 0 = a := by
  rw [gcd', dif_pos rfl]

theorem gcd'_step (a b : Nat) (h : b ≠ 0) : gcd' a b = gcd' b (a % b) := by
  rw [gcd', dif_neg h]

theorem gcd'_dvd : ∀ a b : Nat, gcd' a b ∣ a ∧ gcd' a b ∣ b := by
  intro a b
  induction b using Nat.strongRecOn generalizing a with
  | ind b ih =>
    by_cases h : b = 0
    · subst h
      rw [gcd'_zero]
      exact ⟨Nat.dvd_refl _, Nat.dvd_zero _⟩
    · rw [gcd'_step a b h]
      obtain ⟨h1, h2⟩ := ih (a % b) (Nat.mod_lt _ (Nat.pos_of_ne_zero h)) b
      refine ⟨?_, h1⟩
      have h3 := Nat.dvd_add (Nat.dvd_mul_right_of_dvd h1 (a / b)) h2
      rw [Nat.div_add_mod] at h3
      exact h3

theorem gcd'_greatest : ∀ a b d : Nat, d ∣ a → d ∣ b → d ∣ gcd' a b := by
  intro a b d
  induction b using Nat.strongRecOn generalizing a with
  | ind b ih =>
    intro ha hb
    by_cases h : b = 0
    · subst h
      rw [gcd'_zero]
      exact ha
    · rw [gcd'_step a b h]
      exact ih (a % b) (Nat.mod_lt _ (Nat.pos_of_ne_zero h)) b hb
        ((Nat.dvd_mod_iff hb).mpr ha)
```

## rle

```
    theorem decode_encode : ∀ xs : List Int, decode (encode xs) = xs
    theorem encode_counts_pos : ∀ xs : List Int, ∀ p ∈ encode xs, 0 < p.2
```

### attempt 1: ok (Lean 2.3 s)

```lean
def encode : List Int → List (Int × Nat)
  | [] => []
  | x :: xs =>
    match encode xs with
    | [] => [(x, 1)]
    | (y, n) :: rest =>
      if x = y then (y, n + 1) :: rest else (x, 1) :: (y, n) :: rest

def decode : List (Int × Nat) → List Int
  | [] => []
  | (x, n) :: ps => List.replicate n x ++ decode ps

theorem decode_encode : ∀ xs : List Int, decode (encode xs) = xs := by
  intro xs
  induction xs with
  | nil => simp [encode, decode]
  | cons x xs ih =>
    simp only [encode]
    split
    · rename_i h
      rw [h] at ih
      simp [decode] at ih
      subst ih
      simp [decode]
    · rename_i y n rest h
      rw [h] at ih
      split
      · rename_i hxy
        subst hxy
        simp only [decode] at ih ⊢
        rw [List.replicate_succ, List.cons_append, ih]
      · rename_i hxy
        simp only [decode] at ih ⊢
        rw [ih]
        simp

theorem encode_counts_pos : ∀ xs : List Int, ∀ p ∈ encode xs, 0 < p.2 := by
  intro xs
  induction xs with
  | nil => simp [encode]
  | cons x xs ih =>
    simp only [encode]
    split
    · intro p hp
      simp at hp
      subst hp
      simp
    · rename_i y n rest h
      rw [h] at ih
      split
      · intro p hp
        simp at hp
        rcases hp with rfl | hp
        · simp
        · exact ih p (List.mem_cons_of_mem _ hp)
      · intro p hp
        simp at hp
        rcases hp with rfl | rfl | hp
        · simp
        · exact ih _ (by simp)
        · exact ih p (List.mem_cons_of_mem _ hp)
```
