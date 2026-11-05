#!/usr/bin/env python3
"""Fix-loop trial: do the diagnostics (D10) let a fresh model fix a broken program in one go?

Each case takes a correct base program, plants one typical mistake, and checks that the compiler
reports the expected error code. A fresh `claude -p` then gets SPEC.md, what the program is for,
the broken program and the compiler output, and must reply with a fixed program; it passes if
that compiles and prints what the base program prints.

Two variants of the compiler output:
  full   everything clc prints: location, code, message, the source line, a caret, `fix:`
  brief  only the first line of each diagnostic (location, code, message)

  python3 trials/fixloop.py [--model haiku] [--variants full brief] [--only CASE ...]
"""
import argparse
import datetime
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trial import CLC, HERE, ROOT, attempt, claude, extract  # noqa: E402

BASES = {
    "gcd": ("Print the greatest common divisor of 48 and 36.", """\
fn gcd(a: Int, b: Int) -> Int
  example gcd(a: 12, b: 18) == 6
  example gcd(a: 7, b: 0) == 7
  if b == 0
    return a
  end if
  return gcd(a: b, b: a % b)
end fn gcd

fn main() uses io
  print(gcd(a: 48, b: 36))
end fn main
"""),
    "divsum": ("Print whether 28 is a perfect number, whether 12 is, and the sum of the proper divisors "
               "of 100.", """\
fn divisor_sum(n: Int) -> Int
  example divisor_sum(6) == 6
  example divisor_sum(12) == 16
  var total = 0
  var i = 1
  while i < n
    if n % i == 0
      total = total + i
    end if
    i = i + 1
  end while
  return total
end fn divisor_sum

fn is_perfect(n: Int) -> Bool
  example is_perfect(6)
  return divisor_sum(n) == n
end fn is_perfect

fn main() uses io
  print(is_perfect(28))
  print(is_perfect(12))
  print(divisor_sum(100))
end fn main
"""),
    "basics": ("Print 10 factorial, the sign of -7, and whether 10 is even and 3 is odd.", """\
fn factorial(n: Int) -> Int
  example factorial(0) == 1
  example factorial(5) == 120
  var result = 1
  var i = 2
  while i <= n
    result = result * i
    i = i + 1
  end while
  return result
end fn factorial

fn sign(x: Int) -> Int
  example sign(-4) == -1
  example sign(0) == 0
  if x < 0
    return -1
  else if x == 0
    return 0
  else
    return 1
  end if
end fn sign

fn is_even(n: Int) -> Bool
  example is_even(4)
  example not is_even(7)
  return n % 2 == 0
end fn is_even

fn main() uses io
  print(factorial(10))
  print(sign(-7))
  print(is_even(10) and not is_even(3))
end fn main
"""),
    "countdown": ("Print the numbers from 5 down to 1, then 0.", """\
fn countdown(n: Int) uses io
  var i = n
  while i >= 1
    print(i)
    i = i - 1
  end while
end fn countdown

fn main() uses io
  countdown(5)
  print(0)
end fn main
"""),
}

# (name, base, [(old, new), ...], expected error code)
CASES = [
    ("arg-order", "gcd", [("print(gcd(a: 48, b: 36))", "print(gcd(b: 36, a: 48))")], "arg-order"),
    ("unnamed", "gcd", [("print(gcd(a: 48, b: 36))", "print(gcd(48, 36))")], "unnamed-arg"),
    # Was a trap until 2026-11-05: the `fix:` said to put `end if` above `end while`, which would
    # pull `i = i + 1` into the `if` and loop forever. Now the fix uses indentation and says
    # "above line 10 (`i = i + 1`)".
    ("lost-end-if", "divsum", [("      total = total + i\n    end if\n", "      total = total + i\n")],
     "closer-mismatch"),
    ("ampersands", "divsum", [("  return divisor_sum(n) == n", "  return n > 1 && divisor_sum(n) == n")],
     "bad-char"),
    ("shadowing", "divsum", [("  return divisor_sum(n) == n",
                              "  let total = divisor_sum(n)\n  let total = total - n\n  return total == 0")],
     "duplicate-name"),
    ("not-int", "divsum", [("    if n % i == 0", "    if not (n % i)")], "type-mismatch"),
    ("missing-io", "countdown", [("fn countdown(n: Int) uses io", "fn countdown(n: Int)")], "missing-effect"),
    ("let-not-var", "countdown", [("  var i = n", "  let i = n")], "assign-to-let"),
    ("elif", "basics", [("  else if x == 0", "  elif x == 0")], "syntax"),
    ("off-by-one", "basics", [("  while i <= n\n    result", "  while i < n\n    result")], "example-failed"),
    ("no-ret-type", "basics", [("fn is_even(n: Int) -> Bool", "fn is_even(n: Int)")],
     "unexpected-return-value"),
]

