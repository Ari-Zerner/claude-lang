#!/usr/bin/env python3
"""Spec trials: can a fresh Claude, given only SPEC.md, write working claude-lang?

For each task: ask a headless `claude -p` (no tools) for a program, compile it with clc.py,
and if it fails, hand back the diagnostics once and ask for a fixed version. Every attempt,
diagnostic and output is written to trials/results/<run>.md; those mistakes are design input.

  python3 trials/trial.py [--set basic|hard|lists] [--model sonnet] [--only NAME ...]
"""
import argparse
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

BASIC = [
    ("fib", "Print the first 15 Fibonacci numbers, starting 0, 1, one per line.",
     "".join(f"{x}\n" for x in [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377])),
    ("primes", "Print every prime number below 50, one per line, in increasing order.",
     "".join(f"{p}\n" for p in range(2, 50) if all(p % q for q in range(2, p)))),
    ("collatz", "Print how many steps the Collatz process (n -> n/2 if even, 3n+1 if odd) takes to "
     "reach 1 starting from 27.", "111\n"),
    ("isqrt", "Print the integer square root (the floor of the square root) of 1000000007, computed "
     "with binary search.", "31622\n"),
    ("digits", "Print the sum of the decimal digits of 2 to the power 20.", "31\n"),
    ("perfect", "A perfect number equals the sum of its proper divisors. Print whether 28 is perfect, "
     "then whether 12 is perfect (one result per line).", "true\nfalse\n"),
]

# Tasks that push on what's missing (no break, strings or lists) or easy to get wrong. A
# want of None means there's no single right output; the result is recorded for reading.
HARD = [
    ("first-big-fib", "Print the first Fibonacci number that has more than 10 decimal digits.",
     "12586269025\n"),
    ("triangle", "The n-th triangular number is 1 + 2 + ... + n. Print the smallest n whose triangular "
     "number has more than 50 divisors.", "224\n"),
    ("next-prime", "Print the first prime number greater than 10000.", "10007\n"),
    ("even-odd", "Write two mutually recursive functions is_even and is_odd that don't use `%`, `/` "
     "or `*`. Print is_even(10), then is_even(7).", "true\nfalse\n"),
    ("clamp", "Write a function clamp that takes a value, a lower bound and an upper bound. Print the "
     "result of clamping 15, then -5, then 5, each to the range 0 to 10.", "10\n0\n5\n"),
    ("countdown", "Write a function that prints the numbers from n down to 1, one per line. From main, "
     "call it with 5 and then print 0.", "5\n4\n3\n2\n1\n0\n"),
    ("coins", "Print the number of different ways to make 100 cents from coins of 1, 5, 10, 25 and 50 "
     "cents (order doesn't matter).", "292\n"),
    ("table", "Print a multiplication table for 1 to 4: four lines, each with the four products "
     "separated by single spaces.", "1 2 3 4\n2 4 6 8\n3 6 9 12\n4 8 12 16\n"),
]
# Tasks that need lists (D19), several aimed at other languages' habits: methods, `+` on lists,
# negative indexing, nested assignment, `[0] * n`, and aliasing.
LISTS = [
    ("fib-list", "Build a list of the first 10 Fibonacci numbers (starting 0, 1) and print the list.",
     "[0, 1, 1, 2, 3, 5, 8, 13, 21, 34]\n"),
    ("reverse", "Write a function that returns a list in reverse order. Print the reverse of [1, 2, 3, 4, 5].",
     "[5, 4, 3, 2, 1]\n"),
    ("sieve", "Use the sieve of Eratosthenes (a list of Bools) to find the primes below 100. Print how many "
     "there are, then the largest one.", "25\n97\n"),
    ("dedupe", "Remove duplicates from [3, 1, 3, 2, 1, 5], keeping the first occurrence of each, and print "
     "the resulting list.", "[3, 1, 2, 5]\n"),
    ("words", "Given the list of words apple, kiwi, banana, fig: print the longest word, then the total "
     "number of characters in all the words.", "banana\n18\n"),
    ("last-two", "Print the last item of [4, 8, 15, 16, 23, 42], then the second-to-last.", "42\n23\n"),
    ("join", "Write a function that joins two lists of Ints into one. Print the result of joining [1, 2] "
     "and [3, 4, 5].", "[1, 2, 3, 4, 5]\n"),
    ("grid", "Build a 3 by 3 grid (a list of lists) where the item in row i, column j is i * j (counting "
     "from 0). Then change the middle item to 100 and print the grid.", "[[0, 0, 0], [0, 100, 2], [0, 2, 4]]\n"),
    ("doubled", "Write a function that takes a list of Ints and returns it with its first item doubled. "
     "Call it on a list holding 1, 2, 3, then print the result, then print the original list.",
     "[2, 2, 3]\n[1, 2, 3]\n"),
    ("sort", "Sort [5, 2, 8, 1, 9, 3] with a sorting algorithm you write yourself and print the sorted list.",
     "[1, 2, 3, 5, 8, 9]\n"),
    ("merge", "Write a function that merges two sorted lists into one sorted list. Print the merge of "
     "[1, 4, 9] and [2, 3, 10, 11].", "[1, 2, 3, 4, 9, 10, 11]\n"),
]
SETS = {"basic": BASIC, "hard": HARD, "lists": LISTS}

