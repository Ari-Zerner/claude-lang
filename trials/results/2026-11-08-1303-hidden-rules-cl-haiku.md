# Hidden-input trial 2026-11-08-1303 (rules tasks, cl, haiku)

| task | shown example | ok | wrong | error | verdict | lines | examples |
|---|---|---|---|---|---|---|---|
| parking_fee | first try | 13 | 0 | 0 | all ok | 32 | 16 |
| add_days | after fix | 11 | 0 | 0 | all ok | 86 | 23 |
| tax | first try | 11 | 0 | 0 | all ok | 38 | 10 |
| rank | first try | 8 | 0 | 0 | all ok | 31 | 6 |
| darts | first try | 9 | 0 | 0 | all ok | 33 | 8 |
| elevator | first try | 8 | 0 | 0 | all ok | 83 | 17 |
| runoff | first try | 8 | 0 | 0 | all ok | 50 | 6 |
| vending | first try | 9 | 0 | 0 | all ok | 29 | 7 |

Totals over hidden inputs: {'ok': 77, 'wrong': 0, 'error': 0}. Programs with a wrong answer: 0 of 8.

## parking_fee

`fn parking_fee(minutes: Int) -> Int`

### attempt 1: shown example OK

```cl
fn hourly_charge(minutes: Int) -> Int
  example hourly_charge(minutes: 0) == 0
  example hourly_charge(minutes: 15) == 0
  example hourly_charge(minutes: 16) == 3
  example hourly_charge(minutes: 60) == 3
  example hourly_charge(minutes: 61) == 6
  example hourly_charge(minutes: 100) == 6
  example hourly_charge(minutes: 1439) == 20
  if minutes <= 15
    return 0
  end if
  var hours = (minutes + 59) / 60
  var fee = 3 * hours
  if fee > 20
    return 20
  end if
  return fee
end fn hourly_charge

fn parking_fee(minutes: Int) -> Int
  example parking_fee(minutes: 100) == 6
  example parking_fee(minutes: 0) == 0
  example parking_fee(minutes: 15) == 0
  example parking_fee(minutes: 16) == 3
  example parking_fee(minutes: 1440) == 20
  example parking_fee(minutes: 1456) == 23
  example parking_fee(minutes: 2880) == 40
  example parking_fee(minutes: 2895) == 40
  example parking_fee(minutes: 1439) == 20
  var days = minutes / 1440
  var rest = minutes % 1440
  return 20 * days + hourly_charge(minutes: rest)
end fn parking_fee
```

Hidden inputs: 13 ok, 0 wrong, 0 error

## add_days

`fn add_days(year: Int, month: Int, day: Int, days: Int) -> List[Int]`

### attempt 1: build-fail

