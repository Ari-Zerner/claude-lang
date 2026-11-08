"""Wrong-but-runs trial: the same function tasks in claude-lang and in Python, graded on hidden inputs.

First-try success on a task's own example can't tell the languages apart (models get both right).
This asks for one function per task, shows one example, lets each language have its usual one fix
round on that example (claude-lang: the compiler's diagnostics, including the program's own
`example` lines; Python: the example's output or traceback), and then runs the final code on
inputs the model never saw: edge cases and other values. Each hidden input is one of
  ok     the right answer
  wrong  a wrong answer, printed as if nothing were amiss (the bad outcome this is about)
  error  stopped: a trap, an exception, or a timeout
Usage: trial-like, e.g. `python3 trials/hidden.py --lang cl --model haiku`, `--lang py`;
`--selftest` checks the harness's literals and expected output against the real compiler.
"""
import argparse
import bisect
import datetime
import json
import os
import re
import signal
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CLC = os.path.join(ROOT, "clc.py")
sys.path.insert(0, HERE)
from trial import claude  # noqa: E402


# ---- references -------------------------------------------------------------------------------
def r_rotate(xs, k):
    if not xs:
        return []
    k %= len(xs)
    return xs[len(xs) - k:] + xs[:len(xs) - k]


def r_second_largest(xs):
    rest = [x for x in xs if x < max(xs)] if xs else []
    return max(rest) if rest else None


def r_spread(rows, cols, points):
    grid = [[0] * cols for _ in range(rows)]
    for r, c in points:
        for dr, dc in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            if 0 <= r + dr < rows and 0 <= c + dc < cols:
                grid[r + dr][c + dc] += 1
    return grid


def r_window_sums(xs, k):
    return [sum(xs[i:i + k]) for i in range(len(xs) - k + 1)]


def r_merge_ranges(ranges):
    out = []
    for lo, hi in sorted(ranges):
        if out and lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out


def r_digit_sum(n):
    return sum(int(d) for d in str(abs(n)))


def r_run_lengths(xs):
    out = []
    for x in xs:
        if out and out[-1][0] == x:
            out[-1][1] += 1
        else:
            out.append([x, 1])
    return out


def r_days_until_warmer(temps):
    return [next((j - i for j in range(i + 1, len(temps)) if temps[j] > t), 0) for i, t in enumerate(temps)]


def r_balanced(tokens):
    pairs, stack = {")": "(", "]": "[", "}": "{"}, []
    for t in tokens:
        if t in pairs:
            if not stack or stack.pop() != pairs[t]:
                return False
        else:
            stack.append(t)
    return not stack


def r_max_subarray(xs):
    best = cur = xs[0]
    for x in xs[1:]:
        cur = max(x, cur + x)
        best = max(best, cur)
    return best


def r_median(xs):
    s, n = sorted(xs), len(xs)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) // 2


