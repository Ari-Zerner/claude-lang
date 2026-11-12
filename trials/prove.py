#!/usr/bin/env python3
"""Proof trial: given only SPEC.md, can a fresh Claude write a loop whose `invariant` lines let clc prove
the function's `ensures` (D33)?

Each task hands the model a function's first lines (its name, parameters, `requires`, `ensures` and an
example), sometimes with a helper function the contract calls, and asks for the whole function, written
with a loop. The harness puts the answer between the helper and a `main` of its own, builds it with the
Lean backend and looks for three things: the contract lines are still the ones given, the program prints
what the hidden `main` expects, and clc reports no `unproved` warning. An answer that runs but isn't proved
(or doesn't compile) goes back with the compiler's own words, up to twice. Everything is written to
trials/results/<run>.md.

  python3 trials/prove.py --reference            # the reference answers: every task must come out proved
  python3 trials/prove.py [--model haiku] [--set first|hard] [--only NAME ...]
  python3 trials/prove.py --replay trials/results/RUN.md [--clc OTHER/clc.py]
      # grade again the first answer each task got in an earlier run, without calling a model: do past
      # answers still prove, or (with an older compiler) what would that run have shown before a change?
"""
import argparse
import datetime
import os
import re
import signal
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from trial import claude  # noqa: E402  the same headless, tool-less call the other trials use

CLC = os.path.join(ROOT, "clc.py")
FIXES = 2          # how many times an answer goes back with the compiler's words
BUILD_SECONDS = 300

