#!/usr/bin/env python3
"""Spec trials: can a fresh Claude, given only SPEC.md, write working claude-lang?

For each task: ask a headless `claude -p` (no tools) for a program, compile it with clc.py,
and if it fails, hand back the diagnostics once and ask for a fixed version. Every attempt,
diagnostic and output is written to trials/results/<run>.md; those mistakes are design input.

  python3 trials/trial.py [--set basic|hard] [--model sonnet] [--only NAME ...]
"""
import argparse
import datetime
import json
import os
import re
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
     "separated by spaces.", None),
]
SETS = {"basic": BASIC, "hard": HARD}

PROMPT = """Below is the complete specification of a new programming language, claude-lang.
You have never seen it before; rely only on this spec.

<spec>
{spec}
</spec>

Task: write a complete claude-lang program that does this:
{task}

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
    m = re.search(r"```[a-zA-Z]*\n(.*?)```", reply, re.S)
    return (m.group(1) if m else reply).strip() + "\n"


def attempt(code, tmp):
    path = os.path.join(tmp, "prog.cl")
    with open(path, "w") as fh:
        fh.write(code)
    r = subprocess.run([sys.executable, CLC, "run", path], capture_output=True, text=True, timeout=60, cwd=tmp)
    return r.returncode, r.stdout, r.stderr.replace(tmp + "/", "")


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
