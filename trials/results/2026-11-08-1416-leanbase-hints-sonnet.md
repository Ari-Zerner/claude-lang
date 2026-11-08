# Lean-direct baseline 2026-11-08-1416 (sonnet)

| task | result | lines | Lean s per attempt |
|---|---|---|---|
| isqrt | first try | 35 | [7.4] |

## isqrt

```
    theorem isqrt_spec : ∀ n : Nat, isqrt n * isqrt n ≤ n ∧ n < (isqrt n + 1) * (isqrt n + 1)
```

### attempt 1: ok (Lean 7.4 s)

```lean
def isqrt (n : Nat) : Nat :=
  if n < 2 then n
  else
    if (2 * isqrt (n / 4) + 1) * (2 * isqrt (n / 4) + 1) ≤ n then
      2 * isqrt (n / 4) + 1
    else
      2 * isqrt (n / 4)
decreasing_by omega

theorem isqrt_spec : ∀ n : Nat, isqrt n * isqrt n ≤ n ∧ n < (isqrt n + 1) * (isqrt n + 1) := by
  intro n
  induction n using Nat.strongRecOn with
  | ind n ih =>
    rw [isqrt]
    by_cases hn : n < 2
    · rw [if_pos hn]
      have : n = 0 ∨ n = 1 := by omega
      rcases this with rfl | rfl <;> decide
    · rw [if_neg hn]
      have ih' := ih (n / 4) (by omega)
      generalize isqrt (n / 4) = s at ih' ⊢
      obtain ⟨h1, h2⟩ := ih'
      have e1 : (s + 1) * (s + 1) = s * s + 2 * s + 1 := by grind
      have e2 : (2 * s + 1) * (2 * s + 1) = 4 * (s * s) + 4 * s + 1 := by grind
      have e3 : (2 * s) * (2 * s) = 4 * (s * s) := by grind
      have e4 : (2 * s + 1 + 1) * (2 * s + 1 + 1) = 4 * (s * s) + 8 * s + 4 := by grind
      have e5 : (2 * s + 1) * (2 * s + 1) = 4 * (s * s) + 4 * s + 1 := e2
      by_cases hc : (2 * s + 1) * (2 * s + 1) ≤ n
      · rw [if_pos hc]
        constructor
        · exact hc
        · omega
      · rw [if_neg hc]
        constructor
        · omega
        · omega
```
