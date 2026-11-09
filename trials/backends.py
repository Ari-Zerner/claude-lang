#!/usr/bin/env python3
"""Run every claude-lang program the trials produced through both backends and compare (D26).

Pulls each ```cl block out of trials/results/*.md, drops duplicates and anything the current front end
rejects (older attempts, or programs written before a later language change), then runs each program with
`clc.py run` (or `test`, without `fn main`) on C and on Lean and compares exit code, stdout and stderr.

    python3 trials/backends.py [--limit N] [name-filter...]

Writes a report to trials/results/<date>-backends.md and prints a summary line.
"""
import glob
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CLC = os.path.join(HERE, "..", "clc.py")


def programs(filters):
    seen = set()
    for md in sorted(glob.glob(os.path.join(HERE, "results", "*.md"))):
        if filters and not any(f in os.path.basename(md) for f in filters):
            continue
        text = open(md, encoding="utf-8").read()
        for m in re.finditer(r"^```cl\n(.*?)^```", text, re.S | re.M):
            src = m.group(1)
            h = hashlib.sha1(src.encode()).hexdigest()[:10]
            if h in seen:
                continue
            seen.add(h)
            line = text.count("\n", 0, m.start()) + 1
            yield f"{os.path.basename(md)}:{line}", src


def run(path, cmd, backend, tmp):
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, CLC, cmd, "--backend", backend, path], capture_output=True, text=True,
                           timeout=300, cwd=tmp)
        res = (r.returncode, r.stdout, r.stderr)
    except subprocess.TimeoutExpired:
        res = ("timeout", "", "")
    return res, time.time() - t0


def main():
    argv = sys.argv[1:]
    limit = None
    if "--limit" in argv:
        i = argv.index("--limit")
        limit = int(argv[i + 1])
        del argv[i:i + 2]
    tmp = tempfile.mkdtemp(prefix="backends-")
    rows, same, differ, skipped, unsupported = [], 0, 0, 0, 0
    lean_time = c_time = 0.0
    for n, (where, src) in enumerate(programs(argv)):
        if limit is not None and same + differ + unsupported >= limit:
            break
        path = os.path.join(tmp, "prog.cl")  # one name, so file names in messages agree across programs
        with open(path, "w") as fh:
            fh.write(src)
        chk = subprocess.run([sys.executable, CLC, "check", path], capture_output=True, text=True, cwd=tmp)
        if chk.returncode != 0:
            skipped += 1
            continue
        cmd = "run" if re.search(r"^fn main\(", src, re.M) else "test"
        c, tc = run(path, cmd, "c", tmp)
        lean, tl = run(path, cmd, "lean", tmp)
        c_time += tc
        lean_time += tl
        if lean[0] == 3:
            unsupported += 1
            rows.append(f"- UNSUPPORTED {where}: {lean[2].strip()}")
        elif c == lean:
            same += 1
            rows.append(f"- same {where} ({cmd}, exit {c[0]}, {len(c[1].splitlines())} lines; C {tc:.1f} s, "
                        f"Lean {tl:.1f} s)")
        else:
            differ += 1
            rows.append(f"- **DIFFER** {where} ({cmd}): C exit {c[0]}, Lean exit {lean[0]}\n"
                        f"  - C stdout {c[1][:300]!r} stderr {c[2][:300]!r}\n"
                        f"  - Lean stdout {lean[1][:300]!r} stderr {lean[2][:600]!r}")
        print(rows[-1], flush=True)
    summary = (f"{same} same, {differ} differ, {unsupported} unsupported on Lean, {skipped} skipped (rejected by "
               f"the current front end); total build+run time C {c_time:.0f} s, Lean {lean_time:.0f} s")
    out = os.path.join(HERE, "results", time.strftime("%Y-%m-%d-%H%M") + "-backends.md")
    with open(out, "w") as fh:
        fh.write("# Trial programs through both backends (D26)\n\n" + summary + "\n\n" + "\n".join(rows) + "\n")
    print(summary)
    print(f"report: {os.path.relpath(out, os.path.join(HERE, '..'))}")


if __name__ == "__main__":
    main()
