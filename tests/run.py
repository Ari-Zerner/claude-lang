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
failed = passed = 0
for f in sorted(glob.glob(os.path.join(HERE, "ok", "*.cl"))):
    r = subprocess.run([sys.executable, CLC, "run", f], capture_output=True, text=True)
    want = open(f[:-3] + ".out").read()
    if r.returncode == 0 and r.stdout == want:
        passed += 1
    else:
        failed += 1
        print(f"FAIL {os.path.relpath(f, HERE)}: exit {r.returncode}\n--- stdout\n{r.stdout}--- want\n{want}"
              f"--- stderr\n{r.stderr}")
for f in sorted(glob.glob(os.path.join(HERE, "err", "*.cl"))):
    m = re.match(r"#\s*expect:\s*(.*)", open(f).readline())
    want = sorted(m.group(1).split())
    r = subprocess.run([sys.executable, CLC, "test", "--json", f], capture_output=True, text=True)
    try:
        diags = json.loads(r.stderr or "[]")
    except json.JSONDecodeError:
        diags = None
    got = None if diags is None else sorted(d["code"] for d in diags if d["severity"] == "error")
    if r.returncode == 1 and got == want:
        passed += 1
    else:
        failed += 1
        print(f"FAIL {os.path.relpath(f, HERE)}: want {want}, got {got} (exit {r.returncode})")
        print(subprocess.run([sys.executable, CLC, "check", f], capture_output=True, text=True).stderr)
print(f"{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
