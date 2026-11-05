#!/usr/bin/env python3
"""Spec trials: can a fresh Claude, given only SPEC.md, write working claude-lang?

For each task: ask a headless `claude -p` (no tools) for a program, compile it with clc.py,
and if it fails, hand back the diagnostics once and ask for a fixed version. Every attempt,
diagnostic and output is written to trials/results/<run>.md; those mistakes are design input.

  python3 trials/trial.py [--model sonnet] [--only NAME ...]
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

TASKS = [
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
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()
    spec = open(os.path.join(ROOT, "SPEC.md")).read()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d-%H%M")
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    out_path = os.path.join(HERE, "results", f"{stamp}-{args.model}.md")
    rows, log = [], [f"# Spec trial {stamp} ({args.model})\n"]
    for name, task, want in TASKS:
        if args.only and name not in args.only:
            continue
        log.append(f"## {name}\n\nTask: {task}\n")
        with tempfile.TemporaryDirectory() as tmp:
            code = extract(claude(PROMPT.format(spec=spec, task=task), args.model))
            result = "fail"
            for n in (1, 2):
                rc, out, err = attempt(code, tmp)
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