# name, what to do, helper functions (shown to the model and compiled in), the lines the answer must start
# with, words the body may not use (so the loop does the work), the hidden main and what it prints, and a
# reference body that clc proves.
TASKS = [
    dict(name="mul",
         task="Multiply by adding `a` to a running total `b` times.",
         helper="",
         header="fn mul(a: Int, b: Int) -> Int\n  requires b >= 0\n  ensures result == a * b\n"
                "  example mul(a: 3, b: 4) == 12\n",
         banned=["*"],
         main="  print(mul(a: 6, b: 7))\n  print(mul(a: -3, b: 5))\n  print(mul(a: 9, b: 0))\n",
         want="42\n-15\n0\n",
         reference="  var r = 0\n  for i in 0 until b\n    invariant r == a * i\n    r = r + a\n  end for\n"
                   "  return r\n"),
    dict(name="divide",
         task="Whole-number division by repeated subtraction: how many times `b` fits into `a`.",
         helper="",
         header="fn divide(a: Int, b: Int) -> Int\n  requires a >= 0 and b > 0\n"
                "  ensures result * b <= a and a < (result + 1) * b\n  example divide(a: 17, b: 5) == 3\n",
         banned=["/", "%"],
         main="  print(divide(a: 100, b: 7))\n  print(divide(a: 6, b: 6))\n  print(divide(a: 0, b: 3))\n",
         want="14\n1\n0\n",
         reference="  var q = 0\n  var r = a\n  while r >= b\n    invariant r >= 0 and q * b + r == a\n"
                   "    decreases r\n    r = r - b\n    q = q + 1\n  end while\n  return q\n"),
    dict(name="count_evens",
         task="Count the even numbers in the list.",
         helper="",
         header="fn count_evens(xs: List[Int]) -> Int\n  ensures result >= 0 and result <= length(xs)\n"
                "  example count_evens([1, 2, 4]) == 2\n",
         banned=[],
         main="  print(count_evens([2, 3, 4, 6]))\n  print(count_evens([1, 3]))\n  print(count_evens([]))\n",
         want="3\n0\n0\n",
         reference="  var c = 0\n  for i in 0 until length(xs)\n    invariant c >= 0 and c <= i\n"
                   "    if xs[i] % 2 == 0\n      c = c + 1\n    end if\n  end for\n  return c\n"),
    dict(name="find_index",
         task="Return the index of the first item equal to `want`, or -1 when there is none.",
         helper="",
         header="fn find_index(xs: List[Int], want: Int) -> Int\n"
                "  ensures result == -1 or (result >= 0 and result < length(xs) and xs[result] == want)\n"
                "  example find_index(xs: [4, 5, 6], want: 6) == 2\n"
                "  example find_index(xs: [4, 5, 6], want: 7) == -1\n",
         banned=[],
         main="  print(find_index(xs: [1, 2, 3, 2], want: 2))\n  print(find_index(xs: [], want: 2))\n"
              "  print(find_index(xs: [5], want: 5))\n",
         want="1\n-1\n0\n",
         reference="  for i in 0 until length(xs)\n    if xs[i] == want\n      return i\n    end if\n  end for\n"
                   "  return -1\n"),
    dict(name="fib",
         task="Compute the n-th Fibonacci number with a loop that keeps two running values. `fib_spec` below "
              "is the definition it must agree with; it is far too slow to call from the body.",
         helper="fn fib_spec(n: Int) -> Int\n  requires n >= 0\n  if n < 2\n    return n\n  end if\n"
                "  return fib_spec(n - 1) + fib_spec(n - 2)\nend fn fib_spec\n",
         header="fn fib(n: Int) -> Int\n  requires n >= 0\n  ensures result == fib_spec(n)\n"
                "  example fib(10) == 55\n",
         banned=[],
         main="  print(fib(30))\n  print(fib(0))\n  print(fib(1))\n",
         want="832040\n0\n1\n",
         reference="  var a = 0\n  var b = 1\n  for i in 0 until n\n"
                   "    invariant a == fib_spec(i) and b == fib_spec(i + 1)\n    let t = a + b\n    a = b\n"
                   "    b = t\n  end for\n  return a\n"),
    dict(name="sum",
         task="Add up the items of the list. `sum_spec(xs, n)` below, the sum of the first n items, is the "
              "definition it must agree with.",
         helper="fn sum_spec(xs: List[Int], n: Int) -> Int\n  requires n >= 0 and n <= length(xs)\n"
                "  if n == 0\n    return 0\n  end if\n  return sum_spec(xs: xs, n: n - 1) + xs[n - 1]\n"
                "end fn sum_spec\n",
         header="fn sum(xs: List[Int]) -> Int\n  ensures result == sum_spec(xs: xs, n: length(xs))\n"
                "  example sum([1, 2, 3]) == 6\n",
         banned=[],
         main="  print(sum([10, 20, 30, 40]))\n  print(sum([]))\n  print(sum([-5]))\n",
         want="100\n0\n-5\n",
         reference="  var t = 0\n  for i in 0 until length(xs)\n    invariant t == sum_spec(xs: xs, n: i)\n"
                   "    t = t + xs[i]\n  end for\n  return t\n"),
    dict(name="power",
         task="Raise `b` to the power `e` by repeated multiplication. `pow_spec` below is the definition it "
              "must agree with.",
         helper="fn pow_spec(b: Int, e: Int) -> Int\n  requires e >= 0\n  if e == 0\n    return 1\n  end if\n"
                "  return b * pow_spec(b: b, e: e - 1)\nend fn pow_spec\n",
         header="fn power(b: Int, e: Int) -> Int\n  requires e >= 0\n  ensures result == pow_spec(b: b, e: e)\n"
                "  example power(b: 2, e: 10) == 1024\n",
         banned=[],
         main="  print(power(b: 3, e: 4))\n  print(power(b: 7, e: 0))\n  print(power(b: -2, e: 3))\n",
         want="81\n1\n-8\n",
         reference="  var r = 1\n  for i in 0 until e\n    invariant r == pow_spec(b: b, e: i)\n    r = r * b\n"
                   "  end for\n  return r\n"),
]

