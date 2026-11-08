# Hidden-input trial 2026-11-08-1306 (rules tasks, py, haiku)

| task | shown example | ok | wrong | error | verdict | lines | examples |
|---|---|---|---|---|---|---|---|
| parking_fee | first try | 13 | 0 | 0 | all ok | 60 | 22 |
| add_days | first try | 11 | 0 | 0 | all ok | 92 | 22 |
| tax | first try | 11 | 0 | 0 | all ok | 41 | 10 |
| rank | first try | 8 | 0 | 0 | all ok | 12 | 4 |
| darts | first try | 9 | 0 | 0 | all ok | 41 | 9 |
| elevator | first try | 8 | 0 | 0 | all ok | 28 | 6 |
| runoff | after fix | 8 | 0 | 0 | all ok | 34 | 6 |
| vending | after fix | 9 | 0 | 0 | all ok | 27 | 6 |

Totals over hidden inputs: {'ok': 77, 'wrong': 0, 'error': 0}. Programs with a wrong answer: 0 of 8.

## parking_fee

`def parking_fee(minutes: int) -> int`

### attempt 1: shown example OK

```python
def _short_stay_fee(minutes: int) -> int:
    """Fee for a stay shorter than one day (0 <= minutes < 1440).

    >>> _short_stay_fee(0)
    0
    >>> _short_stay_fee(15)
    0
    >>> _short_stay_fee(16)
    3
    >>> _short_stay_fee(60)
    3
    >>> _short_stay_fee(61)
    6
    >>> _short_stay_fee(360)
    18
    >>> _short_stay_fee(361)
    20
    >>> _short_stay_fee(1439)
    20
    """
    if minutes <= 15:
        return 0
    hours = (minutes + 59) // 60  # hours, counting any part of an hour as a full hour
    return min(3 * hours, 20)


def parking_fee(minutes: int) -> int:
    """Return the car park charge for a stay of `minutes` minutes.

    >>> parking_fee(minutes=0)
    0
    >>> parking_fee(minutes=15)
    0
    >>> parking_fee(minutes=16)
    3
    >>> parking_fee(minutes=100)
    6
    >>> parking_fee(minutes=360)
    18
    >>> parking_fee(minutes=361)
    20
    >>> parking_fee(minutes=1439)
    20
    >>> parking_fee(minutes=1440)
    20
    >>> parking_fee(minutes=1441)
    20
    >>> parking_fee(minutes=1440 + 100)
    26
    >>> parking_fee(minutes=2 * 1440)
    40
    >>> parking_fee(minutes=2 * 1440 + 15)
    40
    >>> parking_fee(minutes=2 * 1440 + 16)
    43
    >>> parking_fee(minutes=-1)
    Traceback (most recent call last):
        ...
    ValueError: minutes must be 0 or more
    """
    if minutes < 0:
        raise ValueError("minutes must be 0 or more")
    days, remainder = divmod(minutes, 1440)
    return 20 * days + _short_stay_fee(remainder)
```

Hidden inputs: 13 ok, 0 wrong, 0 error

## add_days

`def add_days(year: int, month: int, day: int, days: int) -> list[int]`

### attempt 1: shown example OK