PROMPT = """Below is the complete specification of a new programming language, claude-lang.
You have never seen it before; rely only on this spec.

<spec>
{spec}
</spec>

Task: write a complete claude-lang program that does this:
{task}

Print exactly what the task asks for, with no labels or other text.
Reply with only the program, in one ```cl code block."""

FIX_PROMPT = """Below is the complete specification of a new programming language, claude-lang.

<spec>
{spec}
</spec>

You were asked to write a program that does this:
{task}

You wrote:
```cl
{code}
```

The compiler said:
```
{diags}
```

Reply with only the corrected program, in one ```cl code block."""


def claude(prompt, model):
    cmd = ["claude", "-p", prompt, "--restricted", "--strict-mcp-config", "--tools", "",
           "--permission-mode", "dontAsk", "--no-session-persistence", "--model", model,
           "--output-format", "json"]
    env = {k: os.environ[k] for k in ("HOME", "LANG", "TERM") if k in os.environ}
    env.update(CLAUDE_CODE_CERT_STORE="system", DISABLE_AUTOUPDATER="1", ENABLE_CLAUDEAI_MCP_SERVERS="false")
    env["PATH"] = subprocess.run(
        ["bash", "-c", ". /root/.nvm/nvm.sh >/dev/null 2>&1; . /root/bin/claude-path.sh 2>/dev/null; echo $PATH"],
        capture_output=True, text=True).stdout.strip() or os.environ.get("PATH", "")
    with tempfile.TemporaryDirectory() as cwd:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, stdin=subprocess.DEVNULL, env=env,
                           timeout=600)
    line = next((l for l in r.stdout.splitlines() if l.startswith("{")), None)
    if not line:
        raise RuntimeError(f"claude -p failed: {(r.stderr or r.stdout)[-300:]}")
    return json.loads(line).get("result", "")


def extract(reply):
    """The program in a reply: the code block with `fn main` (the last such), else the last block."""
    blocks = re.findall(r"```[a-zA-Z]*\n(.*?)```", reply, re.S)
    mains = [b for b in blocks if "fn main" in b]
    return ((mains or blocks or [reply])[-1]).strip() + "\n"


def attempt(code, tmp):
    path = os.path.join(tmp, "prog.cl")
    with open(path, "w") as fh:
        fh.write(code)
    # Own process group, so a program that never ends is killed along with clc.
    p = subprocess.Popen([sys.executable, CLC, "run", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, cwd=tmp, start_new_session=True)
    try:
        out, err = p.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        out, err = p.communicate()
        return 124, out, "(the program was still running after 20 s and was stopped)"
    return p.returncode, out, err.replace(tmp + "/", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--set", choices=sorted(SETS), default="basic")
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()
    spec = open(os.path.join(ROOT, "SPEC.md")).read()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d-%H%M")
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    out_path = os.path.join(HERE, "results", f"{stamp}-{args.set}-{args.model}.md")
    rows, log = [], [f"# Spec trial {stamp} ({args.set} tasks, {args.model})\n"]
    for name, task, want in SETS[args.set]:
        if args.only and name not in args.only:
            continue
        log.append(f"## {name}\n\nTask: {task}\n")
        with tempfile.TemporaryDirectory() as tmp:
            code = extract(claude(PROMPT.format(spec=spec, task=task), args.model))
            result = "fail"
            for n in (1, 2):
                rc, out, err = attempt(code, tmp)
                if want is None and rc == 0:  # no single right answer: record it and stop
                    log.append(f"### attempt {n}: compiled (open-ended task)\n\n```cl\n{code}```\n"
                               f"Output:\n```\n{out}```\n")
                    if err.strip():
                        log.append(f"Compiler:\n```\n{err.strip()}\n```\n")
                    result = "compiled (open-ended)" + (" after one fix" if n == 2 else "")
                    break
                ok = rc == 0 and out == want
                log.append(f"### attempt {n}: {'OK' if ok else 'exit ' + str(rc)}\n\n```cl\n{code}```\n")
                if err.strip():
                    log.append(f"Compiler:\n```\n{err.strip()}\n```\n")
                if rc == 0 and not ok:
                    log.append(f"Output was wrong:\n```\n{out}```\nwanted:\n```\n{want}```\n")
                if ok:
                    result = "first try" if n == 1 else "after one fix"
                    break
                if n == 1:
                    diags = err.strip() or f"(it compiled, but printed:\n{out}\ninstead of:\n{want})"
                    log.append("_Sent the diagnostics back for a fix._\n")
                    code = extract(claude(FIX_PROMPT.format(spec=spec, task=task, code=code, diags=diags),
                                          args.model))
        rows.append((name, result))
        print(f"{name}: {result}", flush=True)
    log.insert(1, "| task | result |\n|---|---|\n" + "".join(f"| {n} | {r} |\n" for n, r in rows))
    with open(out_path, "w") as fh:
        fh.write("\n".join(log))
    print(out_path)


if __name__ == "__main__":
    main()
