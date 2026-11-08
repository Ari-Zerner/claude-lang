# Hidden-input trial 2026-11-08-1106 (py, haiku)

| task | shown example | ok | wrong | error | verdict | lines | examples |
|---|---|---|---|---|---|---|---|
| rotate | first try | 9 | 0 | 0 | all ok | 8 | 0 |
| second_largest | first try | 9 | 0 | 0 | all ok | 8 | 0 |
| spread | first try | 8 | 0 | 0 | all ok | 8 | 0 |
| window_sums | first try | 8 | 0 | 0 | all ok | 13 | 0 |
| merge_ranges | first try | 9 | 0 | 0 | all ok | 9 | 0 |
| first_at_least | first try | 8 | 0 | 0 | all ok | 9 | 0 |
| digit_sum | first try | 7 | 0 | 0 | all ok | 2 | 0 |
| run_lengths | first try | 6 | 0 | 0 | all ok | 8 | 0 |
| days_until_warmer | first try | 7 | 0 | 0 | all ok | 9 | 0 |
| balanced | first try | 9 | 0 | 0 | all ok | 14 | 0 |
| max_subarray | first try | 7 | 0 | 0 | all ok | 7 | 0 |
| median | first try | 7 | 0 | 0 | all ok | 7 | 0 |

Totals over hidden inputs: {'ok': 94, 'wrong': 0, 'error': 0}. Programs with a wrong answer: 0 of 12.

## rotate

`def rotate(xs: list[int], k: int) -> list[int]`

### attempt 1: shown example OK

```python
def rotate(xs: list[int], k: int) -> list[int]:
    n = len(xs)
    if n == 0:
        return []
    k %= n
    if k == 0:
        return list(xs)
    return xs[-k:] + xs[:-k]
```

Hidden inputs: 9 ok, 0 wrong, 0 error

## second_largest

`def second_largest(xs: list[int]) -> int | None`

### attempt 1: shown example OK

```python
def second_largest(xs: list[int]) -> int | None:
    if not xs:
        return None
    maximum = max(xs)
    candidates = [x for x in xs if x < maximum]
    if not candidates:
        return None
    return max(candidates)
```

Hidden inputs: 9 ok, 0 wrong, 0 error

## spread

`def spread(rows: int, cols: int, points: list[list[int]]) -> list[list[int]]`

### attempt 1: shown example OK

```python
def spread(rows: int, cols: int, points: list[list[int]]) -> list[list[int]]:
    grid = [[0] * cols for _ in range(rows)]
    for r, c in points:
        for dr, dc in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                grid[nr][nc] += 1
    return grid
```

Hidden inputs: 8 ok, 0 wrong, 0 error

## window_sums

`def window_sums(xs: list[int], k: int) -> list[int]`

### attempt 1: shown example OK

```python
from itertools import islice


def window_sums(xs: list[int], k: int) -> list[int]:
    if k < 1:
        raise ValueError("k must be at least 1")
    n = len(xs)
    if k > n:
        return []
    current = sum(xs[:k])
    result = [current]
    for i in range(k, n):
        current += xs[i] - xs[i - k]
        result.append(current)
    return result
```

Hidden inputs: 8 ok, 0 wrong, 0 error

## merge_ranges

`def merge_ranges(ranges: list[list[int]]) -> list[list[int]]`

### attempt 1: shown example OK

```python
def merge_ranges(ranges: list[list[int]]) -> list[list[int]]:
    merged: list[list[int]] = []
    for lo, hi in sorted((r[0], r[1]) for r in ranges):
        if merged and lo <= merged[-1][1]:
            if hi > merged[-1][1]:
                merged[-1][1] = hi
        else:
            merged.append([lo, hi])
    return merged
```

Hidden inputs: 9 ok, 0 wrong, 0 error

## first_at_least

`def first_at_least(xs: list[int], x: int) -> int`

### attempt 1: shown example OK

```python
def first_at_least(xs: list[int], x: int) -> int:
    lo, hi = 0, len(xs)
    while lo < hi:
        mid = (lo + hi) // 2
        if xs[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo
```

Hidden inputs: 8 ok, 0 wrong, 0 error

## digit_sum

`def digit_sum(n: int) -> int`

### attempt 1: shown example OK

```python
def digit_sum(n: int) -> int:
    return sum(int(d) for d in str(abs(n)))
```

Hidden inputs: 7 ok, 0 wrong, 0 error

## run_lengths

`def run_lengths(xs: list[int]) -> list[list[int]]`

### attempt 1: shown example OK

```python
def run_lengths(xs: list[int]) -> list[list[int]]:
    result: list[list[int]] = []
    for x in xs:
        if result and result[-1][0] == x:
            result[-1][1] += 1
        else:
            result.append([x, 1])
    return result
```

Hidden inputs: 6 ok, 0 wrong, 0 error

## days_until_warmer

`def days_until_warmer(temps: list[int]) -> list[int]`

### attempt 1: shown example OK

```python
def days_until_warmer(temps: list[int]) -> list[int]:
    result = [0] * len(temps)
    stack: list[int] = []  # indices of days still waiting for a warmer day

    for i, temp in enumerate(temps):
        while stack and temps[stack[-1]] < temp:
            j = stack.pop()
            result[j] = i - j
        stack.append(i)

    return result
```

Hidden inputs: 7 ok, 0 wrong, 0 error

## balanced

`def balanced(tokens: list[str]) -> bool`

### attempt 1: shown example OK

```python
def balanced(tokens: list[str]) -> bool:
    pairs = {')': '(', ']': '[', '}': '{'}
    openers = set(pairs.values())
    stack: list[str] = []
    for tok in tokens:
        if tok in openers:
            stack.append(tok)
        elif tok in pairs:
            if not stack or stack[-1] != pairs[tok]:
                return False
            stack.pop()
        else:
            return False
    return not stack
```

Hidden inputs: 9 ok, 0 wrong, 0 error

## max_subarray

`def max_subarray(xs: list[int]) -> int`

### attempt 1: shown example OK

```python
def max_subarray(xs: list[int]) -> int:
    best = current = xs[0]
    for x in xs[1:]:
        current = max(x, current + x)
        if current > best:
            best = current
    return best
```

Hidden inputs: 7 ok, 0 wrong, 0 error

## median

`def median(xs: list[int]) -> int`

### attempt 1: shown example OK

```python
def median(xs: list[int]) -> int:
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) // 2
```

Hidden inputs: 7 ok, 0 wrong, 0 error
