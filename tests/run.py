#!/usr/bin/env python3
"""Compiler tests. tests/ok/X.cl must build, pass its examples and print exactly X.out.
tests/err/X.cl must fail with exactly the error codes on its first line (`# expect: a b`)."""
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CLC = os.path.join(HERE, "..", "clc.py")
# Tests run on clc's default backend, Lean (D26); `--backend c` runs them on C. A program a backend can't emit
# (clc exits 3) is skipped, not failed. Only the files matching an optional name filter run, e.g. `run.py --backend lean gcd`.
argv = sys.argv[1:]
BACKEND = ["--backend", argv[argv.index("--backend") + 1]] if "--backend" in argv else []
ONLY = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] != "--backend")]
failed = passed = skipped = 0


def wanted(f):
    return not ONLY or any(o in os.path.basename(f) for o in ONLY)


def backend_ok(f):
    """A test can name the backends it's for on its first line, e.g. `# backends: lean` (Int past 64 bits)."""
    m = re.match(r"#\s*backends:\s*(.*)", open(f).readline())
    name = BACKEND[1] if BACKEND else "lean"
    return m is None or name in m.group(1).split()


def skip(r, what):
    global skipped
    if r.returncode == 3 and BACKEND:
        skipped += 1
        print(f"SKIP {what}: {r.stderr.strip()}")
        return True
    return False


def termination(f, tmp):
    """`# total: a b` and `# partial: c` lines (D28) must match what the generated Lean says about each
    recursive function. Builds f into tmp; returns (binary, problems) or None when f has no such lines."""
    src = open(f).read()
    total = " ".join(re.findall(r"^#\s*total:(.*)$", src, re.M)).split()
    partial = " ".join(re.findall(r"^#\s*partial:(.*)$", src, re.M)).split()
    if not (total or partial) or (BACKEND and BACKEND[1] != "lean"):
        return None
    exe = os.path.join(tmp, "prog")
    subprocess.run([sys.executable, CLC, "build", "--emit-lean", "-o", exe, f], capture_output=True, text=True)
    lean = open(exe + ".lean").read() if os.path.exists(exe + ".lean") else ""
    said_total = set(re.findall(r"(\w+): ", " ".join(re.findall(r"^-- terminates \(D28\), measure (.*)$", lean, re.M))))
    said_partial = set(" ".join(re.findall(r"^-- partial: clc found no reason (.*) must stop", lean, re.M))
                       .replace(" and ", " ").split())
    problems = [f"{n} should be total" for n in total if n not in said_total]
    problems += [f"{n} should be partial" for n in partial if n not in said_partial]
    return exe, problems


def unproved_problems(f):
    """A program with `ensures` (D30) must leave unproved exactly the lines its `# unproved: 17 18` line lists."""
    src = open(f).read()
    if not re.search(r"^\s*ensures ", src, re.M) or (BACKEND and BACKEND[1] != "lean"):
        return None
    want = sorted(int(x) for x in " ".join(re.findall(r"^#\s*unproved:(.*)$", src, re.M)).split())
    r = subprocess.run([sys.executable, CLC, "test", "--json", f], capture_output=True, text=True)
    try:
        got = sorted(d["line"] for d in json.loads(r.stderr or "[]") if d["code"] == "unproved")
    except json.JSONDecodeError:
        return f"`clc test --json` didn't give JSON: {r.stderr[:500]}"
    return None if got == want else f"unproved `ensures` on lines {got}, expected {want}"


import tempfile
for f in sorted(f for f in glob.glob(os.path.join(HERE, "ok", "*.cl")) if wanted(f) and backend_ok(f)):
    with tempfile.TemporaryDirectory() as tmp:
        term = termination(f, tmp)
        if term:
            r = subprocess.run([term[0]], capture_output=True, text=True)
        else:
            r = subprocess.run([sys.executable, CLC, "run", *BACKEND, f], capture_output=True, text=True)
    want = open(f[:-3] + ".out").read()
    if skip(r, os.path.relpath(f, HERE)):
        continue
    unproved = unproved_problems(f)
    if term and term[1]:
        failed += 1
        print(f"FAIL {os.path.relpath(f, HERE)}: {'; '.join(term[1])}")
    elif unproved:
        failed += 1
        print(f"FAIL {os.path.relpath(f, HERE)}: {unproved}")
    elif r.returncode == 0 and r.stdout == want:
        passed += 1
    else:
        failed += 1
        print(f"FAIL {os.path.relpath(f, HERE)}: exit {r.returncode}\n--- stdout\n{r.stdout}--- want\n{want}"
              f"--- stderr\n{r.stderr}")
for f in sorted(filter(wanted, glob.glob(os.path.join(HERE, "err", "*.cl")))):
    m = re.match(r"#\s*expect:\s*(.*)", open(f).readline())
    want = sorted(m.group(1).split())
    r = subprocess.run([sys.executable, CLC, "test", "--json", *BACKEND, f], capture_output=True, text=True)
    if skip(r, os.path.relpath(f, HERE)):
        continue
    try:
        diags = json.loads(r.stderr or "[]")
    except json.JSONDecodeError:
        diags = None
    got = None if diags is None else sorted(d["code"] for d in diags if d["severity"] == "error")
    mentions = re.findall(r"^#\s*fix-mentions:\s*(.*)$", open(f).read(), re.M)
    fixes = " ".join(d.get("fix", "") for d in diags or [])
    missing = [m for m in mentions if m not in fixes]
    if missing:
        got = f"{got}, but no fix mentions {missing}"
    if r.returncode == 1 and got == want:
        passed += 1
    else:
        failed += 1
        print(f"FAIL {os.path.relpath(f, HERE)}: want {want}, got {got} (exit {r.returncode})")
        print(subprocess.run([sys.executable, CLC, "check", f], capture_output=True, text=True).stderr)
# Every complete program in SPEC.md (a code block with `fn main`) must build and pass its examples.
import tempfile
spec = open(os.path.join(HERE, "..", "SPEC.md")).read()
for i, block in enumerate(re.findall(r"```\n(.*?)```", spec, re.S)):
    if "fn main" not in block or (ONLY and "spec" not in ONLY):
        continue
    with tempfile.NamedTemporaryFile("w", suffix=".cl", delete=False) as fh:
        fh.write(block)
    r = subprocess.run([sys.executable, CLC, "test", *BACKEND, fh.name], capture_output=True, text=True)
    os.unlink(fh.name)
    if skip(r, f"SPEC.md code block {i + 1}"):
        continue
    if r.returncode == 0:
        passed += 1
    else:
        failed += 1
        print(f"FAIL SPEC.md code block {i + 1}:\n{r.stderr}")
print(f"{passed} passed, {failed} failed" + (f", {skipped} skipped" if skipped else ""))
sys.exit(1 if failed else 0)