# A harder set (night 8 step 5): a `while` with a `return`, loops against recursive definitions that need more
# than restating the loop, a list built in the loop, and a check that can't be proved with an early `return`.
HARD = [
    dict(name="bsearch",
         task="Binary search: `xs` is sorted in increasing order; return an index where `want` is, or -1 when "
              "it isn't there. Halve the range each pass; don't scan the list item by item.",
         helper="",
         header="fn bsearch(xs: List[Int], want: Int) -> Int\n"
                "  ensures result == -1 or (result >= 0 and result < length(xs) and xs[result] == want)\n"
                "  example bsearch(xs: [1, 3, 5, 7], want: 5) == 2\n"
                "  example bsearch(xs: [1, 3, 5, 7], want: 4) == -1\n",
         banned=[],
         main="  print(bsearch(xs: [2, 4, 6, 8, 10], want: 8))\n  print(bsearch(xs: [2, 4, 6, 8, 10], want: 5))\n"
              "  print(bsearch(xs: [], want: 1))\n  print(bsearch(xs: [7], want: 7))\n",
         want="3\n-1\n-1\n0\n",
         reference="  var lo = 0\n  var hi = length(xs)\n  while lo < hi\n"
                   "    invariant lo >= 0 and hi <= length(xs)\n    decreases hi - lo\n"
                   "    let mid = (lo + hi) / 2\n    if xs[mid] == want\n      return mid\n    end if\n"
                   "    if xs[mid] < want\n      lo = mid + 1\n    else\n      hi = mid\n    end if\n"
                   "  end while\n  return -1\n"),
    dict(name="gcd",
         task="Greatest common divisor by Euclid's method, with a loop. `gcd_spec` below is the definition it "
              "must agree with.",
         helper="fn gcd_spec(a: Int, b: Int) -> Int\n  requires a >= 0 and b >= 0\n  if b == 0\n    return a\n"
                "  end if\n  return gcd_spec(a: b, b: a % b)\nend fn gcd_spec\n",
         header="fn gcd(a: Int, b: Int) -> Int\n  requires a >= 0 and b >= 0\n"
                "  ensures result == gcd_spec(a: a, b: b)\n  example gcd(a: 48, b: 36) == 12\n",
         banned=["gcd_spec"],
         main="  print(gcd(a: 12, b: 18))\n  print(gcd(a: 7, b: 0))\n  print(gcd(a: 0, b: 0))\n"
              "  print(gcd(a: 35, b: 64))\n",
         want="6\n7\n0\n1\n",
         reference="  var x = a\n  var y = b\n  while y != 0\n"
                   "    invariant x >= 0 and y >= 0 and gcd_spec(a: x, b: y) == gcd_spec(a: a, b: b)\n"
                   "    decreases y\n    let t = x % y\n    x = y\n    y = t\n  end while\n  return x\n"),
    dict(name="factorial",
         task="n factorial, with a loop. `fact_spec` below is the definition it must agree with.",
         helper="fn fact_spec(n: Int) -> Int\n  requires n >= 0\n  if n == 0\n    return 1\n  end if\n"
                "  return n * fact_spec(n - 1)\nend fn fact_spec\n",
         header="fn factorial(n: Int) -> Int\n  requires n >= 0\n  ensures result == fact_spec(n)\n"
                "  example factorial(5) == 120\n",
         banned=["fact_spec"],
         main="  print(factorial(6))\n  print(factorial(0))\n  print(factorial(1))\n",
         want="720\n1\n1\n",
         reference="  var r = 1\n  for i in 1 through n\n    invariant r == fact_spec(i - 1)\n    r = r * i\n"
                   "  end for\n  return r\n"),
    dict(name="digit_sum",
         task="The sum of the decimal digits of n, with a loop. `digits_spec` below is the definition it must "
              "agree with.",
         helper="fn digits_spec(n: Int) -> Int\n  requires n >= 0\n  if n < 10\n    return n\n  end if\n"
                "  return n % 10 + digits_spec(n / 10)\nend fn digits_spec\n",
         header="fn digit_sum(n: Int) -> Int\n  requires n >= 0\n  ensures result == digits_spec(n)\n"
                "  example digit_sum(1234) == 10\n",
         banned=["digits_spec"],
         main="  print(digit_sum(98765))\n  print(digit_sum(0))\n  print(digit_sum(7))\n  print(digit_sum(1000))\n",
         want="35\n0\n7\n1\n",
         reference="  var k = n\n  var s = 0\n  while k >= 10\n"
                   "    invariant k >= 0 and s + digits_spec(k) == digits_spec(n)\n    decreases k\n"
                   "    s = s + k % 10\n    k = k / 10\n  end while\n  return s + k\n"),
    dict(name="reversed_list",
         task="Return the items of the list in the opposite order.",
         helper="",
         header="fn reversed_list(xs: List[Int]) -> List[Int]\n  ensures length(result) == length(xs)\n"
                "  example reversed_list([1, 2, 3]) == [3, 2, 1]\n",
         banned=[],
         main="  print(reversed_list([1, 2, 3, 4]))\n  print(reversed_list([]))\n  print(reversed_list([9]))\n",
         want="[4, 3, 2, 1]\n[]\n[9]\n",
         reference="  var out: List[Int] = []\n  for i in 0 until length(xs)\n    invariant length(out) == i\n"
                   "    out = append(list: out, item: xs[length(xs) - 1 - i])\n  end for\n  return out\n"),
    dict(name="max_index",
         task="Return the index of the largest item (the first one, if it appears more than once).",
         helper="",
         header="fn max_index(xs: List[Int]) -> Int\n  requires length(xs) > 0\n"
                "  ensures result >= 0 and result < length(xs)\n  example max_index([3, 9, 2]) == 1\n",
         banned=[],
         main="  print(max_index([5, 1, 7, 7]))\n  print(max_index([4]))\n  print(max_index([-3, -1, -2]))\n",
         want="2\n0\n1\n",
         reference="  var best = 0\n  for i in 1 until length(xs)\n    invariant best >= 0 and best < length(xs)\n"
                   "    if xs[i] > xs[best]\n      best = i\n    end if\n  end for\n  return best\n"),
    dict(name="is_sorted",
         task="Is the list in non-decreasing order? `sorted_spec(xs, n)` below, which says whether the first n "
              "items are, is the definition it must agree with.",
         helper="fn sorted_spec(xs: List[Int], n: Int) -> Bool\n  requires n >= 0 and n <= length(xs)\n"
                "  if n < 2\n    return true\n  end if\n"
                "  return sorted_spec(xs: xs, n: n - 1) and xs[n - 2] <= xs[n - 1]\nend fn sorted_spec\n",
         header="fn is_sorted(xs: List[Int]) -> Bool\n  ensures result == sorted_spec(xs: xs, n: length(xs))\n"
                "  example is_sorted([1, 2, 2, 5]) == true\n  example is_sorted([1, 3, 2]) == false\n",
         banned=["sorted_spec"],
         main="  print(is_sorted([1, 2, 3]))\n  print(is_sorted([3, 1, 2]))\n  print(is_sorted([]))\n"
              "  print(is_sorted([4]))\n  print(is_sorted([1, 2, 1, 5]))\n",
         want="true\nfalse\ntrue\ntrue\nfalse\n",
         reference="  if length(xs) < 2\n    return true\n  end if\n  var ok = true\n"
                   "  for i in 1 until length(xs)\n    invariant ok == sorted_spec(xs: xs, n: i)\n"
                   "    if xs[i - 1] > xs[i]\n      ok = false\n    end if\n  end for\n  return ok\n"),
]
SETS = {"first": TASKS, "hard": HARD}

