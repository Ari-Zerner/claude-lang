#!/usr/bin/env python3
"""Fix-round trial: does a warning that names the failing part get an unproved loop fixed more often?

Each case is a function from the proof trial (trials/prove.py) whose code is right and whose proof lines
aren't: an `invariant` that is false at the start, one a pass doesn't keep, a `decreases` that doesn't go
down, a line missing for the end. Both compilers call it unproved, in different words: the old one says what
might be wrong ("either one doesn't hold when its loop starts, or a pass ... or together they aren't
enough"), the new one says what is. A fresh model gets the task, that answer and one compiler's words, as in
prove.py's fix round, and its one fix is graded with the new compiler. Same cases, same prompt, only the
compiler's words differ.

  python3 trials/provefix.py --dry                      # no model: what each compiler says about each case
  python3 trials/provefix.py [--model haiku] [--repeats 2] [--only NAME ...] [--old-clc OTHER/clc.py]

The old compiler defaults to commit f16db28 (night 8), taken out of git into a temporary directory.
Results go to trials/results/<run>-provefix-<model>.md.
"""
import argparse
import datetime
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import prove  # noqa: E402
from trial import claude  # noqa: E402

OLD_COMMIT = "f16db28"
HAIKU_RUN = os.path.join(HERE, "results", "2026-11-12-1500-prove-hard-haiku.md")

# task (in prove.py), what is wrong with the proof lines, and the body (or `recorded`: the first answer that
# task got in an earlier run).
CASES = [
    dict(task="mul", flaw="a second `invariant` line that a pass doesn't keep when `a` is negative",
         body="  var r = 0\n  for i in 0 until b\n    invariant r == a * i\n    invariant r >= 0\n"
              "    r = r + a\n  end for\n  return r\n"),
    dict(task="divide", flaw="the invariant doesn't say `r >= 0`, which the end needs",
         body="  var q = 0\n  var r = a\n  while r >= b\n    invariant q * b + r == a\n    decreases r\n"
              "    r = r - b\n    q = q + 1\n  end while\n  return q\n"),
    dict(task="sum", flaw="the invariant is one item ahead, so it is false at the start",
         body="  var t = 0\n  for i in 0 until length(xs)\n    invariant t == sum_spec(xs: xs, n: i + 1)\n"
              "    t = t + xs[i]\n  end for\n  return t\n"),
    dict(task="fib", flaw="the second `invariant` line is off by one",
         body="  var a = 0\n  var b = 1\n  for i in 0 until n\n    invariant a == fib_spec(i)\n"
              "    invariant b == fib_spec(i)\n    let t = a + b\n    a = b\n    b = t\n  end for\n  return a\n"),
    dict(task="gcd", flaw="`decreases x`, which doesn't go down when `x < y`",
         body="  var x = a\n  var y = b\n  while y != 0\n"
              "    invariant x >= 0 and y >= 0 and gcd_spec(a: x, b: y) == gcd_spec(a: a, b: b)\n"
              "    decreases x\n    let t = x % y\n    x = y\n    y = t\n  end while\n  return x\n"),
    dict(task="factorial", flaw="the invariant is one factor ahead: true at the start, not kept",
         body="  var r = 1\n  for i in 1 through n\n    invariant r == fact_spec(i)\n    r = r * i\n"
              "  end for\n  return r\n"),
    dict(task="digit_sum", flaw="the invariant doesn't say `k >= 0`",
         body="  var k = n\n  var s = 0\n  while k >= 10\n"
              "    invariant s + digits_spec(k) == digits_spec(n)\n    decreases k\n"
              "    s = s + k % 10\n    k = k / 10\n  end while\n  return s + k\n"),
    dict(task="bsearch", flaw="the invariant doesn't say `hi <= length(xs)`",
         body="  var lo = 0\n  var hi = length(xs)\n  while lo < hi\n    invariant lo >= 0\n"
              "    decreases hi - lo\n    let mid = (lo + hi) / 2\n    if xs[mid] == want\n      return mid\n"
              "    end if\n    if xs[mid] < want\n      lo = mid + 1\n    else\n      hi = mid\n    end if\n"
              "  end while\n  return -1\n"),
    dict(task="is_sorted", flaw="Haiku's own first answer: its invariant is false at the start",
         recorded=HAIKU_RUN),
]


