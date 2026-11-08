"""Lean-direct baseline: can a fresh Claude write a function in Lean 4 *and prove it correct*?

Ari's sanity check for the verification plan (2026-11-07): "is this buying Claude anything over just
writing in Lean directly?" Before claude-lang grows contracts and proofs, this measures the other
road. Each task gives a function to write and theorem statements to prove (exact text). The harness
appends, after the model's code:
  - `theorem harness_k : <statement> := <name>` for each theorem, so a weakened statement fails;
  - `#print axioms <name>`, which must show none beyond propext / Classical.choice / Quot.sound
    (so no `sorry`, no `axiom`, no `native_decide`);
  - `#eval`s on hidden inputs, so the function computes what the task says, not just something
    that satisfies the theorems.
Lean's errors go back for up to two fix rounds. Lean 4.35 core only (no Mathlib), as installed.
Usage: python3 trials/leanbase.py --model haiku [--only NAME ...]
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from trial import claude  # noqa: E402

OK_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}

TASKS = [
    dict(name="sum", sig="def sumTo (n : Nat) : Nat",
         text="`sumTo n` is 0 + 1 + ... + n.",
         thms=[("sumTo_spec", "∀ n : Nat, 2 * sumTo n = n * (n + 1)")],
         evals=[("sumTo 0", "0"), ("sumTo 10", "55"), ("sumTo 100", "5050")]),
    dict(name="isqrt", sig="def isqrt (n : Nat) : Nat",
         text="`isqrt n` is the integer square root of n: the largest r with r * r ≤ n.",
         thms=[("isqrt_spec", "∀ n : Nat, isqrt n * isqrt n ≤ n ∧ n < (isqrt n + 1) * (isqrt n + 1)")],
         evals=[("isqrt 0", "0"), ("isqrt 1", "1"), ("isqrt 15", "3"), ("isqrt 16", "4"), ("isqrt 1000", "31")]),
    dict(name="max", sig="def maxList (x : Int) (xs : List Int) : Int",
         text="`maxList x xs` is the largest item of the non-empty list `x :: xs`.",
         thms=[("maxList_ge", "∀ (x : Int) (xs : List Int), ∀ y ∈ x :: xs, y ≤ maxList x xs"),
               ("maxList_mem", "∀ (x : Int) (xs : List Int), maxList x xs ∈ x :: xs")],
         evals=[("maxList 3 []", "3"), ("maxList (-5) [-7, -2, -9]", "-2"), ("maxList 1 [4, 1, 4, 2]", "4")]),
    dict(name="isort", sig="def isort (xs : List Int) : List Int",
         text="`isort` sorts the list into ascending order by insertion sort.",
         thms=[("isort_sorted", "∀ xs : List Int, (isort xs).Pairwise (· ≤ ·)"),
               ("isort_perm", "∀ xs : List Int, (isort xs).Perm xs")],
         evals=[("isort []", "[]"), ("isort [3, 1, 2, 1]", "[1, 1, 2, 3]"), ("isort [5, -1, 0]", "[-1, 0, 5]")]),
    dict(name="tax", sig="def tax (income : Nat) : Nat",
         text="The part of the income up to 10000 is taxed at 0%; the part above 10000, up to 40000, at 10%; "
              "the part above 40000, up to 100000, at 25%; and the part above 100000 at 40%. Each part's tax "
              "is rounded down to a whole number on its own, and then the parts are added. Finally a credit of "
              "500 is subtracted, but the tax is never below 0.",
         thms=[("tax_mono", "∀ a b : Nat, a ≤ b → tax a ≤ tax b")],
         evals=[("tax 0", "0"), ("tax 15010", "1"), ("tax 40003", "2500"), ("tax 40004", "2501"),
                ("tax 50000", "5000"), ("tax 100003", "17501"), ("tax 250000", "77500")]),
    dict(name="parking", sig="def parkingFee (minutes : Nat) : Nat",
         text="A car park charges for a stay of `minutes` minutes. A stay of 15 minutes or less is free. "
              "Otherwise the charge is 3 for each hour or part of an hour, counted from the start of the stay, "
              "but never more than 20. A stay of a day (1440 minutes) or longer pays 20 for each complete "
              "day, and what is left after the complete days is charged by the rules above as if it were a "
              "stay of its own (so a remainder of 15 minutes or less is free).",
         thms=[("parkingFee_le", "∀ m : Nat, parkingFee m ≤ 20 * (m / 1440 + 1)"),
               ("parkingFee_mono", "∀ a b : Nat, a ≤ b → parkingFee a ≤ parkingFee b")],
         evals=[("parkingFee 15", "0"), ("parkingFee 16", "3"), ("parkingFee 61", "6"), ("parkingFee 361", "20"),
                ("parkingFee 1455", "20"), ("parkingFee 1456", "23"), ("parkingFee 3301", "60")]),
]

# Where Lean-direct might break: a loop needing an invariant, an index-heavy algorithm, well-founded
# recursion, a round trip. `must`/`forbid` are regexes over the model's code (e.g. a `for` loop really
# is one; gcd doesn't just call Nat.gcd).
HARD = [
    dict(name="loop", sig="def sumSq (xs : List Nat) : Nat",
         text="`sumSq xs` is the sum of the squares of the items. Write it imperatively: `Id.run do` with a "
              "`let mut` accumulator and a `for x in xs do` loop.",
         must=[r"\bfor\b", r"let\s+mut"],
         thms=[("sumSq_spec", "∀ xs : List Nat, sumSq xs = (xs.map (fun x => x * x)).sum")],
         evals=[("sumSq []", "0"), ("sumSq [1, 2, 3]", "14"), ("sumSq [5]", "25")]),
    dict(name="bsearch", sig="def lowerBound (xs : Array Int) (x : Int) : Nat",
         text="`xs` is sorted in ascending order. `lowerBound xs x` is the position of the first item that is "
              "greater than or equal to x, or `xs.size` if there is none. Find it by binary search, halving "
              "the range of candidate positions each step.",
         thms=[("lowerBound_le", "∀ (xs : Array Int) (x : Int), lowerBound xs x ≤ xs.size"),
               ("lowerBound_spec", "∀ (xs : Array Int) (x : Int), xs.toList.Pairwise (· ≤ ·) → "
                "(∀ i (h : i < xs.size), i < lowerBound xs x → xs[i] < x) ∧ "
                "(∀ i (h : i < xs.size), lowerBound xs x ≤ i → x ≤ xs[i])")],
         evals=[("lowerBound #[1, 3, 3, 5] 3", "1"), ("lowerBound #[] 1", "0"), ("lowerBound #[1, 3, 3, 5] 6", "4"),
                ("lowerBound #[1, 3, 3, 5] 0", "0"), ("lowerBound #[-4, -2, 0] (-3)", "1"),
                ("lowerBound #[2, 2, 2] 2", "0")]),
    dict(name="gcd", sig="def gcd' (a b : Nat) : Nat",
         text="`gcd' a b` is the greatest common divisor of a and b, computed by Euclid's algorithm "
              "(`gcd' a 0 = a`, otherwise `gcd' b (a % b)`). Don't use `Nat.gcd` or its lemmas.",
         forbid=[r"Nat\.gcd"],
         thms=[("gcd'_dvd", "∀ a b : Nat, gcd' a b ∣ a ∧ gcd' a b ∣ b"),
               ("gcd'_greatest", "∀ a b d : Nat, d ∣ a → d ∣ b → d ∣ gcd' a b")],
         evals=[("gcd' 12 18", "6"), ("gcd' 7 0", "7"), ("gcd' 0 7", "7"), ("gcd' 0 0", "0"),
                ("gcd' 17 5", "1"), ("gcd' 100 75", "25")]),
    dict(name="rle", sig="def encode (xs : List Int) : List (Int × Nat)\n    def decode (ps : List (Int × Nat)) : List Int",
         text="`encode` run-length encodes a list: one (value, count) pair per maximal run of equal adjacent "
              "items, in order. `decode` expands pairs back into a list.",
         thms=[("decode_encode", "∀ xs : List Int, decode (encode xs) = xs"),
               ("encode_counts_pos", "∀ xs : List Int, ∀ p ∈ encode xs, 0 < p.2")],
         evals=[("encode [1, 1, 2]", "[(1, 2), (2, 1)]"), ("encode []", "[]"), ("decode [(3, 2)]", "[3, 3]"),
                ("encode [5, 5, -1, 5]", "[(5, 2), (-1, 1), (5, 1)]")]),
]
SETS = {"basic": TASKS, "hard": HARD}

PROMPT = """Write Lean 4 code (Lean 4.35, core library only: no Mathlib and no Batteries; `import Std` is
available) that defines

    {sig}