PROMPT = """Below is the complete specification of a new programming language, claude-lang.
You have never seen it before; rely only on this spec.

<spec>
{spec}
</spec>

Task: write the claude-lang function `{name}`. {task}
{helper}
The function must begin with exactly these lines (don't change, add or remove a `requires` or `ensures`):

```cl
{header}```

Rules:
- Do the work with a `while` or `for` loop. `{name}` must not call itself{banned}.
- The compiler tries to prove each `ensures`. Give the loop the `invariant` lines (and, for a `while`, the
  `decreases` line) that let it: the goal is that the compiler reports nothing unproved.
- Reply with only the function `{name}`, from `fn {name}` to `end fn {name}`, in one ```cl code block. Don't
  write `main` or repeat any helper function.
"""

FIX_PROMPT = """Below is the complete specification of a new programming language, claude-lang.

<spec>
{spec}
</spec>

Task: write the claude-lang function `{name}`. {task}
{helper}
The function must begin with exactly these lines (don't change, add or remove a `requires` or `ensures`):

```cl
{header}```

Rules:
- Do the work with a `while` or `for` loop. `{name}` must not call itself{banned}.
- The compiler tries to prove each `ensures`. Give the loop the `invariant` lines (and, for a `while`, the
  `decreases` line) that let it: the goal is that the compiler reports nothing unproved.

You wrote:
```cl
{code}```

That isn't there yet:
```
{said}
```

Reply with only the corrected function `{name}`, from `fn {name}` to `end fn {name}`, in one ```cl code block.
"""