```cl
fn floor_div(a: Int, b: Int) -> Int
  example floor_div(a: 7, b: 2) == 3
  example floor_div(a: -7, b: 2) == -4
  example floor_div(a: -6, b: 2) == -3
  var q = a / b
  if a % b < 0
    q = q - 1
  end if
  return q
end fn floor_div

fn is_leap(year: Int) -> Bool
  example is_leap(2000) == true
  example is_leap(1900) == false
  example is_leap(2024) == true
  example is_leap(2023) == false
  return (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
end fn is_leap

fn days_in_year(year: Int) -> Int
  example days_in_year(2024) == 366
  example days_in_year(1900) == 365
  if is_leap(year)
    return 366
  else
    return 365
  end if
end fn days_in_year

fn days_in_month(year: Int, month: Int) -> Int
  example days_in_month(year: 2024, month: 2) == 29
  example days_in_month(year: 2023, month: 2) == 28
  example days_in_month(year: 2023, month: 4) == 30
  example days_in_month(year: 2023, month: 12) == 31
  if month == 2
    if is_leap(year)
      return 29
    else
      return 28
    end if
  else if month == 4 or month == 6 or month == 9 or month == 11
    return 30
  else
    return 31
  end if
end fn days_in_month

fn days_before_month(year: Int, month: Int) -> Int
  example days_before_month(year: 2024, month: 3) == 60
  example days_before_month(year: 2023, month: 1) == 0
  var total = 0
  for k in 1 until month
    total = total + days_in_month(year: year, month: k)
  end for
  return total
end fn days_before_month

# Days from 0001-01-01 (day 0) to the given date. Requires year >= 1.
fn days_from_civil(year: Int, month: Int, day: Int) -> Int
  example days_from_civil(year: 1, month: 1, day: 1) == 0
  example days_from_civil(year: 1970, month: 1, day: 1) == 719162
  let y1 = year - 1
  let whole_years = 365 * y1 + y1 / 4 - y1 / 100 + y1 / 400
  return whole_years + days_before_month(year: year, month: month) + (day - 1)
end fn days_from_civil

fn add_days(year: Int, month: Int, day: Int, days: Int) -> List[Int]
  example add_days(year: 2024, month: 2, day: 28, days: 2) == [2024, 3, 1]
  example add_days(year: 2024, month: 3, day: 1, days: -1) == [2024, 2, 29]
  example add_days(year: 2023, month: 12, day: 31, days: 1) == [2024, 1, 1]
  example add_days(year: 2000, month: 1, day: 1, days: 0) == [2000, 1, 1]
  example add_days(year: 1, month: 1, day: 1, days: 146097) == [401, 1, 1]
  example add_days(year: 1, month: 1, day: 1, days: -146097) == [1, 1, 1]
  let start = days_from_civil(year: year, month: month, day: day)
  # Split off whole 400-year cycles so that large values of days cannot overflow.
  let cycles = floor_div(a: days, b: 146097)
  let offset = days - cycles * 146097
  let total = start + offset
  let extra = floor_div(a: total, b: 146097)
  let leftover = total - extra * 146097
  let base = 1 + 400 * (cycles + extra)
  var yr = base
  var rest = leftover
  while rest >= days_in_year(yr)
    rest = rest - days_in_year(yr)
    yr = yr + 1
  end while
  var mon = 1
  while rest >= days_in_month(year: yr, month: mon)
    rest = rest - days_in_month(year: yr, month: mon)
    mon = mon + 1
  end while
  return [yr, mon, rest + 1]
end fn add_days
```

Diagnostics sent back:
```
prog.cl:73:3: error[example-failed]: example is false: `add_days(year: 1, month: 1, day: 1, days: -146097)` is [-399, 1, 1], expected [1, 1, 1]
   73 |   example add_days(year: 1, month: 1, day: 1, days: -146097) == [1, 1, 1]
      |   ^^^^^^^
1 error(s), 0 warning(s)
```

### attempt 2: shown example OK

