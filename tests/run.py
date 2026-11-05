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
    if "fn main" not in block:
        continue
    with tempfile.NamedTemporaryFile("w", suffix=".cl", delete=False) as fh:
        fh.write(block)
    r = subprocess.run([sys.executable, CLC, "test", fh.name], capture_output=True, text=True)
    os.unlink(fh.name)
    if r.returncode == 0:
        passed += 1
    else:
        failed += 1
        print(f"FAIL SPEC.md code block {i + 1}:\n{r.stderr}")
print(f"{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