CONTRACT = ("requires", "ensures")
PROOF_LINES = CONTRACT + ("invariant", "decreases", "example")


def fields(t):
    banned = "".join(f", and its body must not use `{b}` (contract lines may)" for b in t["banned"])
    helper = f"\nThis helper is already in the program:\n\n```cl\n{t['helper']}```\n" if t["helper"] else ""
    return dict(name=t["name"], task=t["task"], helper=helper, header=t["header"], banned=banned)


def extract(reply, name):
    """The function in a reply: the last code block that defines it, cut to `fn name` ... `end fn name`."""
    blocks = re.findall(r"```[a-zA-Z]*\n(.*?)```", reply, re.S) or [reply]
    for b in reversed(blocks):
        m = re.search(rf"^fn {name}\(.*?^end fn {name}[ \t]*$", b, re.S | re.M)
        if m:
            return m.group(0) + "\n"
    return blocks[-1].strip() + "\n"


def rule_problems(t, code):
    """What the answer does that the task forbids, in words the model can act on (or [] when it's fine)."""
    out = []
    want = [ln.strip() for ln in t["header"].splitlines() if ln.strip().split(" ")[0] in CONTRACT]
    got = [ln.split("#")[0].strip() for ln in code.splitlines() if ln.strip().split(" ")[0] in CONTRACT]
    if sorted(want) != sorted(got):
        out.append("the `requires` and `ensures` lines must be exactly the ones given:\n  " + "\n  ".join(want))
    body = [ln.split("#")[0] for ln in code.splitlines()[1:] if ln.strip().split(" ")[0] not in PROOF_LINES]
    if not any(re.match(r"\s*(while|for)\b", ln) for ln in body):
        out.append("the function must do its work with a `while` or `for` loop")
    if any(re.search(rf"\b{t['name']}\(", ln) for ln in body):
        out.append(f"`{t['name']}` must not call itself")
    for b in t["banned"]:
        if any(b in ln for ln in body):
            out.append(f"the body must not use `{b}` (only the `requires`/`ensures`/`invariant` lines may)")
    return out