L, LL = "List[Int]", "List[List[Int]]"
TASKS = [
    dict(name="rotate", params=[("xs", L), ("k", "Int")], ret=L, ref=r_rotate,
         text="Rotate the list right by k places: each item moves k places later, and items that fall off the "
              "end wrap around to the front. k may be negative (rotate left) or larger than the list's length. "
              "An empty list stays empty.",
         shown=dict(xs=[1, 2, 3, 4, 5], k=2),
         hidden=[dict(xs=[1, 2, 3, 4, 5], k=0), dict(xs=[1, 2, 3, 4, 5], k=5), dict(xs=[1, 2, 3, 4, 5], k=7),
                 dict(xs=[1, 2, 3, 4, 5], k=-1), dict(xs=[1, 2, 3, 4, 5], k=-7), dict(xs=[], k=3),
                 dict(xs=[9], k=4), dict(xs=[1, 2], k=-5), dict(xs=[1, 2, 3], k=100)]),
    dict(name="second_largest", params=[("xs", L)], ret="Option[Int]", ref=r_second_largest,
         text="Return the largest value in the list that is strictly smaller than the list's maximum, or none "
              "if there is no such value (for example, when the list is empty or all its items are equal).",
         shown=dict(xs=[3, 1, 4, 1, 5]),
         hidden=[dict(xs=[]), dict(xs=[7]), dict(xs=[2, 2, 2]), dict(xs=[-3, -1, -2]), dict(xs=[5, 5, 4]),
                 dict(xs=[-1, -1]), dict(xs=[1, 2]), dict(xs=[0, -5]), dict(xs=[4, 9, 9, 1])]),
    dict(name="spread", params=[("rows", "Int"), ("cols", "Int"), ("points", LL)], ret=LL, ref=r_spread,
         text="Make a grid of zeros with the given number of rows and columns (both at least 1). Each point is "
              "a two-item list [row, column], numbered from 0, and is always inside the grid. For each point "
              "in turn, add 1 to that cell and to each of its four neighbours (up, down, left, right) that "
              "lie inside the grid. Return the grid as a list of rows.",
         shown=dict(rows=2, cols=3, points=[[0, 0]]),
         hidden=[dict(rows=3, cols=3, points=[[1, 1]]), dict(rows=2, cols=3, points=[[1, 2]]),
                 dict(rows=3, cols=4, points=[[2, 3], [0, 3]]), dict(rows=1, cols=1, points=[[0, 0]]),
                 dict(rows=2, cols=2, points=[]), dict(rows=3, cols=2, points=[[2, 0], [2, 0]]),
                 dict(rows=1, cols=4, points=[[0, 0], [0, 3]]), dict(rows=4, cols=1, points=[[3, 0]])]),
    dict(name="window_sums", params=[("xs", L), ("k", "Int")], ret=L, ref=r_window_sums,
         text="Return the sum of every run of k consecutive items, in order from the left. k is at least 1. "
              "If k is larger than the list's length, there are no runs.",
         shown=dict(xs=[1, 2, 3, 4], k=2),
         hidden=[dict(xs=[1, 2, 3, 4], k=4), dict(xs=[1, 2, 3, 4], k=5), dict(xs=[1, 2, 3, 4], k=1),
                 dict(xs=[], k=1), dict(xs=[5], k=1), dict(xs=[-1, 2, -3, 4, -5], k=3),
                 dict(xs=[1, 1, 1, 1, 1, 1], k=3), dict(xs=[7, 8], k=3)]),
    dict(name="merge_ranges", params=[("ranges", LL)], ret=LL, ref=r_merge_ranges,
         text="Each range is a two-item list [lo, hi] meaning every whole number from lo to hi, inclusive "
              "(lo <= hi). The ranges come in any order. Merge ranges that share at least one number, "
              "repeatedly, until no two share a number, and return the result sorted by lo.",
         shown=dict(ranges=[[5, 6], [1, 3], [2, 4]]),
         hidden=[dict(ranges=[]), dict(ranges=[[1, 3], [3, 5]]), dict(ranges=[[1, 3], [4, 5]]),
                 dict(ranges=[[1, 10], [2, 3], [4, 5]]), dict(ranges=[[4, 5], [1, 3]]),
                 dict(ranges=[[2, 2]]), dict(ranges=[[1, 2], [1, 2]]), dict(ranges=[[-5, -1], [-2, 0], [3, 4]]),
                 dict(ranges=[[6, 8], [1, 2], [2, 6], [10, 11]])]),
    dict(name="first_at_least", params=[("xs", L), ("x", "Int")], ret="Int",
         ref=lambda xs, x: bisect.bisect_left(xs, x),
         text="The list is sorted in ascending order and may repeat values. Return the position (from 0) of "
              "the first item that is greater than or equal to x, or the list's length if there is none.",
         shown=dict(xs=[1, 3, 3, 5], x=3),
         hidden=[dict(xs=[1, 3, 3, 5], x=0), dict(xs=[1, 3, 3, 5], x=6), dict(xs=[], x=1),
                 dict(xs=[1, 3, 3, 5], x=4), dict(xs=[1, 3, 3, 5], x=5), dict(xs=[2, 2, 2], x=2),
                 dict(xs=[-4, -2, 0], x=-3), dict(xs=[1, 3, 3, 5], x=1)]),
    dict(name="digit_sum", params=[("n", "Int")], ret="Int", ref=r_digit_sum,
         text="Return the sum of the decimal digits of n, ignoring its sign (so a negative number has the same "
              "digit sum as its absolute value).",
         shown=dict(n=1234),
         hidden=[dict(n=0), dict(n=-1234), dict(n=9), dict(n=-5), dict(n=1000000), dict(n=-90),
                 dict(n=9223372036854775807)]),
    dict(name="run_lengths", params=[("xs", L)], ret=LL, ref=r_run_lengths,
         text="Run-length encode the list: return a list of [value, count] pairs, one per run of equal "
              "adjacent items, in order.",
         shown=dict(xs=[1, 1, 2, 3, 3, 3]),
         hidden=[dict(xs=[]), dict(xs=[5]), dict(xs=[1, 2, 1]), dict(xs=[4, 4, 4, 4]),
                 dict(xs=[1, 2, 2]), dict(xs=[0, 0, -1, 0])]),
    dict(name="days_until_warmer", params=[("temps", L)], ret=L, ref=r_days_until_warmer,
         text="For each day's temperature, return how many days later the first strictly warmer day comes, "
              "or 0 if no later day is warmer.",
         shown=dict(temps=[73, 74, 75, 71, 69, 72, 76, 73]),
         hidden=[dict(temps=[]), dict(temps=[50]), dict(temps=[5, 4, 3]), dict(temps=[5, 5, 5]),
                 dict(temps=[1, 2, 3]), dict(temps=[3, 1, 1, 2, 4]), dict(temps=[-5, -10, -3])]),
    dict(name="balanced", params=[("tokens", "List[String]")], ret="Bool", ref=r_balanced,
         text="Each token is one of the brackets ( ) [ ] { }, as a one-character string. Return whether "
              "they are properly balanced: every opening bracket is closed by the matching kind, in the "
              "right nesting order, and nothing is left open.",
         shown=dict(tokens=["(", "[", "]", ")"]),
         hidden=[dict(tokens=[]), dict(tokens=[")"]), dict(tokens=["(", "]"]), dict(tokens=["("]),
                 dict(tokens=["(", ")", "("]), dict(tokens=["{", "(", "[", "]", ")", "}"]),
                 dict(tokens=["[", "(", "]", ")"]), dict(tokens=["(", ")", ")", "("]),
                 dict(tokens=["{", "}", "[", "]"])]),
    dict(name="max_subarray", params=[("xs", L)], ret="Int", ref=r_max_subarray,
         text="The list has at least one item. Return the largest sum of a non-empty run of consecutive items.",
         shown=dict(xs=[-2, 1, -3, 4, -1, 2, 1, -5, 4]),
         hidden=[dict(xs=[-3, -1, -2]), dict(xs=[-5]), dict(xs=[0]), dict(xs=[1, 2, 3]),
                 dict(xs=[2, -1, 2]), dict(xs=[-1, 0, -2]), dict(xs=[5, -10, 6])]),
    dict(name="median", params=[("xs", L)], ret="Int", ref=r_median,
         text="The list has at least one item, in any order. Return its median: the middle value once sorted; "
              "for an even number of items, the mean of the two middle values rounded down (toward negative "
              "infinity, so -1.5 rounds to -2).",
         shown=dict(xs=[3, 1, 2]),
         hidden=[dict(xs=[4, 1, 3, 2]), dict(xs=[-1, -2]), dict(xs=[5]), dict(xs=[1, 1, 1, 1]),
                 dict(xs=[-3, -4, 10, 0]), dict(xs=[7, 8]), dict(xs=[2, -7, 4, -1, 0])]),
]