{text}

and proves these theorems, with exactly these names and statements:

{thms}

No `sorry`, no `axiom`, no `native_decide`. The definition must compute (it will be run with `#eval`).
Reply with only the code, in one ```lean code block."""

# --hints: the core-vs-Mathlib names both models tripped on in the first run (checked against Lean 4.35).
HINTS = """
Core Lean is not Mathlib. These don't exist here: `split_ifs` (use `split`), `linarith`, `nlinarith`,
`ring`, `norm_num`, `positivity`, `interval_cases`, `Nat.strong_induction_on`. Use `omega` for linear
arithmetic over Nat and Int (it handles `/` and `%` by constants), `grind` for nonlinear facts such as
ring identities, `simp`, `decide`, and `induction n using Nat.strongRecOn with | ind n ih => ...` for
strong induction."""

FIX = """{prompt}

You wrote:
```lean
{code}
```

Checking it gave:
```
{diags}
```

Reply with only the corrected code, in one ```lean code block."""


def extract(reply):
    blocks = re.findall(r"```[a-zA-Z0-9]*\n(.*?)```", reply, re.S)
    return (blocks or [reply])[-1].strip() + "\n"


def check(task, code, tmp):
    """(ok, diagnostics for the model, summary). Runs Lean once on the code plus the harness lines."""
    lines = code.rstrip("\n").split("\n")
    tail, roles = ["", "-- harness checks"], {}
    for k, (name, stmt) in enumerate(task["thms"]):
        roles[len(lines) + len(tail) + 1] = ("stmt", name)
        tail.append(f"theorem harness_{k} : {stmt} := {name}")
    for name, _ in task["thms"]:
        roles[len(lines) + len(tail) + 1] = ("axioms", name)
        tail.append(f"#print axioms {name}")
    for expr, want in task["evals"]:
        roles[len(lines) + len(tail) + 1] = ("eval", (expr, want))
        tail.append(f"#eval {expr}")
    path = os.path.join(tmp, "Task.lean")
    with open(path, "w") as fh:
        fh.write("\n".join(lines + tail) + "\n")
    t0 = time.time()
    try:
        r = subprocess.run(["systemd-run", "--scope", "-q", "-p", "MemoryMax=500M", "--", "lean", "--json", path],
                           capture_output=True, text=True, timeout=300, cwd=tmp)
        out = r.stdout
    except subprocess.TimeoutExpired:
        return False, "(Lean was still running after 300 s and was stopped)", "timeout", 300
    secs = round(time.time() - t0, 1)
    msgs = []
    for l in out.splitlines():
        try:
            msgs.append(json.loads(l))
        except json.JSONDecodeError:
            pass
    problems, evals_bad, model_errors = [], [], []
    for m in msgs:
        line, sev, data = m["pos"]["line"], m["severity"], m["data"].strip()
        role = roles.get(line)
        if role is None:  # the model's own code
            if sev == "error":
                model_errors.append(f"line {line}:{m['pos']['column']}: error: {data}")
            elif "sorry" in data:
                model_errors.append(f"line {line}: {data}")
            continue
        kind, info = role
        if sev == "error":
            what = {"stmt": f"theorem `{info}` doesn't have the required statement (or doesn't exist)",
                    "axioms": f"`{info}` doesn't exist", "eval": f"`#eval {info[0] if kind == 'eval' else ''}` failed"}[kind]
            problems.append(f"{what}: {data[:300]}")
        elif kind == "axioms":
            axs = set(re.findall(r"[\w.]+", data.split("[", 1)[1])) if "[" in data else set()
            if axs - OK_AXIOMS:
                problems.append(f"`{info}` depends on {sorted(axs - OK_AXIOMS)} (sorry, an axiom or native_decide)")
        elif kind == "eval" and data != info[1]:
            evals_bad.append(f"`{info[0]}` gave {data}, but should be {info[1]}")
    for pat in task.get("must", []):
        if not re.search(pat, code):
            problems.append(f"the code must use `{pat}` (see the task)")
    for pat in task.get("forbid", []):
        if re.search(pat, code):
            problems.append(f"the code must not use `{pat}` (see the task)")
    diags = "\n".join(model_errors + problems + evals_bad)
    if not msgs and r.returncode != 0:
        diags = (r.stderr or "lean failed")[-800:]
    ok = not model_errors and not problems and not evals_bad and r.returncode == 0
    summary = "ok" if ok else ("errors" if model_errors or problems else "wrong values")
    return ok, diags, summary, secs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--set", choices=sorted(SETS), default="basic")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--rounds", type=int, default=2, help="fix rounds after the first try")
    ap.add_argument("--hints", action="store_true", help="add the core-vs-Mathlib name note to the prompt")
    args = ap.parse_args()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d-%H%M")
    out_path = os.path.join(HERE, "results", f"{stamp}-leanbase-{args.set}{'-hints' if args.hints else ''}-{args.model}.md")
    rows, log = [], [f"# Lean-direct baseline {stamp} ({args.model})\n"]
    for task in SETS[args.set]:
        if args.only and task["name"] not in args.only:
            continue
        thms = "\n".join(f"    theorem {n} : {s}" for n, s in task["thms"])
        prompt = PROMPT.format(sig=task["sig"], text=task["text"], thms=thms)
        if args.hints:
            prompt = prompt.replace("\nReply with only", HINTS + "\n\nReply with only")
        log.append(f"## {task['name']}\n\n```\n{thms}\n```\n")
        result, lean_secs = "fail", []
        with tempfile.TemporaryDirectory() as tmp:
            code = extract(claude(prompt, args.model))
            for n in range(args.rounds + 1):
                ok, diags, summary, secs = check(task, code, tmp)
                lean_secs.append(secs)
                log.append(f"### attempt {n + 1}: {summary} (Lean {secs} s)\n\n```lean\n{code}```\n")
                if ok:
                    result = "first try" if n == 0 else f"after {n} fix{'es' if n > 1 else ''}"
                    break
                log.append(f"Sent back:\n```\n{diags[:3000]}\n```\n")
                if n < args.rounds:
                    code = extract(claude(FIX.format(prompt=prompt, code=code, diags=diags[:3000]), args.model))
        size = sum(1 for l in code.splitlines() if l.strip() and not l.strip().startswith("--"))
        rows.append((task["name"], result, size, lean_secs))
        print(f"{task['name']}: {result} ({size} lines, Lean {lean_secs} s)", flush=True)
    head = "| task | result | lines | Lean s per attempt |\n|---|---|---|---|\n" + \
        "".join(f"| {n} | {r} | {s} | {t} |\n" for n, r, s, t in rows)
    log.insert(1, head)
    with open(out_path, "w") as fh:
        fh.write("\n".join(log))
    print(out_path)


if __name__ == "__main__":
    main()
