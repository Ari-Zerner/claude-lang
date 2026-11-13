#!/usr/bin/env python3
"""Which goals does a loop proof leave open, and would another tactic close them?

  python3 clc.py build --emit-lean -o /tmp/x/prog prog.cl
  python3 trials/lean/goals.py /tmp/x/prog.lean FN [TACTIC] > /tmp/x/goals.lean
  lean /tmp/x/goals.lean

Since night 9 the Lean that clc writes prints its own open goals (after a `CLGAP f_j` line; `lean prog.lean`
shows them, and clc reads them to say which part of which loop failed). This script is for the other half:
it writes a Lean file with the program and fn FN's first `ensures` theorem alone, with TACTIC in place of
the closing tactic (`fail` shows every goal `mvcgen` makes), each goal it can't close printed and given up
with `sorry`. Other functions' `ensures` theorems are left out, so a proof that needs a callee's fact will
show that goal. Found night 8's two prover gaps (NOTES, night 8 step 2)."""
import re
import sys

src = open(sys.argv[1]).read()
fn = sys.argv[2]
head = src[:src.index("\n-- fn ")]  # the prelude and the program, up to the first theorem
m = re.search(rf"\ntheorem clSpec_{fn}_0 (.*?)\n  first\n  \| \((.*?)\n  \| exact clUnproved", src, re.S)
if not m:
    sys.exit(f"no loop theorem for fn {fn} in {sys.argv[1]}")
stmt, script = m.group(1), m.group(2)
lines = script.split("\n")
closing = lines[-1].strip()
m = re.match(r"all_goals first \| (\(mleave; .*?\)) \| \(\(try mleave\); ", closing)
if not m:
    sys.exit(f"fn {fn}'s proof isn't an `mvcgen` script (no loop?)")
tac = sys.argv[3] if len(sys.argv) > 3 else m.group(1)
lines[-1] = f"all_goals first | {tac} | (mleave; trace_state; sorry)"
print(head)
print(f"theorem clSpec_{fn}_0 {stmt}")
print("\n".join("  " + ln.strip() for ln in lines))