# Rule-dense tasks a model hasn't seen solved a thousand times: every rule matters, and the hidden
# inputs sit on the boundaries between rules.
def r_parking_fee(minutes):
    def part(m):
        return 0 if m <= 15 else min(20, 3 * -(-m // 60))
    return 20 * (minutes // 1440) + part(minutes % 1440)


def r_add_days(year, month, day, days):
    import datetime as dt
    d = dt.date(year, month, day) + dt.timedelta(days=days)
    return [d.year, d.month, d.day]


def r_tax(income):
    t, prev = 0, 0
    for cap, rate in ((10000, 0), (40000, 10), (100000, 25), (None, 40)):
        top = income if cap is None else min(income, cap)
        t += max(0, top - prev) * rate // 100
        if cap is None or income <= cap:
            break
        prev = cap
    return max(0, t - 500)


def r_rank(scores, attempts):
    return sorted(range(len(scores)), key=lambda i: (-scores[i], attempts[i], i))


def r_darts(start, throws):
    score = start
    for t in range(0, len(throws), 3):
        turn_start = score
        for x in throws[t:t + 3]:
            if score - x < 0 or score - x == 1:
                score = turn_start
                break
            score -= x
            if score == 0:
                return 0
    return score


def r_elevator(start, requests):
    s = set(requests)
    return ([start] if start in s else []) + sorted(f for f in s if f > start) + \
        sorted((f for f in s if f < start), reverse=True)


def r_runoff(candidates, ballots):
    left = set(range(candidates))
    while len(left) > 1:
        counts, total = {k: 0 for k in left}, 0
        for b in ballots:
            top = next((x for x in b if x in left), None)
            if top is not None:
                counts[top] += 1
                total += 1
        for k in left:
            if counts[k] * 2 > total:
                return k
        low = min(counts.values())
        left.remove(max(k for k in left if counts[k] == low))
    return min(left)


def r_vending(amount, coins):
    used, rest = [], amount
    for value, have in zip((25, 10, 5, 1), coins):
        k = min(have, rest // value)
        used.append(k)
        rest -= k * value
    return used if rest == 0 else None


RULES = [
    dict(name="parking_fee", params=[("minutes", "Int")], ret="Int", ref=r_parking_fee,
         text="A car park charges for a stay of `minutes` minutes (0 or more). A stay of 15 minutes or less is "
              "free. Otherwise the charge is 3 for each hour or part of an hour, counted from the start of the "
              "stay, but never more than 20. A stay of a day (1440 minutes) or longer pays 20 for each complete "
              "day, and what is left after the complete days is charged by the rules above as if it were a "
              "stay of its own (so a remainder of 15 minutes or less is free).",
         shown=dict(minutes=100),
         hidden=[dict(minutes=0), dict(minutes=15), dict(minutes=16), dict(minutes=60), dict(minutes=61),
                 dict(minutes=360), dict(minutes=361), dict(minutes=1439), dict(minutes=1440),
                 dict(minutes=1455), dict(minutes=1456), dict(minutes=1500), dict(minutes=3301)]),
    dict(name="add_days", params=[("year", "Int"), ("month", "Int"), ("day", "Int"), ("days", "Int")],
         ret=L, ref=r_add_days,
         text="Given a valid date in the Gregorian calendar (year from 1 to 9000, month 1-12, day of the month "
              "from 1) and a number of days, which may be negative, return the date that many days later as "
              "[year, month, day]. Leap years are those divisible by 4, except years divisible by 100, which "
              "are leap years only if also divisible by 400.",
         shown=dict(year=2024, month=2, day=28, days=2),
         hidden=[dict(year=2023, month=2, day=28, days=1), dict(year=2024, month=2, day=28, days=1),
                 dict(year=1900, month=2, day=28, days=1), dict(year=2000, month=2, day=28, days=1),
                 dict(year=2024, month=1, day=1, days=-1), dict(year=2100, month=3, day=1, days=-1),
                 dict(year=2024, month=3, day=15, days=0), dict(year=2023, month=12, day=31, days=366),
                 dict(year=2020, month=5, day=31, days=1000), dict(year=2000, month=3, day=1, days=-1000),
                 dict(year=2024, month=2, day=29, days=365)]),
    dict(name="tax", params=[("income", "Int")], ret="Int", ref=r_tax,
         text="Compute the tax on an income (0 or more). The part of the income up to 10000 is taxed at 0%; "
              "the part above 10000, up to 40000, at 10%; the part above 40000, up to 100000, at 25%; and the "
              "part above 100000 at 40%. Each part's tax is rounded down to a whole number on its own, and "
              "then the parts are added. Finally a credit of 500 is subtracted, but the tax is never below 0.",
         shown=dict(income=50000),
         hidden=[dict(income=0), dict(income=10000), dict(income=15000), dict(income=15010),
                 dict(income=10009), dict(income=40000), dict(income=40003), dict(income=40004),
                 dict(income=100000), dict(income=100003), dict(income=250000)]),
    dict(name="rank", params=[("scores", L), ("attempts", L)], ret=L, ref=r_rank,
         text="Player i scored scores[i] points using attempts[i] attempts (the two lists have the same "
              "length). Return the players' indexes in ranking order: more points first; on equal points, "
              "fewer attempts first; if both are equal, the lower index first.",
         shown=dict(scores=[3, 5, 5, 1], attempts=[2, 3, 1, 0]),
         hidden=[dict(scores=[], attempts=[]), dict(scores=[7], attempts=[1]),
                 dict(scores=[5, 5, 5], attempts=[1, 1, 1]), dict(scores=[2, 2, 2, 2], attempts=[3, 1, 3, 1]),
                 dict(scores=[4, 4, 4, 4, 4], attempts=[5, 4, 3, 2, 1]),
                 dict(scores=[1, 3, 2, 3, 1, 2], attempts=[0, 2, 2, 2, 0, 1]),
                 dict(scores=[-1, 0, -1], attempts=[1, 1, 0]),
                 dict(scores=[9, 1, 9, 1, 9], attempts=[2, 2, 2, 2, 2])]),
    dict(name="darts", params=[("start", "Int"), ("throws", L)], ret="Int", ref=r_darts,
         text="A darts game starts with `start` points (2 or more). The throws come in turns of three: throws "
              "1-3 are the first turn, 4-6 the second, and so on (the last turn may be shorter). Each throw's "
              "points (0 or more) are subtracted from the score. If a throw would leave the score below 0 or "
              "at exactly 1, it's a bust: the score goes back to what it was at the start of that turn, and "
              "the rest of that turn's throws are skipped. When the score reaches exactly 0 the game is over "
              "and any later throws are ignored. Return the final score.",
         shown=dict(start=50, throws=[20, 20, 5, 3, 1, 1]),
         hidden=[dict(start=101, throws=[]), dict(start=40, throws=[20, 20]), dict(start=40, throws=[20, 20, 5]),
                 dict(start=40, throws=[30, 15, 5, 10]), dict(start=10, throws=[9]),
                 dict(start=10, throws=[5, 3, 4, 2]), dict(start=3, throws=[1, 1, 1]),
                 dict(start=100, throws=[60, 60, 0, 50, 50]), dict(start=7, throws=[3, 3, 3, 2, 2, 2, 2])]),
    dict(name="elevator", params=[("start", "Int"), ("requests", L)], ret=L, ref=r_elevator,
         text="An elevator is at floor `start` and must visit every requested floor (floors may be negative; "
              "a floor may be requested more than once but is visited once). If the starting floor is "
              "requested, it is visited first, before moving. Then the elevator goes up, stopping at each "
              "requested floor on the way, until no requested floor is left above it; then it goes down, "
              "stopping at the remaining requested floors. Return the floors in the order they are visited.",
         shown=dict(start=5, requests=[7, 2, 9, 3]),
         hidden=[dict(start=5, requests=[]), dict(start=5, requests=[5]), dict(start=5, requests=[1, 2]),
                 dict(start=5, requests=[6, 6, 6]), dict(start=0, requests=[-2, 3, -1, 5]),
                 dict(start=5, requests=[5, 4, 6, 5]), dict(start=3, requests=[1, 2, 3, 4, 5]),
                 dict(start=10, requests=[9, 11, 10, 8, 12])]),
    dict(name="runoff", params=[("candidates", "Int"), ("ballots", LL)], ret="Int", ref=r_runoff,
         text="Candidates are numbered from 0 to candidates - 1 (there is at least one). Each ballot lists "
              "candidate numbers in order of preference; it may list only some candidates (or none) and never "
              "lists one twice. Count in rounds. If only one candidate is left in the race, that candidate "
              "wins. Otherwise every ballot counts for its highest-ranked candidate still in the race; a "
              "ballot with none left counts for nobody. If a candidate has more than half of the ballots that "
              "count this round, that candidate wins. Otherwise the candidate with the fewest votes this round "
              "is removed from the race (a candidate with no votes has 0); if several are tied for fewest, "
              "the one with the highest number is removed. Then the next round starts. Return the winner.",
         shown=dict(candidates=3, ballots=[[0, 1], [1], [2, 1], [0], [1, 0]]),
         hidden=[dict(candidates=1, ballots=[]), dict(candidates=2, ballots=[]),
                 dict(candidates=3, ballots=[[2], [2], [1]]), dict(candidates=3, ballots=[[0], [1], [2]]),
                 dict(candidates=4, ballots=[[3, 0], [3, 0], [1, 0], [2, 1]]),
                 dict(candidates=2, ballots=[[1], [1], [0], [0]]),
                 dict(candidates=3, ballots=[[1, 2], [2, 1], [0]]), dict(candidates=3, ballots=[[], [], [0]])]),
    dict(name="vending", params=[("amount", "Int"), ("coins", L)], ret="Option[List[Int]]", ref=r_vending,
         text="A machine gives `amount` (0 or more) in change, using coins worth 25, 10, 5 and 1. `coins` has "
              "four items: how many coins of each value the machine holds, in that order. It uses as many 25s "
              "as it can without going over the amount or its supply, then as many 10s, then 5s, then 1s. If "
              "that leaves part of the amount unpaid, return none (even if some other mix of coins would have "
              "worked). Otherwise return how many coins of each value it used, in the same order.",
         shown=dict(amount=67, coins=[2, 1, 3, 10]),
         hidden=[dict(amount=0, coins=[0, 0, 0, 0]), dict(amount=30, coins=[1, 0, 0, 4]),
                 dict(amount=30, coins=[0, 3, 0, 0]), dict(amount=30, coins=[1, 0, 1, 0]),
                 dict(amount=99, coins=[3, 2, 1, 4]), dict(amount=100, coins=[10, 10, 10, 10]),
                 dict(amount=40, coins=[1, 1, 0, 4]), dict(amount=6, coins=[0, 0, 0, 5]),
                 dict(amount=6, coins=[0, 0, 1, 1])]),
]
SETS = {"basic": TASKS, "rules": RULES}


# ---- formatting -------------------------------------------------------------------------------
def inner(t):
    return t[t.index("[") + 1:-1]


def py_type(t):
    if t.startswith("List["):
        return f"list[{py_type(inner(t))}]"
    if t.startswith("Option["):
        return f"{py_type(inner(t))} | None"
    return {"Int": "int", "Bool": "bool", "String": "str"}[t]


def cl_str(s):
    return '"' + "".join({"\\": "\\\\", '"': '\\"', "{": "\\{", "}": "\\}", "\n": "\\n", "\t": "\\t"}.get(c, c)
                         for c in s) + '"'


def lit_cl(v, t):
    if t.startswith("List["):
        return "[" + ", ".join(lit_cl(x, inner(t)) for x in v) + "]"
    if t.startswith("Option["):
        return "None" if v is None else f"Some({lit_cl(v, inner(t))})"
    if t == "Bool":
        return "true" if v else "false"
    return cl_str(v) if t == "String" else str(v)


def lit_py(v, t):
    if t.startswith("List["):
        return "[" + ", ".join(lit_py(x, inner(t)) for x in v) + "]"
    if t.startswith("Option["):
        return "None" if v is None else lit_py(v, inner(t))
    return repr(v)


# What claude-lang's print shows for a value; the Python runner prints its result the same way. The
# source is also pasted into each Python run, so a result of the wrong type reads as a wrong answer.
FMT_SRC = r'''
def fmt(v, t, top=True):
    if t.startswith("List["):
        if not isinstance(v, (list, tuple)):
            return "<not a list: %r>" % (v,)
        return "[" + ", ".join(fmt(x, t[5:-1], False) for x in v) + "]"
    if t.startswith("Option["):
        return "None" if v is None else "Some(" + fmt(v, t[7:-1], False) + ")"
    if t == "Bool":
        return ("true" if v else "false") if isinstance(v, bool) else "<not a Bool: %r>" % (v,)
    if t == "Int":
        return str(v) if isinstance(v, int) and not isinstance(v, bool) else "<not an Int: %r>" % (v,)
    if not isinstance(v, str):
        return "<not a String: %r>" % (v,)
    return v if top else '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
'''
exec(FMT_SRC)


def call_cl(task, args):
    ps = task["params"]
    if len(ps) == 1:
        return f"{task['name']}({ps[0][0]}: {lit_cl(args[ps[0][0]], ps[0][1])})"
    return f"{task['name']}(" + ", ".join(f"{p}: {lit_cl(args[p], t)}" for p, t in ps) + ")"


def call_py(task, args):
    return f"{task['name']}(" + ", ".join(f"{p}={lit_py(args[p], t)}" for p, t in task["params"]) + ")"


def sig_cl(task):
    return f"fn {task['name']}(" + ", ".join(f"{p}: {t}" for p, t in task["params"]) + f") -> {task['ret']}"


def sig_py(task):
    return f"def {task['name']}(" + ", ".join(f"{p}: {py_type(t)}" for p, t in task["params"]) + \
           f") -> {py_type(task['ret'])}"


def want(task, args):
    return fmt(task["ref"](**json.loads(json.dumps(args))), task["ret"])  # deep copy: refs mustn't share


# ---- prompts ----------------------------------------------------------------------------------
TAIL = ("It will also be called on other inputs, so handle every input the task allows. {extra}"
        "Reply with only the code, in one ```{fence} code block.")
CL_PROMPT = """Below is the complete specification of a new programming language, claude-lang.
You have never seen it before; rely only on this spec.

<spec>
{spec}
</spec>

Task: write this claude-lang function, with any helper functions or types it needs:

    {sig}

{text}

Example: `{example}`

""" + TAIL
PY_PROMPT = """Task: write this Python function, with any helper functions or types it needs:

    {sig}

{text}

Example: `{example}`

""" + TAIL
FIX = """{prompt}

You wrote:
```{fence}
{code}
```

{what}
```
{diags}
```

Reply with only the corrected code, in one ```{fence} code block."""
EXTRA = {"cl": "Don't write `fn main`. ",
         "py": "Use only the standard library, and write no top-level code other than definitions "
               "(no `if __name__` block). You may put doctests in docstrings: they are run before the "
               "example, and failures are sent back to you. "}


def extract(reply, fence):
    blocks = re.findall(r"```[a-zA-Z]*\n(.*?)```", reply, re.S)
    code = (blocks or [reply])[-1]
    if fence == "cl":  # a `fn main` the model wrote anyway would clash with ours
        code = re.sub(r"^fn main\(\).*?^end fn main[ \t]*\n?", "", code, flags=re.S | re.M)
    return code.strip() + "\n"


# ---- running ----------------------------------------------------------------------------------
def run(cmd, cwd, timeout=10):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd,
                         start_new_session=True)
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        p.communicate()
        return 124, "", f"(still running after {timeout} s; stopped)"
    return p.returncode, out, err.replace(cwd + "/", "")


def execute(lang, task, code, args, tmp, doctests=False):
    """(status, output, stderr) for one call. Status 'build-fail' is a claude-lang build error (its
    `example` lines included) or, with doctests=True, a failing Python doctest: each language's own
    check before the code is used."""
    if lang == "cl":
        src = code + f"\nfn main() uses io\n  print({call_cl(task, args)})\nend fn main\n"
        with open(os.path.join(tmp, "prog.cl"), "w") as fh:
            fh.write(src)
        rc, out, err = run([sys.executable, CLC, "build", "-o", os.path.join(tmp, "prog"), "prog.cl"], tmp, 60)
        if rc != 0:
            return "build-fail", out, err
        rc, out, err = run([os.path.join(tmp, "prog")], tmp)
    else:
        with open(os.path.join(tmp, "sol.py"), "w") as fh:
            fh.write(code)
        if doctests:
            rc, out, err = run([sys.executable, "-B", "-m", "doctest", "sol.py"], tmp)
            if rc != 0:
                return "build-fail", "", "\n".join((out + err).replace(tmp + "/", "").strip().splitlines()[-40:])
        with open(os.path.join(tmp, "runner.py"), "w") as fh:
            fh.write(FMT_SRC + f"\nfrom sol import {task['name']}\n"
                     f"print(fmt({call_py(task, args)}, {task['ret']!r}))\n")
        rc, out, err = run([sys.executable, "-B", "runner.py"], tmp)
        err = "\n".join(err.strip().splitlines()[-6:])
    return ("ran" if rc == 0 else "error"), out, err


def selftest():
    """Every expected value, written as a claude-lang literal and printed, must read back as fmt() says."""
    bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        for task in TASKS + RULES:
            lines = []
            for args in [task["shown"]] + task["hidden"]:
                v = task["ref"](**json.loads(json.dumps(args)))
                lines.append(f"  let v{len(lines)}: {task['ret']} = {lit_cl(v, task['ret'])}\n"
                             f"  print(v{len(lines)})\n")
                call_cl(task, args), call_py(task, args)
            with open(os.path.join(tmp, "t.cl"), "w") as fh:
                fh.write("fn main() uses io\n" + "".join(lines) + "end fn main\n")
            rc, out, err = run([sys.executable, CLC, "run", "t.cl"], tmp, 60)
            exp = "".join(want(task, a) + "\n" for a in [task["shown"]] + task["hidden"])
            ok = rc == 0 and out == exp
            bad += not ok
            print(f"{task['name']}: {'ok' if ok else 'MISMATCH'}")
            if not ok:
                print(err[-500:], out, exp, sep="\n---\n")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=["cl", "py"])
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--set", choices=sorted(SETS), default="basic")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(1 if selftest() else 0)
    spec = open(os.path.join(ROOT, "SPEC.md")).read()
    lang, fence = args.lang, {"cl": "cl", "py": "python"}[args.lang]
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d-%H%M")
    out_path = os.path.join(HERE, "results", f"{stamp}-hidden-{args.set}-{lang}-{args.model}.md")
    rows, log = [], [f"# Hidden-input trial {stamp} ({args.set} tasks, {lang}, {args.model})\n"]
    totals = dict(ok=0, wrong=0, error=0)
    for task in SETS[args.set]:
        if args.only and task["name"] not in args.only:
            continue
        sig, call = (sig_cl(task), call_cl) if lang == "cl" else (sig_py(task), call_py)
        shown_want = (lit_cl if lang == "cl" else lit_py)(task["ref"](**task["shown"]), task["ret"])
        prompt = (CL_PROMPT if lang == "cl" else PY_PROMPT).format(
            spec=spec, sig=sig, text=task["text"], example=f"{call(task, task['shown'])} == {shown_want}",
            extra=EXTRA[lang], fence=fence)
        log.append(f"## {task['name']}\n\n`{sig}`\n")
        with tempfile.TemporaryDirectory() as tmp:
            code = extract(claude(prompt, args.model), fence)
            fixed = False
            for n in (1, 2):
                status, out, err = execute(lang, task, code, task["shown"], tmp, doctests=True)
                good = status == "ran" and out == want(task, task["shown"]) + "\n"
                log.append(f"### attempt {n}: {'shown example OK' if good else status}\n\n```{fence}\n{code}```\n")
                if good or n == 2:
                    break
                diags = err.strip() if status != "ran" else \
                    f"(it printed:\n{out.strip()}\ninstead of:\n{want(task, task['shown'])})"
                log.append(f"Diagnostics sent back:\n```\n{diags}\n```\n")
                what = ("The compiler said:" if lang == "cl" else "Running its doctests gave:") \
                    if status == "build-fail" else "Running the example gave:"
                code = extract(claude(FIX.format(prompt=prompt, fence=fence, code=code, what=what, diags=diags),
                                      args.model), fence)
                fixed = True
            counts, notes = dict(ok=0, wrong=0, error=0), []
            if status == "build-fail":
                counts["error"] = len(task["hidden"])
                notes.append("never built")
            else:
                for hargs in task["hidden"]:
                    st, out, err = execute(lang, task, code, hargs, tmp)
                    w = want(task, hargs)
                    kind = "ok" if st == "ran" and out == w + "\n" else ("wrong" if st == "ran" else "error")
                    counts[kind] += 1
                    if kind != "ok":
                        got = out.strip() if st == "ran" else (err.strip().splitlines() or ["?"])[-1][:160]
                        notes.append(f"- {kind}: `{call(task, hargs)}` gave `{got}`, want `{w}`")
            for k in totals:
                totals[k] += counts[k]
        examples = len(re.findall(r"^\s*example " if lang == "cl" else r"^\s*>>> ", code, re.M))
        size = sum(1 for l in code.splitlines() if l.strip() and not l.strip().startswith("#"))
        verdict = "all ok" if counts["ok"] == len(task["hidden"]) else \
            ("WRONG" if counts["wrong"] else "stopped")
        rows.append((task["name"], "after fix" if fixed else "first try", counts, verdict, size, examples))
        log.append("Hidden inputs: " + ", ".join(f"{v} {k}" for k, v in counts.items()) + "\n")
        log.extend(n + "\n" for n in notes)
        print(f"{task['name']}: {verdict} {counts} ({'after fix' if fixed else 'first try'})", flush=True)
    head = "| task | shown example | ok | wrong | error | verdict | lines | examples |\n|---|---|---|---|---|---|---|---|\n"
    head += "".join(f"| {n} | {f} | {c['ok']} | {c['wrong']} | {c['error']} | {v} | {s} | {e} |\n"
                    for n, f, c, v, s, e in rows)
    head += f"\nTotals over hidden inputs: {totals}. Programs with a wrong answer: " \
            f"{sum(1 for r in rows if r[3] == 'WRONG')} of {len(rows)}.\n"
    log.insert(1, head)
    with open(out_path, "w") as fh:
        fh.write("\n".join(log))
    print(out_path)


if __name__ == "__main__":
    main()