```cl
fn floor_div(a: Int, b: Int) -> Int
  example floor_div(a: 7, b: 2) == 3
  example floor_div(a: -7, b: 2) == -4
  example floor_div(a: -6, b: 2) == -3
  var q = a / b
  if a % b < 0
    q = q - 1
  end if
  return q
end fn floor_div

fn is_leap(year: Int) -> Bool
  example is_leap(2000) == true
  example is_leap(1900) == false
  example is_leap(2024) == true
  example is_leap(2023) == false
  return (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
end fn is_leap

fn days_in_year(year: Int) -> Int
  example days_in_year(2024) == 366
  example days_in_year(1900) == 365
  if is_leap(year)
    return 366
  else
    return 365
  end if
end fn days_in_year

fn days_in_month(year: Int, month: Int) -> Int
  example days_in_month(year: 2024, month: 2) == 29
  example days_in_month(year: 2023, month: 2) == 28
  example days_in_month(year: 2023, month: 4) == 30
  example days_in_month(year: 2023, month: 12) == 31
  if month == 2
    if is_leap(year)
      return 29
    else
      return 28
    end if
  else if month == 4 or month == 6 or month == 9 or month == 11
    return 30
  else
    return 31
  end if
end fn days_in_month

fn days_before_month(year: Int, month: Int) -> Int
  example days_before_month(year: 2024, month: 3) == 60
  example days_before_month(year: 2023, month: 1) == 0
  var total = 0
  for k in 1 until month
    total = total + days_in_month(year: year, month: k)
  end for
  return total
end fn days_before_month

# Days from 0001-01-01 (day 0) to the given date. Requires year >= 1.
fn days_from_civil(year: Int, month: Int, day: Int) -> Int
  example days_from_civil(year: 1, month: 1, day: 1) == 0
  example days_from_civil(year: 1970, month: 1, day: 1) == 719162
  let y1 = year - 1
  let whole_years = 365 * y1 + y1 / 4 - y1 / 100 + y1 / 400
  return whole_years + days_before_month(year: year, month: month) + (day - 1)
end fn days_from_civil

fn add_days(year: Int, month: Int, day: Int, days: Int) -> List[Int]
  example add_days(year: 2024, month: 2, day: 28, days: 2) == [2024, 3, 1]
  example add_days(year: 2024, month: 3, day: 1, days: -1) == [2024, 2, 29]
  example add_days(year: 2023, month: 12, day: 31, days: 1) == [2024, 1, 1]
  example add_days(year: 2000, month: 1, day: 1, days: 0) == [2000, 1, 1]
  example add_days(year: 1, month: 1, day: 1, days: 146097) == [401, 1, 1]
  example add_days(year: 401, month: 1, day: 1, days: -146097) == [1, 1, 1]
  let start = days_from_civil(year: year, month: month, day: day)
  # Split off whole 400-year cycles so that large values of days cannot overflow.
  let cycles = floor_div(a: days, b: 146097)
  let offset = days - cycles * 146097
  let total = start + offset
  let extra = floor_div(a: total, b: 146097)
  let leftover = total - extra * 146097
  let base = 1 + 400 * (cycles + extra)
  var yr = base
  var rest = leftover
  while rest >= days_in_year(yr)
    rest = rest - days_in_year(yr)
    yr = yr + 1
  end while
  var mon = 1
  while rest >= days_in_month(year: yr, month: mon)
    rest = rest - days_in_month(year: yr, month: mon)
    mon = mon + 1
  end while
  return [yr, mon, rest + 1]
end fn add_days
```

Hidden inputs: 11 ok, 0 wrong, 0 error

## tax

`fn tax(income: Int) -> Int`

### attempt 1: shown example OK

```cl
fn share(amount: Int, pct: Int) -> Int
  example share(amount: 30000, pct: 10) == 3000
  example share(amount: 10000, pct: 25) == 2500
  example share(amount: 99, pct: 10) == 9
  example share(amount: 0, pct: 40) == 0
  return (amount / 100) * pct + ((amount % 100) * pct) / 100
end fn share

fn tax(income: Int) -> Int
  example tax(income: 50000) == 5000
  example tax(income: 0) == 0
  example tax(income: 10000) == 0
  example tax(income: 20000) == 500
  example tax(income: 100000) == 17500
  example tax(income: 200000) == 57500
  var t = 0
  if income > 10000
    var top1 = income
    if income > 40000
      top1 = 40000
    end if
    t = t + share(amount: top1 - 10000, pct: 10)
  end if
  if income > 40000
    var top2 = income
    if income > 100000
      top2 = 100000
    end if
    t = t + share(amount: top2 - 40000, pct: 25)
  end if
  if income > 100000
    t = t + share(amount: income - 100000, pct: 40)
  end if
  t = t - 500
  if t < 0
    return 0
  end if
  return t
end fn tax
```

Hidden inputs: 11 ok, 0 wrong, 0 error

## rank

`fn rank(scores: List[Int], attempts: List[Int]) -> List[Int]`

### attempt 1: shown example OK

```cl
fn ranks_before(i: Int, j: Int, scores: List[Int], attempts: List[Int]) -> Bool
  example ranks_before(i: 0, j: 1, scores: [3, 5], attempts: [1, 1]) == false
  example ranks_before(i: 1, j: 0, scores: [3, 5], attempts: [1, 1]) == true
  example ranks_before(i: 0, j: 1, scores: [5, 5], attempts: [2, 1]) == false
  example ranks_before(i: 0, j: 1, scores: [5, 5], attempts: [1, 2]) == true
  if scores[i] != scores[j]
    return scores[i] > scores[j]
  end if
  if attempts[i] != attempts[j]
    return attempts[i] < attempts[j]
  end if
  return i < j
end fn ranks_before

fn rank(scores: List[Int], attempts: List[Int]) -> List[Int]
  example rank(scores: [3, 5, 5, 1], attempts: [2, 3, 1, 0]) == [2, 1, 0, 3]
  example rank(scores: [], attempts: []) == []
  var order: List[Int] = []
  for i in 0 until length(scores)
    order = append(list: order, item: i)
  end for
  for k in 1 until length(order)
    var j = k
    while j > 0 and ranks_before(i: order[j], j: order[j - 1], scores: scores, attempts: attempts)
      var tmp = order[j]
      order[j] = order[j - 1]
      order[j - 1] = tmp
      j = j - 1
    end while
  end for
  return order
end fn rank
```