```python
def is_leap_year(year: int) -> bool:
    """Return True if year is a leap year in the proleptic Gregorian calendar.

    >>> is_leap_year(2024)
    True
    >>> is_leap_year(1900)
    False
    >>> is_leap_year(2000)
    True
    """
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def days_in_month(year: int, month: int) -> int:
    """Return the number of days in the given month.

    >>> days_in_month(2024, 2)
    29
    >>> days_in_month(2023, 2)
    28
    >>> days_in_month(2023, 4)
    30
    >>> days_in_month(2023, 12)
    31
    """
    if month == 2:
        return 29 if is_leap_year(year) else 28
    if month in (4, 6, 9, 11):
        return 30
    return 31


def days_before_year(year: int) -> int:
    """Return the number of days from 0001-01-01 up to January 1 of year.

    Day 0 is 0001-01-01. Negative results cover years before year 1,
    using the same proleptic rules.

    >>> days_before_year(1)
    0
    >>> days_before_year(2)
    365
    >>> days_before_year(0)
    -366
    """
    y = year - 1
    return y * 365 + y // 4 - y // 100 + y // 400


def date_to_ordinal(year: int, month: int, day: int) -> int:
    """Return the day number of a date, where 0001-01-01 is day 0.

    >>> date_to_ordinal(1, 1, 1)
    0
    >>> date_to_ordinal(1, 1, 2)
    1
    """
    ordinal = days_before_year(year)
    for m in range(1, month):
        ordinal += days_in_month(year, m)
    return ordinal + day - 1


def ordinal_to_date(ordinal: int) -> list[int]:
    """Convert a day number (0 is 0001-01-01) back to [year, month, day].

    >>> ordinal_to_date(0)
    [1, 1, 1]
    >>> ordinal_to_date(-1)
    [0, 12, 31]
    """
    year = (ordinal * 400) // 146097 + 1
    while days_before_year(year + 1) <= ordinal:
        year += 1
    while days_before_year(year) > ordinal:
        year -= 1

    remaining = ordinal - days_before_year(year)
    for month in range(1, 13):
        length = days_in_month(year, month)
        if remaining < length:
            return [year, month, remaining + 1]
        remaining -= length
    raise AssertionError("unreachable: day-of-year out of range")


def add_days(year: int, month: int, day: int, days: int) -> list[int]:
    """Return the date `days` days after (or before, if negative) the given date.

    The result is returned as [year, month, day] in the proleptic Gregorian
    calendar.

    >>> add_days(year=2024, month=2, day=28, days=2)
    [2024, 3, 1]
    >>> add_days(2023, 2, 28, 1)
    [2023, 3, 1]
    >>> add_days(2000, 12, 31, 1)
    [2001, 1, 1]
    >>> add_days(2024, 1, 1, 0)
    [2024, 1, 1]
    >>> add_days(1, 1, 1, -1)
    [0, 12, 31]
    >>> add_days(1900, 3, 1, -1)
    [1900, 2, 28]
    >>> add_days(2000, 3, 1, -1)
    [2000, 2, 29]
    >>> add_days(9000, 12, 31, 1)
    [9001, 1, 1]
    """
    ordinal = date_to_ordinal(year, month, day) + days
    return ordinal_to_date(ordinal)
```

Hidden inputs: 11 ok, 0 wrong, 0 error

## tax

`def tax(income: int) -> int`

### attempt 1: shown example OK

```python
def _band_tax(income: int, lower: int, upper: int | None, percent: int) -> int:
    """Return the tax on the part of income above `lower` and up to `upper`, rounded down.

    An upper of None means there is no upper limit.

    >>> _band_tax(50000, 10000, 40000, 10)
    3000
    >>> _band_tax(5000, 10000, 40000, 10)
    0
    >>> _band_tax(150, 100, None, 25)
    12
    """
    top = income if upper is None else min(income, upper)
    taxable = max(0, top - lower)
    return taxable * percent // 100


def tax(income: int) -> int:
    """Compute the tax on an income of 0 or more.

    The brackets are 0% up to 10000, 10% from 10000 to 40000, 25% from 40000
    to 100000, and 40% above 100000. Each bracket's tax is rounded down
    separately and the results are summed. A credit of 500 is then subtracted,
    and the result is never below 0.

    >>> tax(income=50000)
    5000
    >>> tax(0)
    0
    >>> tax(10000)
    0
    >>> tax(10500)
    0
    >>> tax(40000)
    2500
    >>> tax(100000)
    17500
    >>> tax(100003)
    17501
    """
    total = (
        _band_tax(income, 0, 10000, 0)
        + _band_tax(income, 10000, 40000, 10)
        + _band_tax(income, 40000, 100000, 25)
        + _band_tax(income, 100000, None, 40)
    )
    return max(0, total - 500)
```

Hidden inputs: 11 ok, 0 wrong, 0 error

## rank

`def rank(scores: list[int], attempts: list[int]) -> list[int]`

### attempt 1: shown example OK

```python
def rank(scores: list[int], attempts: list[int]) -> list[int]:
    """Return player indexes ordered by points (high to low), then attempts (low to high), then index (low to high).

    >>> rank(scores=[3, 5, 5, 1], attempts=[2, 3, 1, 0])
    [2, 1, 0, 3]
    >>> rank(scores=[], attempts=[])
    []
    >>> rank(scores=[4, 4, 4], attempts=[2, 1, 1])
    [1, 2, 0]
    >>> rank(scores=[-1, 0, -1], attempts=[0, 0, 0])
    [1, 0, 2]
    """
    return sorted(range(len(scores)), key=lambda i: (-scores[i], attempts[i], i))
```

