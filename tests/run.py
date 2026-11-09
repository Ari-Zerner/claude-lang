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


for f in sorted(f for f in glob.glob(os.path.join(HERE, "ok", "*.cl")) if wanted(f) and backend_ok(f)):
    r = subprocess.run([sys.executable, CLC, "run", *BACKEND, f], capture_output=True, text=True)
    want = open(f[:-3] + ".out").read()
    if skip(r, os.path.relpath(f, HERE)):
        continue
    if r.returncode == 0 and r.stdout == want:
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