Hidden inputs: 8 ok, 0 wrong, 0 error

## darts

`fn darts(start: Int, throws: List[Int]) -> Int`

### attempt 1: shown example OK

```cl
fn darts(start: Int, throws: List[Int]) -> Int
  example darts(start: 50, throws: [20, 20, 5, 3, 1, 1]) == 5
  example darts(start: 2, throws: []) == 2
  example darts(start: 10, throws: [10]) == 0
  example darts(start: 10, throws: [4, 6, 3]) == 0
  example darts(start: 10, throws: [7, 5]) == 10
  example darts(start: 10, throws: [5, 4, 1]) == 10
  example darts(start: 20, throws: [5, 5, 5, 9, 9, 1, 3]) == 2
  example darts(start: 5, throws: [0, 0, 0]) == 5
  var score = start
  var n = 0
  while n < length(throws) and score > 0
    var turnStart = score
    var turnEnd = n + 3
    if turnEnd > length(throws)
      turnEnd = length(throws)
    end if
    var busted = false
    var k = n
    while k < turnEnd and score > 0 and not busted
      var left = score - throws[k]
      if left < 0 or left == 1
        score = turnStart
        busted = true
      else
        score = left
      end if
      k = k + 1
    end while
    n = turnEnd
  end while
  return score
end fn darts
```

Hidden inputs: 9 ok, 0 wrong, 0 error

## elevator

`fn elevator(start: Int, requests: List[Int]) -> List[Int]`

### attempt 1: shown example OK

```cl
fn contains_floor(xs: List[Int], x: Int) -> Bool
  example contains_floor(xs: [1, 2], x: 2) == true
  example contains_floor(xs: [], x: 2) == false
  for v in xs
    if v == x
      return true
    end if
  end for
  return false
end fn contains_floor

fn insert_sorted(ys: List[Int], x: Int) -> List[Int]
  example insert_sorted(ys: [1, 3], x: 2) == [1, 2, 3]
  example insert_sorted(ys: [1, 3], x: 3) == [1, 3]
  example insert_sorted(ys: [], x: 5) == [5]
  var out: List[Int] = []
  var placed = false
  for y in ys
    if (not placed) and (x <= y)
      if x < y
        out = append(list: out, item: x)
      end if
      placed = true
    end if
    out = append(list: out, item: y)
  end for
  if not placed
    out = append(list: out, item: x)
  end if
  return out
end fn insert_sorted

fn sort_unique(xs: List[Int]) -> List[Int]
  example length(sort_unique(xs: [3, 1, 3, 2])) == 3
  example sort_unique(xs: [3, 1, 3, 2]) == [1, 2, 3]
  example length(sort_unique(xs: [])) == 0
  var out: List[Int] = []
  for x in xs
    out = insert_sorted(ys: out, x: x)
  end for
  return out
end fn sort_unique

fn floors_above(xs: List[Int], start: Int) -> List[Int]
  example floors_above(xs: [1, 4, 6], start: 4) == [6]
  example floors_above(xs: [], start: 4) == []
  var out: List[Int] = []
  for x in xs
    if x > start
      out = append(list: out, item: x)
    end if
  end for
  return out
end fn floors_above

fn floors_below(xs: List[Int], start: Int) -> List[Int]
  example floors_below(xs: [1, 4, 6], start: 4) == [1]
  example floors_below(xs: [-2, 1, 3], start: 2) == [1, -2]
  var out: List[Int] = []
  for x in xs reversed
    if x < start
      out = append(list: out, item: x)
    end if
  end for
  return out
end fn floors_below

fn elevator(start: Int, requests: List[Int]) -> List[Int]
  example elevator(start: 5, requests: [7, 2, 9, 3]) == [7, 9, 3, 2]
  example elevator(start: 5, requests: [5, 5, 7]) == [5, 7]
  example elevator(start: 5, requests: [5]) == [5]
  example elevator(start: 0, requests: [-2, 3, -2, 1]) == [1, 3, -2]
  example length(elevator(start: 0, requests: [])) == 0
  let floors = sort_unique(xs: requests)
  let up = floors_above(xs: floors, start: start)
  let down = floors_below(xs: floors, start: start)
  var out: List[Int] = []
  if contains_floor(xs: floors, x: start)
    out = append(list: out, item: start)
  end if
  for f in up
    out = append(list: out, item: f)
  end for
  for f in down
    out = append(list: out, item: f)
  end for
  return out
end fn elevator
```