Hidden inputs: 8 ok, 0 wrong, 0 error

## darts

`def darts(start: int, throws: list[int]) -> int`

### attempt 1: shown example OK

```python
def darts(start: int, throws: list[int]) -> int:
    """Return the final score of a darts game.

    The game starts at `start` points. Throws are grouped into turns of three.
    A throw that would leave the score below 0 or at exactly 1 is a bust: the
    score reverts to what it was at the start of that turn and the rest of that
    turn is skipped. Reaching exactly 0 ends the game and ignores later throws.

    >>> darts(start=50, throws=[20, 20, 5, 3, 1, 1])
    5
    >>> darts(10, [])
    10
    >>> darts(10, [10])
    0
    >>> darts(10, [9])
    10
    >>> darts(10, [5, 4, 0])
    10
    >>> darts(10, [1, 1, 1, 8, 2])
    7
    >>> darts(10, [0, 0, 0])
    10
    >>> darts(10, [4, 6, 3])
    0
    >>> darts(10, [10, 0, 0, 5, 5, 5])
    0
    """
    score = start
    for turn_begin in range(0, len(throws), 3):
        if score == 0:
            break
        turn_score = score
        for points in throws[turn_begin:turn_begin + 3]:
            new_score = score - points
            if new_score < 0 or new_score == 1:
                score = turn_score
                break
            score = new_score
            if score == 0:
                break
        if score == 0:
            break
    return score
```

Hidden inputs: 9 ok, 0 wrong, 0 error

## elevator

`def elevator(start: int, requests: list[int]) -> list[int]`

### attempt 1: shown example OK

```python
def elevator(start: int, requests: list[int]) -> list[int]:
    """
    Return the floors an elevator visits, in visiting order.

    The elevator starts at `start`. A requested start floor is visited first.
    It then goes up, stopping at each requested floor above it in ascending
    order, and then goes down, stopping at each requested floor below it in
    descending order. Duplicate requests are visited once.

    >>> elevator(start=5, requests=[7, 2, 9, 3])
    [7, 9, 3, 2]
    >>> elevator(5, [5, 8, 1])
    [5, 8, 1]
    >>> elevator(0, [])
    []
    >>> elevator(0, [-3, 4, -3, 2, 4])
    [2, 4, -3]
    >>> elevator(-2, [-5, -2, -1, -7])
    [-2, -1, -5, -7]
    >>> elevator(3, [3, 3, 3])
    [3]
    """
    floors = set(requests)
    visited: list[int] = []

    if start in floors:
        visited.append(start)
        floors.discard(start)

    up = sorted(floor for floor in floors if floor > start)
    down = sorted((floor for floor in floors if floor < start), reverse=True)

    return visited + up + down
```

Hidden inputs: 8 ok, 0 wrong, 0 error

## runoff

`def runoff(candidates: int, ballots: list[list[int]]) -> int`

### attempt 1: build-fail

```python
def runoff(candidates: int, ballots: list[list[int]]) -> int:
    """Return the winner of a ranked-choice runoff election.

    Candidates are numbered 0 to candidates - 1. Each ballot is a list of
    candidate numbers in order of preference; it may be empty or partial.

    >>> runoff(candidates=3, ballots=[[0, 1], [1], [2, 1], [0], [1, 0]])
    1
    >>> runoff(candidates=1, ballots=[])
    0
    >>> runoff(candidates=2, ballots=[])
    0
    >>> runoff(candidates=2, ballots=[[1], [1], [0]])
    1
    >>> runoff(candidates=3, ballots=[[0], [1], [2]])
    0
    >>> runoff(candidates=3, ballots=[[], [2], []])
    0
    """
    remaining = set(range(candidates))
    while True:
        if len(remaining) == 1:
            return next(iter(remaining))

        votes = {c: 0 for c in remaining}
        counting = 0
        for ballot in ballots:
            for c in ballot:
                if c in remaining:
                    votes[c] += 1
                    counting += 1
                    break

        for c in remaining:
            if 2 * votes[c] > counting:
                return c

        # Fewest votes loses; among ties, the highest-numbered candidate loses.
        loser = min(remaining, key=lambda c: (votes[c], -c))
        remaining.remove(loser)
```

Diagnostics sent back:
```
**********************************************************************
File "sol.py", line 17, in sol.runoff
Failed example:
    runoff(candidates=3, ballots=[[], [2], []])
Expected:
    0
Got:
    2
**********************************************************************
1 items had failures:
   1 of   6 in sol.runoff
***Test Failed*** 1 failures.
```

