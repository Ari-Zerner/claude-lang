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
               "(no tests, no `if __name__` block). "}


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


def execute(lang, task, code, args, tmp):
    """(status, output, stderr) for one call: status is 'built-fail' for a claude-lang build error."""
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
        with open(os.path.join(tmp, "runner.py"), "w") as fh:
            fh.write(FMT_SRC + f"\nfrom sol import {task['name']}\n"
                     f"print(fmt({call_py(task, args)}, {task['ret']!r}))\n")
        rc, out, err = run([sys.executable, "runner.py"], tmp)
        err = "\n".join(err.strip().splitlines()[-6:])
    return ("ran" if rc == 0 else "error"), out, err


def selftest():
    """Every expected value, written as a claude-lang literal and printed, must read back as fmt() says."""
    bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        for task in TASKS:
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
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(1 if selftest() else 0)
    spec = open(os.path.join(ROOT, "SPEC.md")).read()
    lang, fence = args.lang, {"cl": "cl", "py": "python"}[args.lang]
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d-%H%M")
    out_path = os.path.join(HERE, "results", f"{stamp}-hidden-{lang}-{args.model}.md")
    rows, log = [], [f"# Hidden-input trial {stamp} ({lang}, {args.model})\n"]
    totals = dict(ok=0, wrong=0, error=0)
    for task in TASKS:
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
                status, out, err = execute(lang, task, code, task["shown"], tmp)
                good = status == "ran" and out == want(task, task["shown"]) + "\n"
                log.append(f"### attempt {n}: {'shown example OK' if good else status}\n\n```{fence}\n{code}```\n")
                if good or n == 2:
                    break
                diags = err.strip() if status != "ran" else \
                    f"(it printed:\n{out.strip()}\ninstead of:\n{want(task, task['shown'])})"
                log.append(f"Diagnostics sent back:\n```\n{diags}\n```\n")
                what = "The compiler said:" if status == "build-fail" else "Running the example gave:"
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
        examples = len(re.findall(r"^\s*example ", code, re.M)) if lang == "cl" else 0
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