Hidden inputs: 8 ok, 0 wrong, 0 error

## runoff

`fn runoff(candidates: Int, ballots: List[List[Int]]) -> Int`

### attempt 1: shown example OK

```cl
fn first_active(active: List[Bool]) -> Int
  example first_active(active: [false, true, true]) == 1
  example first_active(active: [true]) == 0
  for i in 0 until length(active)
    if active[i]
      return i
    end if
  end for
  return 0
end fn first_active

fn runoff(candidates: Int, ballots: List[List[Int]]) -> Int
  example runoff(candidates: 3, ballots: [[0, 1], [1], [2, 1], [0], [1, 0]]) == 1
  example runoff(candidates: 1, ballots: []) == 0
  example runoff(candidates: 2, ballots: [[1], [0], [0]]) == 0
  example runoff(candidates: 3, ballots: [[0], [1], [2]]) == 0
  var active = repeat(item: true, times: candidates)
  var left = candidates
  while left > 1
    var votes = repeat(item: 0, times: candidates)
    var counted = 0
    for ballot in ballots
      var chosen = -1
      for c in ballot
        if chosen == -1 and active[c]
          chosen = c
        end if
      end for
      if chosen != -1
        votes[chosen] = votes[chosen] + 1
        counted = counted + 1
      end if
    end for
    for cand in 0 until candidates
      if active[cand] and votes[cand] * 2 > counted
        return cand
      end if
    end for
    var out = -1
    var fewest = 0
    for cand2 in 0 until candidates
      if active[cand2] and (out == -1 or votes[cand2] <= fewest)
        out = cand2
        fewest = votes[cand2]
      end if
    end for
    active[out] = false
    left = left - 1
  end while
  return first_active(active: active)
end fn runoff
```

Hidden inputs: 8 ok, 0 wrong, 0 error

## vending

`fn vending(amount: Int, coins: List[Int]) -> Option[List[Int]]`

### attempt 1: shown example OK

```cl
fn take_coins(amount: Int, value: Int, supply: Int) -> Int
  example take_coins(amount: 67, value: 25, supply: 2) == 2
  example take_coins(amount: 0, value: 10, supply: 5) == 0
  example take_coins(amount: 30, value: 10, supply: 1) == 1
  let n = amount / value
  if n > supply
    return supply
  end if
  return n
end fn take_coins

fn vending(amount: Int, coins: List[Int]) -> Option[List[Int]]
  example vending(amount: 67, coins: [2, 1, 3, 10]) == Some([2, 1, 1, 2])
  example vending(amount: 0, coins: [0, 0, 0, 0]) == Some([0, 0, 0, 0])
  example vending(amount: 3, coins: [0, 0, 0, 10]) == Some([0, 0, 0, 3])
  example vending(amount: 4, coins: [0, 0, 0, 3]) == None
  var rest = amount
  let a = take_coins(amount: rest, value: 25, supply: coins[0])
  rest = rest - a * 25
  let b = take_coins(amount: rest, value: 10, supply: coins[1])
  rest = rest - b * 10
  let c = take_coins(amount: rest, value: 5, supply: coins[2])
  rest = rest - c * 5
  let d = take_coins(amount: rest, value: 1, supply: coins[3])
  rest = rest - d
  if rest > 0
    return None
  end if
  return Some([a, b, c, d])
end fn vending
```

Hidden inputs: 9 ok, 0 wrong, 0 error