### attempt 2: shown example OK

```python
def runoff(candidates: int, ballots: list[list[int]]) -> int:
    """Return the winner of a ranked-choice runoff election.

    Candidates are numbered 0 to candidates - 1. Each ballot is a list of
    candidate numbers in order of preference; it may be empty or partial.

    >>> runoff(candidates=3, ballots=[[0, 1], [1], [2, 1], [0], [1, 0]])
    1
    >>> runoff(candidates=1, ballots=[])
    0
    >>> runoff(candidates=2, ballots=[])
    0
    >>> runoff(candidates=2, ballots=[[1], [1], [0]])
    1
    >>> runoff(candidates=3, ballots=[[0], [1], [2]])
    0
    >>> runoff(candidates=3, ballots=[[], [2], []])
    2
    """
    remaining = set(range(candidates))
    while True:
        if len(remaining) == 1:
            return next(iter(remaining))

        votes = {c: 0 for c in remaining}
        counting = 0
        for ballot in ballots:
            for c in ballot:
                if c in remaining:
                    votes[c] += 1
                    counting += 1
                    break

        for c in remaining:
            if 2 * votes[c] > counting:
                return c

        # Fewest votes loses; among ties, the highest-numbered candidate loses.
        loser = min(remaining, key=lambda c: (votes[c], -c))
        remaining.remove(loser)
```

Hidden inputs: 8 ok, 0 wrong, 0 error

## vending

`def vending(amount: int, coins: list[int]) -> list[int] | None`

### attempt 1: build-fail

```python
def vending(amount: int, coins: list[int]) -> list[int] | None:
    """Make change greedily from the largest coin value down.

    Coin values are 25, 10, 5 and 1. `coins` gives the machine's supply of
    each value in that order. Returns the number of each coin used, or None
    if the amount cannot be paid exactly with that greedy strategy.

    >>> vending(amount=67, coins=[2, 1, 3, 10])
    [2, 1, 1, 2]
    >>> vending(amount=0, coins=[0, 0, 0, 0])
    [0, 0, 0, 0]
    >>> vending(amount=30, coins=[0, 0, 0, 0]) is None
    True
    >>> vending(amount=30, coins=[1, 0, 0, 0]) is None
    True
    >>> vending(amount=30, coins=[0, 0, 0, 30])
    [0, 0, 0, 30]
    >>> vending(amount=40, coins=[1, 3, 0, 0])
    [1, 1, 0, 0]
    """
    remaining = amount
    used = []
    for value, supply in zip((25, 10, 5, 1), coins):
        count = min(remaining // value, max(supply, 0))
        used.append(count)
        remaining -= count * value
    if remaining != 0:
        return None
    return used
```

Diagnostics sent back:
```
**********************************************************************
File "sol.py", line 18, in sol.vending
Failed example:
    vending(amount=40, coins=[1, 3, 0, 0])
Expected:
    [1, 1, 0, 0]
Got nothing
**********************************************************************
1 items had failures:
   1 of   6 in sol.vending
***Test Failed*** 1 failures.
```

### attempt 2: shown example OK

```python
def vending(amount: int, coins: list[int]) -> list[int] | None:
    """Make change greedily from the largest coin value down.

    Coin values are 25, 10, 5 and 1. `coins` gives the machine's supply of
    each value in that order. Returns the number of each coin used, or None
    if the amount cannot be paid exactly with that greedy strategy.

    >>> vending(amount=67, coins=[2, 1, 3, 10])
    [2, 1, 1, 2]
    >>> vending(amount=0, coins=[0, 0, 0, 0])
    [0, 0, 0, 0]
    >>> vending(amount=30, coins=[0, 0, 0, 0]) is None
    True
    >>> vending(amount=30, coins=[1, 0, 0, 0]) is None
    True
    >>> vending(amount=30, coins=[0, 0, 0, 30])
    [0, 0, 0, 30]
    >>> vending(amount=40, coins=[1, 3, 0, 0]) is None
    True
    """
    remaining = amount
    used = []
    for value, supply in zip((25, 10, 5, 1), coins):
        count = min(remaining // value, max(supply, 0))
        used.append(count)
        remaining -= count * value
    if remaining != 0:
        return None
    return used
```

Hidden inputs: 9 ok, 0 wrong, 0 error