def build(t, code, tmp):
    """Compile helper + answer + the hidden main. Returns (exit code, stdout, what clc said)."""
    path = os.path.join(tmp, "prog.cl")
    with open(path, "w") as fh:
        fh.write(t["helper"] + ("\n" if t["helper"] else "") + code + "\nfn main() uses io\n" + t["main"]
                 + "end fn main\n")
    p = subprocess.Popen(["systemd-run", "--scope", "-q", "-p", "MemoryMax=400M", "--", sys.executable, CLC,
                          "run", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=tmp,
                         start_new_session=True)
    try:
        out, err = p.communicate(timeout=BUILD_SECONDS)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        out, err = p.communicate()
        return 124, out, f"(the build or the program was still running after {BUILD_SECONDS} s and was stopped)"
    return p.returncode, out, err.replace(tmp + "/", "")


def grade(t, code, tmp):
    """('proved' | 'unproved' | 'wrong', what to tell the model)."""
    rules = rule_problems(t, code)
    if rules:
        return "wrong", "\n".join(rules)
    rc, out, said = build(t, code, tmp)
    said = said.strip()
    if rc != 0:
        return "wrong", said or f"(exit {rc})"
    if out != t["want"]:
        return "wrong", f"It compiled, but a test program that calls it printed:\n{out}instead of:\n{t['want']}"
    if "warning[unproved]" in said:
        return "unproved", said
    return "proved", said


def recorded(path):
    """{task: the first answer it got} from an earlier run's results file."""
    out = {}
    for sec in re.split(r"^## ", open(path).read(), flags=re.M)[1:]:
        m = re.search(r"^### attempt 1: .*?```cl\n(.*?)```", sec, re.S | re.M)
        if m:
            out[sec.split("\n", 1)[0].strip()] = m.group(1)
    return out


def main():
    global CLC
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--set", choices=sorted(SETS), default="first")
    ap.add_argument("--reference", action="store_true", help="grade the reference answers; no model is called")
    ap.add_argument("--replay", metavar="RESULTS.md", help="grade an earlier run's first answers again")
    ap.add_argument("--clc", help="the compiler to grade with (default: this repo's clc.py)")
    args = ap.parse_args()
    if args.clc:
        CLC = os.path.abspath(args.clc)
    spec = open(os.path.join(ROOT, "SPEC.md")).read()
    fixed = recorded(args.replay) if args.replay else None
    who = "reference" if args.reference else args.model
    if args.replay:
        who = "replay-" + os.path.basename(args.replay)[len("2026-11-12-1303-prove-"):-3]
        if args.clc:
            print(f"grading with {CLC}", flush=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d-%H%M")
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    label = "prove" if args.set == "first" or args.replay else f"prove-{args.set}"
    out_path = os.path.join(HERE, "results", f"{stamp}-{label}-{who}.md")
    rows, log = [], [f"# Proof trial {stamp} ({who}{'' if label == 'prove' else ', ' + args.set + ' set'})\n"]
    if args.replay:
        log.append(f"First answers from `{args.replay}`, graded again with `{CLC}`.\n")
    for t in SETS[args.set] if fixed is None else TASKS + HARD:
        if (args.only and t["name"] not in args.only) or (fixed is not None and t["name"] not in fixed):
            continue
        log.append(f"## {t['name']}\n\nTask: {t['task']}\n\n```cl\n{t['helper']}{t['header']}```\n")
        f = fields(t)
        result, n = "not proved", 0
        with tempfile.TemporaryDirectory() as tmp:
            if args.reference:
                code = t["header"] + t["reference"] + f"end fn {t['name']}\n"
            elif fixed is not None:
                code = fixed[t["name"]]
            else:
                code = extract(claude(PROMPT.format(spec=spec, **f), args.model), t["name"])
            for n in range(1, FIXES + 2):
                verdict, said = grade(t, code, tmp)
                log.append(f"### attempt {n}: {verdict}\n\n```cl\n{code}```\n")
                if said:
                    log.append(f"Compiler:\n```\n{said}\n```\n")
                if verdict == "proved":
                    result = "proved, first try" if n == 1 else f"proved after {n - 1} fix{'es' if n > 2 else ''}"
                    break
                result = f"not proved (last: {verdict})"
                if args.reference or fixed is not None or n == FIXES + 1:
                    break
                log.append("_Sent back for a fix._\n")
                code = extract(claude(FIX_PROMPT.format(spec=spec, code=code, said=said, **f), args.model),
                               t["name"])
        rows.append((t["name"], result))
        print(f"{t['name']}: {result}", flush=True)
    log.insert(1, "| task | result |\n|---|---|\n" + "".join(f"| {n} | {r} |\n" for n, r in rows))
    with open(out_path, "w") as fh:
        fh.write("\n".join(log))
    print(out_path)


if __name__ == "__main__":
    main()