def old_compiler(tmp):
    """Night 8's clc.py and cl_lean.py, out of git, in `tmp`. Returns the path of its clc.py."""
    for name in ("clc.py", "cl_lean.py"):
        src = subprocess.run(["git", "-C", ROOT, "show", f"{OLD_COMMIT}:{name}"], capture_output=True, text=True,
                             check=True).stdout
        with open(os.path.join(tmp, name), "w") as fh:
            fh.write(src)
    return os.path.join(tmp, "clc.py")


def grade_with(clc, t, code):
    prove.CLC = clc
    with tempfile.TemporaryDirectory() as tmp:
        return prove.grade(t, code, tmp)


def warnings(said):
    """The compiler's `unproved` lines, without the source excerpt under each."""
    return "\n".join(ln for ln in said.splitlines() if "warning[unproved]" in ln)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--dry", action="store_true", help="show what each compiler says; no model is called")
    ap.add_argument("--old-clc", help=f"the compiler whose words are the old arm (default: commit {OLD_COMMIT})")
    args = ap.parse_args()
    new_clc = os.path.join(ROOT, "clc.py")
    spec = open(os.path.join(ROOT, "SPEC.md")).read()
    tasks = {t["name"]: t for t in prove.TASKS + prove.HARD}
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d-%H%M")
    out_path = os.path.join(HERE, "results", f"{stamp}-provefix-{'dry' if args.dry else args.model}.md")
    log, rows, totals = [f"# Fix-round trial {stamp} ({'no model' if args.dry else args.model})\n"], [], {}
    with tempfile.TemporaryDirectory() as old_dir:
        arms = [("old", os.path.abspath(args.old_clc) if args.old_clc else old_compiler(old_dir)),
                ("new", new_clc)]
        for c in CASES:
            if args.only and c["task"] not in args.only:
                continue
            t = tasks[c["task"]]
            if "recorded" in c:
                code = prove.recorded(c["recorded"])[t["name"]]
            else:
                code = t["header"] + c["body"] + f"end fn {t['name']}\n"
            log.append(f"## {t['name']}\n\nThe flaw: {c['flaw']}.\n\n```cl\n{code}```\n")
            row = [t["name"], c["flaw"]]
            for arm, clc in arms:
                verdict, said = grade_with(clc, t, code)
                log.append(f"### the {arm} compiler: {verdict}\n\n```\n{warnings(said) or said}\n```\n")
                print(f"{t['name']} [{arm}]: {verdict}", flush=True)
                if verdict != "unproved":
                    row.append(f"({verdict}, not sent)")
                    continue
                if args.dry:
                    row.append("unproved")
                    continue
                fixed = 0
                for n in range(1, args.repeats + 1):
                    reply = claude(prove.FIX_PROMPT.format(spec=spec, code=code, said=said, **prove.fields(t)),
                                   args.model)
                    fix = prove.extract(reply, t["name"])
                    v2, said2 = grade_with(new_clc, t, fix)
                    fixed += v2 == "proved"
                    log.append(f"#### fix {n} after the {arm} words: {v2}\n\n```cl\n{fix}```\n")
                    if v2 != "proved":
                        log.append(f"```\n{warnings(said2) or said2}\n```\n")
                    print(f"{t['name']} [{arm}] fix {n}: {v2}", flush=True)
                row.append(f"{fixed} of {args.repeats}")
                got = totals.setdefault(arm, [0, 0])
                got[0] += fixed
                got[1] += args.repeats
            rows.append(row)
    head = "| case | the flaw | old words | new words |\n|---|---|---|---|\n"
    table = head + "".join("| " + " | ".join(r) + " |\n" for r in rows)
    if totals:
        table += "\n" + "; ".join(f"{arm} words: {a} of {b} fixes proved" for arm, (a, b) in totals.items()) + "\n"
    log.insert(1, table)
    with open(out_path, "w") as fh:
        fh.write("\n".join(log))
    print(table)
    print(out_path)


if __name__ == "__main__":
    main()