FIX_PROMPT = """Below is the complete specification of a new programming language, claude-lang.

<spec>
{spec}
</spec>

This program is meant to do the following: {task}

```cl
{code}```

The compiler said:
```
{diags}
```

Reply with only the corrected program, in one ```cl code block."""


def compile_errors(code):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "prog.cl")
        with open(path, "w") as fh:
            fh.write(code)
        r = subprocess.run([sys.executable, CLC, "test", path], capture_output=True, text=True, cwd=tmp)
        return r.returncode, r.stderr.replace(tmp + "/", "")


def brief(diags):
    return "\n".join(l for l in diags.splitlines() if re.search(r": (error|warning)\[", l) or
                     re.match(r"\d+ error", l))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--variants", nargs="*", default=["full", "brief"])
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()
    spec = open(os.path.join(ROOT, "SPEC.md")).read()

    # The bases must be right, and each planted mistake must produce the expected error.
    want = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, (_, code) in BASES.items():
            rc, out, err = attempt(code, tmp)
            assert rc == 0, f"base {name} doesn't work:\n{err}"
            want[name] = out
    cases = []
    for name, base, edits, code_want in CASES:
        if args.only and name not in args.only:
            continue
        code = BASES[base][1]
        for old, new in edits:
            assert old in code, f"{name}: {old!r} not in base {base}"
            code = code.replace(old, new, 1)
        rc, diags = compile_errors(code)
        assert rc == 1 and f"[{code_want}]" in diags, f"{name}: expected {code_want}, got:\n{diags}"
        cases.append((name, base, code, diags))

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d-%H%M")
    out_path = os.path.join(HERE, "results", f"{stamp}-fixloop-{args.model}.md")
    table, log = {}, []
    for name, base, code, diags in cases:
        log.append(f"## {name}\n\nBroken program (base `{base}`):\n```cl\n{code}```\nFull compiler output:\n"
                   f"```\n{diags.strip()}\n```\n")
        for variant in args.variants:
            shown = diags.strip() if variant == "full" else brief(diags)
            reply = claude(FIX_PROMPT.format(spec=spec, task=BASES[base][0], code=code, diags=shown), args.model)
            fixed = extract(reply)
            with tempfile.TemporaryDirectory() as tmp:
                rc, out, err = attempt(fixed, tmp)
            ok = rc == 0 and out == want[base]
            verdict = "fixed" if ok else ("ran, wrong output" if rc == 0 else
                                          "never finished" if rc == 124 else f"still broken (exit {rc})")
            table.setdefault(name, {})[variant] = verdict
            log.append(f"### {variant}: {verdict}\n\n```cl\n{fixed}```\n")
            if not ok:
                log.append(f"Result:\n```\n{(err or out).strip()[:1500]}\n```\n")
            print(f"{name} [{variant}]: {verdict}", flush=True)

    head = [f"# Fix-loop trial {stamp} ({args.model})\n",
            "| case | " + " | ".join(args.variants) + " |", "|---|" + "---|" * len(args.variants)]
    for name, row in table.items():
        head.append(f"| {name} | " + " | ".join(row.get(v, "") for v in args.variants) + " |")
    with open(out_path, "w") as fh:
        fh.write("\n".join(head) + "\n\n" + "\n".join(log))
    print(out_path)


if __name__ == "__main__":
    main()
