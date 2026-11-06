#!/usr/bin/env python3
"""clc: the compiler for claude-lang (working name).

Pipeline: source -> tokens -> AST -> type-checked AST -> C -> gcc -> binary.
After gcc, the binary is run once with --cl-examples to check every `example` line (D8);
a failing example is a compile error.

Usage:
  clc.py check FILE          parse and type-check only
  clc.py build FILE [-o OUT] compile to a binary (default: FILE without .cl)
  clc.py run FILE            build to a temp dir and run it
  clc.py test FILE           build and report how many examples passed
Add --json for machine-readable diagnostics (on stderr), --emit-c to keep the C.

DESIGN.md explains the reasoning behind each rule (D1, D2, ...).
"""
import argparse
import difflib
import json
import os
import shutil
import subprocess
import sys
import tempfile

# ------------------------------------------------------------------ diagnostics (D10)


class Diag:
    def __init__(self, severity, code, msg, line, col, length, fix):
        self.severity, self.code, self.msg = severity, code, msg
        self.line, self.col, self.length, self.fix = line, col, length, fix

    def as_json(self, path):
        d = {"severity": self.severity, "code": self.code, "message": self.msg,
             "file": path, "line": self.line, "col": self.col, "length": self.length}
        if self.fix:
            d["fix"] = self.fix
        return d


class Diags:
    def __init__(self, path, src):
        self.path = path
        self.lines = src.split("\n")
        self.items = []
        self._seen = set()
        self.lexing, self.lex_lines = False, set()

    def add(self, severity, code, msg, line, col, length=1, fix=None):
        key = (line, col, code)
        if key in self._seen:  # one report per spot; later ones are usually cascades
            return
        if self.lexing:
            self.lex_lines.add(line)
        elif line in self.lex_lines:  # a line with a lexical error gets only that: the rest is fallout
            return
        self._seen.add(key)
        self.items.append(Diag(severity, code, msg, line, col, max(1, length), fix))

    def error(self, *a, **k):
        self.add("error", *a, **k)

    def warning(self, *a, **k):
        self.add("warning", *a, **k)

    def has_errors(self):
        return any(d.severity == "error" for d in self.items)

    def ordered(self):
        return sorted(self.items, key=lambda d: (d.line, d.col))

    def render(self):
        out = []
        for d in self.ordered():
            out.append(f"{self.path}:{d.line}:{d.col}: {d.severity}[{d.code}]: {d.msg}")
            if 1 <= d.line <= len(self.lines):
                src = self.lines[d.line - 1].replace("\t", " ")
                out.append(f"{d.line:>5} | {src}")
                out.append("      | " + " " * (d.col - 1) + "^" * d.length)
            if d.fix:
                out.append(f"  fix: {d.fix}")
        errs = sum(d.severity == "error" for d in self.items)
        warns = len(self.items) - errs
        out.append(f"{errs} error(s), {warns} warning(s)")
        return "\n".join(out)

    def report(self, as_json):
        if as_json:
            print(json.dumps([d.as_json(self.path) for d in self.ordered()], indent=1),
                  file=sys.stderr)
        elif self.items:
            print(self.render(), file=sys.stderr)


# ------------------------------------------------------------------ lexer

KEYWORDS = {"fn", "end", "if", "else", "while", "for", "break", "continue", "return", "let", "var", "example",
            "uses", "true", "false", "and", "or", "not"}
BLOCK_KINDS = ("fn", "if", "while", "for")
RANGE_FIX = "`a until b` stops before b, `a through b` includes it: `for i in 0 until n`"
TWO_CHAR_OPS = ("->", "==", "!=", "<=", ">=")
ONE_CHAR_OPS = "+-*/%<>=(),:[]"
CMP_OPS = ("==", "!=", "<", "<=", ">", ">=")
ARITH_OPS = ("+", "-", "*", "/", "%")

_BRACES = "blocks don't use braces: a block starts with its keyword and ends with `end <kind>`, e.g. `end if`"
CHAR_HINTS = {
    "{": _BRACES, "}": _BRACES,
    ";": "a statement ends at the end of its line; drop the `;`",
    "&&": "write `and`", "||": "write `or`", "!": "write `not`",
    ".": "there are no methods or fields: call a function instead, e.g. `length(xs)` or "
         "`xs = append(list: xs, item: x)` (and there are no floats)",
    "'": "strings use double quotes: `\"...\"`",
}
STRING_ESCAPES = {"n": "\n", "t": "\t", "\\": "\\", '"': '"', "{": "{", "}": "}"}


class Tok:
    __slots__ = ("kind", "text", "line", "col", "parts")

    def __init__(self, kind, text, line, col, parts=None):
        self.kind, self.text, self.line, self.col, self.parts = kind, text, line, col, parts

    def __repr__(self):
        return f"Tok({self.kind},{self.text!r},{self.line}:{self.col})"


def lex(src, d):
    """One statement per line (D13): every non-empty line ends with an `nl` token."""
    toks = []
    lines = src.split("\n")
    d.lexing = True
    for lineno, line in enumerate(lines, 1):
        before = len(toks)
        stripped = line.lstrip()
        if stripped.startswith("for") and stripped[3:].lstrip().startswith("(") and ";" in stripped:
            col = len(line) - len(stripped) + 1
            d.error("syntax", "there's no C-style `for`", lineno, col, len(stripped),
                    "count with `for i in 0 until n` (or `while` for other steps)")
            toks.append(Tok("kw", "for", lineno, col))  # keep the block open so `end for` matches
            toks.append(Tok("nl", "", lineno, len(line) + 1))
            continue
        lex_span(line, 0, len(line), lineno, d, toks)
        if len(toks) > before:
            toks.append(Tok("nl", "", lineno, len(line) + 1))
    d.lexing = False
    toks.append(Tok("eof", "", len(lines), 1))
    return toks


def lex_dot(line, i, n, lineno, d, toks):
    """`.` is never valid. Catch the two usual reasons: a method call (`xs.append(4)`, `s.len()`) and a
    float (`1.5`). Returns where to resume."""
    j = i + 1
    while j < n and (line[j].isalnum() or line[j] == "_"):
        j += 1
    m, prev = line[i + 1:j], (toks[-1] if toks else None)
    if line[i + 1:i + 2] == ".":
        k = i
        while k < n and line[k] in ".=<":
            k += 1
        d.error("bad-char", f"`{line[i:k]}` isn't a range; ranges are written with words", lineno, i + 1, k - i,
                RANGE_FIX)
        return k
    if prev is not None and prev.kind == "int" and m.isdigit():
        d.error("bad-char", "there are no floats yet; Int is the only number type", lineno, prev.col,
                j - prev.col + 1)
        return j
    if not m or not (m[0].isalpha() or m[0] == "_") or prev is None:
        d.error("bad-char", f"`.` isn't part of the language; {CHAR_HINTS['.']}", lineno, i + 1)
        return i + 1
    end, args = j, None
    if line[j:j + 1] == "(":
        depth, k = 0, j
        while k < n:
            depth += {"(": 1, ")": -1}.get(line[k], 0)
            if depth == 0:
                break
            k += 1
        if k < n:
            end, args = k + 1, line[j + 1:k].strip()
    obj = prev.text if prev.kind == "name" else None
    fix = None
    if obj and m in ("append", "push", "add", "push_back") and args:
        fix = f"`{obj} = append(list: {obj}, item: {args})`"
    elif obj and m in ("len", "length", "size", "count") and not args:
        fix = f"`length({obj})`"
    elif obj:
        fix = f"call a function with `{obj}` as an argument instead"
    d.error("method-call", f"`.{m}` doesn't exist: there are no methods or fields", lineno, i + 1, end - i, fix)
    return end


def lex_span(line, i, n, lineno, d, toks, in_interp=False):
    """Tokens for line[i:n], appended to toks (columns are real columns in the line)."""
    while i < n:
        c, col = line[i], i + 1
        if c in " \t\r":
            i += 1
        elif c == "#" and not in_interp:
            break
        elif c == "'" and not in_interp and "'" in line[i + 1:n]:
            close = line.index("'", i + 1)
            d.error("bad-char", "strings use double quotes", lineno, col, close - i + 1,
                    f"`\"{line[i + 1:close]}\"`")
            toks.append(Tok("str", line[i:close + 1], lineno, col, [("text", line[i + 1:close])]))  # recover
            i = close + 1
        elif c == '"':
            if in_interp:
                d.error("nested-string", "a string can't appear inside `{...}` in another string",
                        lineno, col, 1, "store it in a `let` first and interpolate the name")
                return
            i = lex_string(line, i, n, lineno, d, toks)
        elif c.isdigit():
            j = i
            while j < n and (line[j].isalnum() or line[j] == "_"):
                j += 1
            text = line[i:j]
            digits = text.replace("_", "")
            if not digits.isdigit():
                d.error("bad-number", f"`{text}` is neither a number nor a name (names can't start with a digit)",
                        lineno, col, len(text))
                digits = "0"
            elif int(digits) > 2**63 - 1:
                d.error("int-too-big", f"`{text}` doesn't fit in an Int (64-bit signed)", lineno, col, len(text))
                digits = "0"
            toks.append(Tok("int", digits, lineno, col))
            i = j
        elif c.isalpha() or c == "_":
            j = i
            while j < n and (line[j].isalnum() or line[j] == "_"):
                j += 1
            w = line[i:j]
            toks.append(Tok("kw" if w in KEYWORDS else "name", w, lineno, col))
            i = j
        elif line[i:i + 2] in TWO_CHAR_OPS:
            toks.append(Tok("op", line[i:i + 2], lineno, col))
            i += 2
        elif line[i:i + 2] in ("&&", "||"):
            d.error("bad-char", f"`{line[i:i+2]}` isn't an operator here; {CHAR_HINTS[line[i:i+2]]}", lineno, col, 2)
            toks.append(Tok("kw", "and" if c == "&" else "or", lineno, col))  # recover
            i += 2
        elif c == "!":
            d.error("bad-char", f"`!` isn't an operator here; {CHAR_HINTS['!']}", lineno, col, 1)
            toks.append(Tok("kw", "not", lineno, col))  # recover
            i += 1
        elif c == ".":
            i = lex_dot(line, i, n, lineno, d, toks)
        elif c in ONE_CHAR_OPS:
            toks.append(Tok("op", c, lineno, col))
            i += 1
        else:
            hint = CHAR_HINTS.get(c)
            d.error("bad-char", f"`{c}` isn't part of the language" + (f"; {hint}" if hint else ""), lineno, col)
            i += 1


def lex_string(line, i, n, lineno, d, toks):
    """A string literal starting at line[i] == '"'. Parts are ("text", str) or ("expr", tokens).
    Strings end on the line they start (D13)."""
    start, parts, buf = i, [], []
    i += 1
    while True:
        if i >= n:
            d.error("unclosed-string", "this string has no closing `\"` on its line", lineno, start + 1,
                    n - start, "strings end on the line they start; use `\\n` for a line break")
            break
        c = line[i]
        if c == '"':
            i += 1
            break
        if c == "\\":
            e = line[i + 1:i + 2]
            if e in STRING_ESCAPES:
                buf.append(STRING_ESCAPES[e])
            else:
                d.error("bad-escape", f"unknown escape `\\{e}`; the escapes are \\n \\t \\\\ \\\" \\{{ \\}}",
                        lineno, i + 1, 2)
            i += 2
            continue
        if c == "{":
            close = line.find("}", i + 1)
            if close == -1 or close >= n:
                d.error("unclosed-interpolation", "`{` starts an interpolation, but there's no `}`", lineno, i + 1,
                        1, "write `\\{` for a literal brace")
                i = n
                continue
            if buf:
                parts.append(("text", "".join(buf)))
                buf = []
            if '"' in line[i + 1:close]:
                q = line.index('"', i + 1)
                d.error("nested-string", "a string can't appear inside `{...}` in another string",
                        lineno, q + 1, 1, "store it in a `let` first and interpolate the name")
                i = close + 1
                continue
            sub = []
            lex_span(line, i + 1, close, lineno, d, sub, in_interp=True)
            if not sub:
                d.error("empty-interpolation", "`{}` has nothing inside", lineno, i + 1, 2,
                        "put an expression inside, or write `\\{}` for literal braces")
            else:
                sub.append(Tok("eof", "", lineno, close + 1))
                parts.append(("expr", sub))
            i = close + 1
            continue
        buf.append(c)
        i += 1
    if buf or not parts:
        parts.append(("text", "".join(buf)))
    toks.append(Tok("str", line[start:i], lineno, start + 1, parts))
    return i


# ------------------------------------------------------------------ AST


class Node:
    def __init__(self, kind, tok, **kw):
        self.kind, self.tok, self.start, self.ty, self.paren = kind, tok, tok, None, False
        self.__dict__.update(kw)


def render(e):
    """Source text for an expression, used in messages and in `fix:` suggestions."""
    k = e.kind
    if k == "int":
        s = str(e.value)
    elif k == "bool":
        s = "true" if e.value else "false"
    elif k == "str":
        s = '"' + "".join(escape_text(p) if kind == "text" else "{" + render(p) + "}"
                          for kind, p in e.parts) + '"'
    elif k == "name":
        s = e.name
    elif k == "call":
        s = f"{e.name}(" + ", ".join((f"{n}: " if n else "") + render(a) for n, _, a in e.args) + ")"
    elif k == "bin":
        s = f"{render(e.left)} {e.op} {render(e.right)}"
    elif k == "neg":
        s = "-" + render(e.expr)
    elif k == "not":
        s = "not " + render(e.expr)
    elif k == "list":
        s = "[" + ", ".join(render(x) for x in e.items) + "]"
    elif k == "index":
        s = f"{render(e.base)}[{render(e.index)}]"
    else:
        s = "?"
    return f"({s})" if e.paren else s


def escape_text(t):
    return (t.replace("\\", "\\\\").replace('"', '\\"').replace("{", "\\{").replace("}", "\\}")
            .replace("\n", "\\n").replace("\t", "\\t"))


def opener(kind, name):
    return f"fn {name}" if kind == "fn" else kind


def closer(kind, name):
    return f"end fn {name}" if kind == "fn" else f"end {kind}"


def bin_node(op_tok, left, right):
    n = Node("bin", op_tok, op=op_tok.text, left=left, right=right)
    n.start = left.start
    return n


def fold(operands, ops):
    e = operands[0]
    for o, r in zip(ops, operands[1:]):
        e = bin_node(o, e, r)
    return e


# ------------------------------------------------------------------ parser

TYPES = ("Int", "Bool", "String")
LIST_WORDS = ("List", "list", "Vec", "vec", "Vector", "vector", "Array", "array", "Seq", "Sequence", "Slice")
TYPE_HINTS = {"int": "Int", "i64": "Int", "i32": "Int", "Integer": "Int", "integer": "Int", "long": "Int",
              "bool": "Bool", "boolean": "Bool", "Boolean": "Bool",
              "str": "String", "Str": "String", "string": "String", "text": "String", "Text": "String"}
NO_RETURN_TYPES = ("Unit", "Void", "void", "None", "Nothing")
FN_WORDS = ("def", "func", "function", "fun", "proc")
CLOSER_WORDS = {"endif": "if", "fi": "if", "endwhile": "while", "done": "while", "endfn": "fn", "endfor": "for"}
STMT_HINTS = {"elif": "write `else if`", "elsif": "write `else if`", "elseif": "write `else if`",
              "const": "write `let` (or `var` for a variable that changes)",
              "loop": "write `while true`"}
LINE_END_HINTS = {"then": "no `then`: the block starts on the next line",
                  "do": "no `do`: the block starts on the next line",
                  ":": "no `:` after the condition: the block starts on the next line"}


class ParseError(Exception):
    pass


def describe(t):
    return {"nl": "the end of the line", "eof": "the end of the file"}.get(t.kind, f"`{t.text}`")


class Parser:
    def __init__(self, toks, d):
        self.toks, self.d, self.i = toks, d, 0
        self.stack = []  # open blocks: [kind, line, name]

    # -- token helpers
    def peek(self, k=0):
        return self.toks[min(self.i + k, len(self.toks) - 1)]

    def next(self):
        t = self.toks[self.i]
        if t.kind != "eof":
            self.i += 1
        return t

    def at(self, kind, text=None, k=0):
        t = self.peek(k)
        return t.kind == kind and (text is None or t.text == text)

    def at_kw(self, w, k=0):
        return self.at("kw", w, k)

    def at_op(self, o, k=0):
        return self.at("op", o, k)

    def at_cmp(self):
        return self.peek().kind == "op" and self.peek().text in CMP_OPS

    def fail(self, code, msg, tok, fix=None):
        self.d.error(code, msg, tok.line, tok.col, len(tok.text), fix)
        raise ParseError()

    def expect_op(self, o, what):
        if self.at_op(o):
            return self.next()
        t = self.peek()
        self.fail("syntax", f"expected `{o}` {what}, found {describe(t)}", t)

    def expect_name(self, what):
        if self.at("name"):
            return self.next()
        t = self.peek()
        extra = " (that's a keyword)" if t.kind == "kw" else ""
        self.fail("syntax", f"expected a name {what}, found {describe(t)}{extra}", t)

    def skip_line(self):
        while not self.at("nl") and not self.at("eof"):
            self.next()
        if self.at("nl"):
            self.next()

    def end_line(self):
        if self.at("nl"):
            self.next()
            return
        if self.at("eof"):
            return
        t = self.peek()
        hint = LINE_END_HINTS.get(t.text, "one statement per line: move this to its own line or remove it")
        self.d.error("extra-tokens", f"unexpected {describe(t)} after the end of the statement", t.line, t.col,
                     len(t.text), hint)
        self.skip_line()

    # -- top level
    def program(self):
        fns = []
        while True:
            while self.at("nl"):
                self.next()
            t = self.peek()
            if t.kind == "eof":
                return fns
            if t.kind == "kw" and t.text == "fn":
                fns.append(self.fn_decl())
                continue
            if t.kind == "name" and t.text in FN_WORDS:
                self.d.error("syntax", f"`{t.text}` isn't a keyword; functions are declared with `fn`",
                             t.line, t.col, len(t.text), "write `fn`")
                fns.append(self.fn_decl())
                continue
            self.d.error("top-level", f"only `fn` declarations can appear at the top level, found {describe(t)}",
                         t.line, t.col, len(t.text))
            self.skip_line()

    def parse_type(self, ret=False):
        t = self.peek()
        if t.kind != "name":
            self.fail("syntax", f"expected a type (Int, Bool, String or List[...]), found {describe(t)}", t)
        self.next()
        if t.text in LIST_WORDS or (t.text not in TYPES and (self.at_op("[") or self.at_op("<"))):
            return self.list_type(t)
        ty = self.simple_type(t, ret)
        if ty and self.at_op("[") and self.at_op("]", 1):  # Int[] (Java/C#)
            b = self.next()
            self.next()
            self.d.error("unknown-type", "list types are written `List[...]`", b.line, b.col, 2, f"`List[{ty}]`")
            return f"List[{ty}]"
        return ty

    def list_type(self, t):
        """`List[T]`, after the name; also recovers from `list[T]`, `Vec<T>`, `Array[T]`..."""
        close = "]"
        if self.at_op("<"):
            close = ">"
        elif not self.at_op("["):
            self.d.error("unknown-type", "`List` needs an item type", t.line, t.col, len(t.text), "`List[Int]`")
            return None
        b = self.next()
        inner = self.parse_type()
        self.expect_op(close, f"to close `{t.text}{b.text}...`")
        if t.text in LIST_WORDS and t.text != "List" or close == ">":
            self.d.error("unknown-type", f"list types are written `List[...]`", t.line, t.col, len(t.text),
                         f"`List[{inner or '...'}]`")
        elif t.text not in LIST_WORDS:
            self.d.error("unknown-type", f"unknown type `{t.text}`; the only type that takes `[...]` is `List`",
                         t.line, t.col, len(t.text))
        return f"List[{inner}]" if inner else None

    def simple_type(self, t, ret):
        if t.text in TYPES:
            return t.text
        if t.text in NO_RETURN_TYPES:
            msg = "functions that return nothing leave out `-> ...`" if ret else f"`{t.text}` isn't a type"
            self.d.error("unknown-type", msg, t.line, t.col, len(t.text))
            return "Unit" if ret else None
        hint = TYPE_HINTS.get(t.text) or next(iter(difflib.get_close_matches(t.text, TYPES, 1)), None)
        self.d.error("unknown-type", f"unknown type `{t.text}`; the types are Int, Bool, String and List[...]",
                     t.line, t.col,
                     len(t.text), f"write `{hint}`" if hint else None)
        return hint  # recover with the likely meaning, so one wrong name doesn't cascade

    def fn_decl(self):
        kw = self.next()
        name, name_tok, params, ret, uses_io = "?", kw, [], "Unit", False
        try:
            name_tok = self.expect_name("for the function")
            name = name_tok.text
            self.expect_op("(", f"after `fn {name}`")
            if not self.at_op(")"):
                while True:
                    pn = self.expect_name("for a parameter")
                    self.expect_op(":", f"and a type after parameter `{pn.text}`, e.g. `{pn.text}: Int`")
                    params.append((pn.text, self.parse_type(), pn))
                    if self.at_op(","):
                        self.next()
                        continue
                    break
            self.expect_op(")", "to close the parameter list")
            if self.at_op("->"):
                self.next()
                ret = self.parse_type(ret=True)
            if self.at_kw("uses"):
                self.next()
                e = self.expect_name("after `uses` (the only effect so far is `io`)")
                if e.text == "io":
                    uses_io = True
                else:
                    self.d.error("unknown-effect", f"unknown effect `{e.text}`; the only effect so far is `io`",
                                 e.line, e.col, len(e.text))
            self.end_line()
        except ParseError:
            self.skip_line()
        f = Node("fn", kw, name=name, name_tok=name_tok, params=params, ret=ret, uses_io=uses_io)
        self.stack.append(["fn", kw.line, name])
        f.body, _, f.end_tok = self.block_body()
        self.stack.pop()
        return f

    # -- blocks and closers (D2)
    def block_body(self):
        """Statements up to the closer of the innermost open block (self.stack[-1]).
        Returns (stmts, how, tok); how is 'end' (closer consumed), 'else' (stopped at an
        `else` of this `if`) or 'implicit' (the block was never closed; already reported)."""
        kind, line, name = self.stack[-1]
        stmts = []
        while True:
            while self.at("nl"):
                self.next()
            t = self.peek()
            if t.kind == "eof":
                self.d.error("unclosed-block", f"`{opener(kind, name)}` (line {line}) is never closed",
                             t.line, t.col, 1, self.closer_fix(kind, name, line, t.line))
                return stmts, "implicit", t
            if t.kind == "kw" and t.text == "end":
                how = self.closer_line()
                if how == "mine":
                    return stmts, "end", t
                if how == "outer":
                    return stmts, "implicit", t
                continue
            if t.kind == "name" and t.text in CLOSER_WORDS and self.at("nl", k=1):
                k = CLOSER_WORDS[t.text]
                self.d.error("closer-kind", f"`{t.text}` isn't a keyword; write `end {k}`",
                             t.line, t.col, len(t.text), f"`end {k}`")
                start = self.i
                self.next()
                how = self.resolve_closer(k, t, start)
                if how == "mine":
                    return stmts, "end", t
                if how == "outer":
                    return stmts, "implicit", t
                continue
            if t.kind == "kw" and t.text == "else":
                if kind == "if":
                    return stmts, "else", t
                self.d.error("stray-else", f"`else` belongs to an `if`, but the innermost open block is "
                             f"`{opener(kind, name)}` (line {line})", t.line, t.col, 4)
                self.skip_line()
                continue
            if t.kind == "kw" and t.text == "fn":
                self.d.error("unclosed-block", f"`{opener(kind, name)}` (line {line}) is never closed before the "
                             "next `fn`", t.line, t.col, 2, self.closer_fix(kind, name, line, t.line))
                return stmts, "implicit", t
            try:
                s = self.statement()
                if s is not None:
                    stmts.append(s)
            except ParseError:
                self.skip_line()

    def closer_fix(self, kind, name, open_line, here):
        """Where does the missing closer go? Indentation has no meaning to the compiler, but it is
        good evidence: the first line indented no deeper than the opener is probably outside it."""
        what = f"`{closer(kind, name)}`"
        lines = self.d.lines
        indent = lambda ln: len(lines[ln - 1]) - len(lines[ln - 1].lstrip())
        if 1 <= open_line <= len(lines):
            for ln in range(open_line + 1, min(here, len(lines) + 1)):
                text = lines[ln - 1].strip()
                if not text or text.startswith("#"):
                    continue
                if indent(ln) <= indent(open_line):
                    if kind == "if" and text.split()[0] == "else":
                        continue
                    return (f"add {what} above line {ln} (`{text}`), where the indentation goes back to the "
                            f"`{opener(kind, name)}` on line {open_line}")
        return f"add {what} above line {here}" if here <= len(lines) else f"add {what} at the end"

    def closer_line(self):
        start = self.i
        end_tok = self.next()
        kind, line, name = self.stack[-1]
        t = self.peek()
        if not (t.kind == "kw" and t.text in BLOCK_KINDS):
            self.d.error("closer-kind", f"`end` must say what it closes; the innermost open block is "
                         f"`{opener(kind, name)}` (line {line})", end_tok.line, end_tok.col, 3,
                         f"`{closer(kind, name)}`")
            self.skip_line()
            return "mine"
        self.next()
        return self.resolve_closer(t.text, end_tok, start)

    def resolve_closer(self, k, start_tok, start):
        kind, line, name = self.stack[-1]
        if k == kind:
            if kind == "fn":
                if self.at("name"):
                    nt = self.next()
                    if nt.text != name:
                        self.d.error("closer-name", f"`end fn {nt.text}` is closing `fn {name}` (line {line})",
                                     nt.line, nt.col, len(nt.text), f"`end fn {name}`")
                else:
                    self.d.error("closer-name", "`end fn` must repeat the function's name",
                                 start_tok.line, start_tok.col, 6, f"`end fn {name}`")
            self.end_line()
            return "mine"
        if any(b[0] == k for b in self.stack[:-1]):
            self.d.error("closer-mismatch", f"`end {k}` doesn't match the innermost open block, "
                         f"`{opener(kind, name)}` (line {line})", start_tok.line, start_tok.col,
                         len(f"end {k}"), self.closer_fix(kind, name, line, start_tok.line))
            self.i = start  # leave the closer for the outer block
            return "outer"
        self.d.error("stray-closer", f"`end {k}` doesn't close anything: no `{k}` is open (the innermost open "
                     f"block is `{opener(kind, name)}` from line {line})", start_tok.line, start_tok.col,
                     len(f"end {k}"), "remove this line")
        self.skip_line()
        return "stray"

    # -- statements
    def statement(self):
        t = self.peek()
        if t.kind == "kw":
            w = t.text
            if w in ("let", "var"):
                return self.let_stmt()
            if w == "return":
                self.next()
                e = None if (self.at("nl") or self.at("eof")) else self.expr()
                self.end_line()
                return Node("return", t, expr=e)
            if w == "if":
                return self.if_stmt()
            if w == "while":
                return self.while_stmt()
            if w == "for":
                return self.for_stmt()
            if w in ("break", "continue"):
                self.next()
                self.end_line()
                return Node(w, t)
            if w == "example":
                self.next()
                e = self.expr()
                self.end_line()
                return Node("example", t, expr=e)
        if t.kind == "name":
            if t.text in STMT_HINTS:
                fix = None
                if t.text in ("elif", "elsif", "elseif"):
                    src = self.d.lines[t.line - 1]
                    fix = f"`{(src[:t.col - 1] + 'else if' + src[t.col - 1 + len(t.text):]).strip()}`"
                self.fail("syntax", f"`{t.text}` isn't a keyword; {STMT_HINTS[t.text]}", t, fix)
            if t.text in FN_WORDS:
                self.fail("syntax", "functions can't be nested", t)
            if self.at_op("=", 1):
                self.next()
                self.next()
                e = self.expr()
                self.end_line()
                return Node("assign", t, name=t.text, expr=e)
        e = self.expr()
        if self.at_op("="):
            eq = self.next()
            if e.kind != "index":
                self.fail("syntax", f"can't assign to `{render(e)}`; only a variable or a list item `xs[i]` can be "
                          "assigned", eq)
            v = self.expr()
            self.end_line()
            return Node("setindex", t, target=e, expr=v)
        self.end_line()
        return Node("exprstmt", t, expr=e)

    def let_stmt(self):
        kw = self.next()
        mutable = kw.text == "var"
        nt = self.expect_name(f"after `{kw.text}`")
        if nt.text == "mut" and self.at("name"):
            self.d.error("syntax", "there's no `mut`; declare a variable that changes with `var`",
                         nt.line, nt.col, 3, f"`var {self.peek().text} = ...`")
            nt, mutable = self.next(), True
        ann, has_ann = None, False
        if self.at_op(":"):
            self.next()
            ann, has_ann = self.parse_type(), True
        self.expect_op("=", f"after `{kw.text} {nt.text}`")
        e = self.expr()
        self.end_line()
        return Node("let", kw, name=nt.text, name_tok=nt, mutable=mutable, ann=ann, has_ann=has_ann, expr=e)

    def cond_line(self):
        try:
            c = self.expr()
            self.end_line()
            return c
        except ParseError:
            self.skip_line()
            return None

    def if_stmt(self):
        kw = self.next()
        cond = self.cond_line()
        self.stack.append(["if", kw.line, None])
        branches, else_body = [], None
        body, how, _ = self.block_body()
        branches.append((cond, body))
        while how == "else":
            et = self.next()
            if self.at_kw("if"):
                self.next()
                c = self.cond_line()
                if else_body is not None:
                    self.d.error("else-order", "`else if` can't come after a plain `else`", et.line, et.col, 4)
                body, how, _ = self.block_body()
                branches.append((c, body))
            else:
                self.end_line()
                if else_body is not None:
                    self.d.error("else-order", "this `if` already has an `else`", et.line, et.col, 4)
                body, how, _ = self.block_body()
                else_body = (else_body or []) + body
        self.stack.pop()
        return Node("if", kw, branches=branches, else_body=else_body)

    def while_stmt(self):
        kw = self.next()
        cond = self.cond_line()
        self.stack.append(["while", kw.line, None])
        body, _, _ = self.block_body()
        self.stack.pop()
        return Node("while", kw, cond=cond, body=body)

    def for_stmt(self):
        """for x in xs / for i in a until b / for i in a through b, each optionally ending in `reversed` (D21)."""
        kw = self.next()
        n = Node("for", kw, var=None, var_tok=None, src=None, lo=None, hi=None, incl=False, rev=False)
        try:
            if self.at_op("("):
                self.fail("syntax", "there's no C-style `for`", self.peek(), "count with `for i in 0 until n`")
            n.var_tok = self.expect_name("for the loop variable, e.g. `for x in xs`")
            n.var = n.var_tok.text
            if self.at_op(","):
                self.fail("syntax", "a `for` loop has one variable", self.peek(),
                          "loop over the indexes with `for i in 0 until length(xs)` and read `xs[i]`")
            if not self.at("name", "in"):
                t = self.peek()
                self.fail("syntax", f"expected `in` after `for {n.var}`, found {describe(t)}", t,
                          f"`for {n.var} in ...`")
            self.next()
            first = self.expr()
            if self.at("name") and self.peek().text in ("until", "through", "to"):
                w = self.next()
                n.lo, n.hi, n.incl = first, self.expr(), w.text != "until"
                if w.text == "to":
                    a, b = render(n.lo), render(n.hi)
                    self.d.error("range-to", "`to` includes the end in some languages and not in others, so it "
                                 "isn't used", w.line, w.col, 2,
                                 f"`for {n.var} in {a} through {b}` (includes {b}) or `for {n.var} in {a} until {b}` "
                                 f"(stops before {b})")
            else:
                n.src = first
            if self.at("name", "reversed"):
                self.next()
                n.rev = True
            self.end_line()
        except ParseError:
            self.skip_line()
        self.stack.append(["for", kw.line, None])
        n.body, _, _ = self.block_body()
        self.stack.pop()
        return n

    # -- expressions (D6: conventional precedence, with the easy-to-misread cases made errors)
    def expr(self):
        return self.logic()

    def logic(self):
        operands, ops = [self.compare()], []
        while self.at_kw("and") or self.at_kw("or"):
            ops.append(self.next())
            operands.append(self.compare())
        if len({o.text for o in ops}) <= 1:
            return fold(operands, ops)
        # Mixed: report it, and recover with the conventional reading (`and` binds tighter).
        groups, gops, orops = [[operands[0]]], [[]], []
        for o, e in zip(ops, operands[1:]):
            if o.text == "and":
                groups[-1].append(e)
                gops[-1].append(o)
            else:
                orops.append(o)
                groups.append([e])
                gops.append([])
        parts = []
        for g, go in zip(groups, gops):
            p = fold(g, go)
            if go:
                p.paren = True
            parts.append(p)
        tree = fold(parts, orops)
        bad = next(o for o in ops if o.text != ops[0].text)
        self.d.error("mixed-and-or", "`and` and `or` can't be mixed without parentheses",
                     bad.line, bad.col, len(bad.text), f"`{render(tree)}` (if that's what you mean)")
        return tree

    def compare(self):
        left = self.additive()
        if not self.at_cmp():
            return left
        ot = self.next()
        right = self.additive()
        node = bin_node(ot, left, right)
        if self.at_cmp():
            ot2 = self.next()
            r2 = self.additive()
            self.d.error("chained-comparison", "comparisons don't chain", ot2.line, ot2.col, len(ot2.text),
                         f"`{render(left)} {ot.text} {render(right)} and {render(right)} {ot2.text} {render(r2)}`")
            while self.at_cmp():
                self.next()
                self.additive()
        return node

    def additive(self):
        left = self.multiplicative()
        while self.at_op("+") or self.at_op("-"):
            ot = self.next()
            left = bin_node(ot, left, self.multiplicative())
        return left

    def multiplicative(self):
        left, prev = self.unary(), None
        while self.at_op("*") or self.at_op("/") or self.at_op("%"):
            ot = self.next()
            right = self.unary()
            if prev in ("/", "%"):
                a, b, c = render(left.left), render(left.right), render(right)
                self.d.error("ambiguous-division", f"`{prev}` followed by `{ot.text}` needs parentheses",
                             ot.line, ot.col, 1, f"`({a} {prev} {b}) {ot.text} {c}` or `{a} {prev} ({b} {ot.text} {c})`")
            left, prev = bin_node(ot, left, right), ot.text
        return left

    def unary(self):
        if self.at_op("-"):
            t = self.next()
            return Node("neg", t, expr=self.unary())
        if self.at_kw("not"):
            t = self.next()
            after_not = self.i
            e = self.unary()
            nt = self.peek()
            if nt.kind == "op" and nt.text in CMP_OPS + ARITH_OPS:
                # `not a == b`: recover with the reading most languages use, `not (a == b)`.
                self.i = after_not
                whole = self.compare()
                self.d.error("not-scope", f"`not` followed by `{render(whole)}` is easy to misread",
                             t.line, t.col, 3, f"`not ({render(whole)})` or `(not {render(e)}) {nt.text} ...`")
                whole.paren = True
                return Node("not", t, expr=whole)
            return Node("not", t, expr=e)
        return self.primary()

    def primary(self):
        e = self.atom()
        while self.at_op("["):
            b = self.next()
            i = self.expr()
            self.expect_op("]", "to close the index")
            n = Node("index", b, base=e, index=i)
            n.start = e.start
            e = n
        return e

    def atom(self):
        t = self.peek()
        if t.kind == "op" and t.text == "[":
            self.next()
            items = []
            if not self.at_op("]"):
                while True:
                    items.append(self.expr())
                    if not self.at_op(","):
                        break
                    self.next()
                    if self.at_op("]"):
                        break  # trailing comma
            self.expect_op("]", "to close the list")
            return Node("list", t, items=items)
        if t.kind == "int":
            self.next()
            return Node("int", t, value=int(t.text))
        if t.kind == "kw" and t.text in ("true", "false"):
            self.next()
            return Node("bool", t, value=t.text == "true")
        if t.kind == "str":
            self.next()
            parts = []
            for kind, p in t.parts:
                if kind == "text":
                    parts.append(("text", p))
                    continue
                sub = Parser(p, self.d)
                try:
                    e = sub.expr()
                    if not sub.at("eof"):
                        x = sub.peek()
                        self.d.error("syntax", f"unexpected {describe(x)} inside `{{...}}`", x.line, x.col,
                                     len(x.text), "an interpolation holds one expression")
                    parts.append(("expr", e))
                except ParseError:
                    parts.append(("expr", Node("bool", p[0], value=False)))  # placeholder; already reported
            return Node("str", t, parts=parts)
        if t.kind == "name":
            self.next()
            if self.at_op("("):
                return self.call(t)
            return Node("name", t, name=t.text)
        if t.kind == "op" and t.text == "(":
            self.next()
            e = self.expr()
            self.expect_op(")", "to close the parenthesis")
            e.paren, e.start = True, t
            return e
        self.fail("syntax", f"expected an expression, found {describe(t)}", t)

    def call(self, nt):
        self.next()  # (
        args = []
        if not self.at_op(")"):
            while True:
                if self.at("name") and (self.at_op(":", 1) or self.at_op("=", 1)):
                    an = self.next()
                    if self.next().text == "=":
                        self.d.error("syntax", "named arguments use `:`, not `=`", an.line, an.col,
                                     len(an.text) + 1, f"`{an.text}: ...`")
                    args.append((an.text, an, self.expr()))
                else:
                    args.append((None, None, self.expr()))
                if self.at_op(","):
                    self.next()
                    continue
                break
        self.expect_op(")", f"to close the call to `{nt.text}`")
        return Node("call", nt, name=nt.text, args=args)


# ------------------------------------------------------------------ checker

CALL_HINTS = {n: "the output function is `print`" for n in
              ("println", "printf", "puts", "echo", "write", "writeln", "console", "log", "display")}
CALL_HINTS.update({n: "write `length(xs)`" for n in ("len", "size", "count", "len_of", "length_of")})
CALL_HINTS.update({n: "write `xs = append(list: xs, item: x)`" for n in ("push", "add", "push_back", "insert")})
CALL_HINTS.update({n: "write `repeat(item: 0, times: n)`" for n in ("fill", "filled", "make", "replicate", "vec")})
BUILTINS = {"print": None, "length": None, "append": ["list", "item"], "repeat": ["item", "times"]}


def is_list(t):
    return bool(t) and t.startswith("List[")


def elem(t):
    return t[5:-1] if is_list(t) else None
NAME_HINTS = {"True": "write `true`", "False": "write `false`", "TRUE": "write `true`",
              "FALSE": "write `false`", "null": "there's no null", "nil": "there's no null",
              "None": "there's no null"}


class Var:
    def __init__(self, ty, mutable, line, param=False, loop=False):
        self.ty, self.mutable, self.line, self.param, self.loop = ty, mutable, line, param, loop


def returns(stmts):
    """Does every path through these statements end in `return`?"""
    for s in stmts:
        if s.kind == "return":
            return True
        if (s.kind == "if" and s.else_body is not None and returns(s.else_body)
                and all(returns(b) for _, b in s.branches)):
            return True
        if (s.kind == "while" and s.cond is not None and s.cond.kind == "bool" and s.cond.value
                and not breaks(s.body)):
            return True  # `while true` with no `break` never falls through
    return False


def breaks(stmts):
    """Is there a `break` for the enclosing loop in these statements (not counting inner loops)?"""
    for s in stmts:
        if s.kind == "break":
            return True
        if s.kind == "if" and (any(breaks(b) for _, b in s.branches) or breaks(s.else_body or [])):
            return True
    return False


def sig(f, uses_io=None):
    io = f.uses_io if uses_io is None else uses_io
    ps = ", ".join(f"{n}: {t or '?'}" for n, t, _ in f.params)
    return f"fn {f.name}({ps})" + (f" -> {f.ret}" if f.ret not in ("Unit", None) else "") + (" uses io" if io else "")


class Checker:
    def __init__(self, fns, d):
        self.d, self.fns, self.all = d, {}, fns
        self.in_example = False
        for f in fns:
            if f.name == "?":
                continue
            if f.name in BUILTINS:
                self.err("reserved-name", f"`{f.name}` is built in and can't be redefined", f.name_tok)
            elif f.name in self.fns:
                self.err("duplicate-fn", f"`fn {f.name}` is already defined on line {self.fns[f.name].tok.line}",
                         f.name_tok)
            else:
                self.fns[f.name] = f

    def err(self, code, msg, tok, fix=None, length=None):
        self.d.error(code, msg, tok.line, tok.col, length or len(tok.text), fix)

    def err_at(self, code, msg, e, fix=None):
        self.d.error(code, msg, e.start.line, e.start.col, len(render(e)), fix)

    def run(self):
        for f in self.all:
            self.check_fn(f)
        main = self.fns.get("main")
        if main is None:
            self.d.error("no-main", "there's no `fn main()`, so the program has nowhere to start", 1, 1, 1,
                         "add `fn main() uses io` ... `end fn main`")
        elif main.params or main.ret != "Unit":
            self.err("main-signature", "`fn main` takes no parameters and returns nothing", main.name_tok,
                     "`fn main() uses io`")

    def check_fn(self, f):
        self.cur = f
        self.scopes = [{}]
        self.loops = 0
        for pn, pt, ptok in f.params:
            if pn in self.scopes[0]:
                self.err("duplicate-name", f"parameter `{pn}` appears twice", ptok)
            self.scopes[0][pn] = Var(pt, False, ptok.line, param=True)
        seen_body = False
        for s in f.body:
            if s.kind != "example":
                seen_body = True
            elif seen_body:
                self.err("example-placement", "`example` lines go right after the `fn` line, before the body",
                         s.tok)
        self.block(f.body, new_scope=False)
        if f.ret not in ("Unit", None) and not returns(f.body):
            self.err("missing-return", f"`fn {f.name}` returns {f.ret}, but some path reaches `end fn` "
                     "without a `return`", f.end_tok, f"add `return <{f.ret}>` on the path that falls through")

    def lookup(self, name):
        for sc in reversed(self.scopes):
            if name in sc:
                return sc[name]
        return None

    def visible_names(self):
        return [n for sc in self.scopes for n in sc]

    def block(self, stmts, new_scope=True):
        if new_scope:
            self.scopes.append({})
        dead = warned = False
        for s in stmts:
            if dead and not warned:
                self.d.warning("unreachable", "this line can never run: it comes after a `return`, `break` or "
                               "`continue`",
                               s.tok.line, s.tok.col, len(s.tok.text))
                warned = True
            self.stmt(s)
            dead = dead or s.kind in ("return", "break", "continue")
        if new_scope:
            self.scopes.pop()

    def cond(self, c):
        if c is None:
            return
        t = self.expr(c)
        if t == "Int":
            self.err_at("not-bool", "a condition must be Bool, and Int isn't converted", c, f"`{render(c)} != 0`")
        elif t not in (None, "Bool"):
            self.err_at("not-bool", f"a condition must be Bool, but this is {t}", c)

    def stmt(self, s):
        k = s.kind
        if k == "example":
            saved, self.scopes, self.in_example = self.scopes, [{}], True
            t = self.expr(s.expr)
            self.scopes, self.in_example = saved, False
            if t not in (None, "Bool"):
                self.err_at("not-bool", "an example must be a Bool expression, usually `f(...) == expected`",
                            s.expr)
        elif k == "let":
            t = self.expr(s.expr, want=s.ann)
            if t == "Unit":
                self.err_at("unit-value", f"`{render(s.expr)}` returns nothing, so there's no value to store",
                            s.expr)
            elif s.has_ann and s.ann and t and t != s.ann:
                self.err_at("type-mismatch", f"`{s.name}` is declared {s.ann}, but the value is {t}", s.expr)
            ty = s.ann if s.has_ann else t
            s.var_ty = ty
            if s.name == "_":
                if s.mutable:
                    self.err("syntax", "discard a value with `let _ = ...`, not `var`", s.tok)
                return
            prev = self.lookup(s.name)
            if prev:
                fix = (f"assign instead: `{s.name} = ...`" if prev.mutable else
                       f"pick a new name, or declare it with `var` on line {prev.line} and assign `{s.name} = ...`")
                self.err("duplicate-name", f"`{s.name}` is already defined on line {prev.line}; a name means one "
                         "thing within a function", s.name_tok, fix)
            else:
                self.scopes[-1][s.name] = Var(ty, s.mutable, s.tok.line)
        elif k == "assign":
            v = self.lookup(s.name)
            t = self.expr(s.expr, want=v.ty if v else None)
            if v is None:
                self.unknown_name(s.tok, fix=f"declare it first: `var {s.name} = ...`")
            elif self.check_mutable(s.name, v, s.tok) and v.ty and t and v.ty != t:
                self.err_at("type-mismatch", f"`{s.name}` is {v.ty}, but the value is {t}", s.expr)
        elif k == "setindex":
            self.setindex(s)
        elif k == "return":
            ret = self.cur.ret
            if s.expr is None:
                if ret not in ("Unit", None):
                    self.err("missing-return-value", f"`fn {self.cur.name}` returns {ret}; give `return` a value",
                             s.tok)
            else:
                t = self.expr(s.expr, want=ret)
                if ret == "Unit":
                    self.err("unexpected-return-value", f"`fn {self.cur.name}` has no return type, so `return` "
                             "takes no value", s.tok, f"add `-> {t}` to the signature, or write plain `return`")
                elif ret and t and t != ret:
                    self.err_at("type-mismatch", f"`fn {self.cur.name}` returns {ret}, but this is {t}", s.expr)
        elif k == "if":
            for c, body in s.branches:
                self.cond(c)
                self.block(body)
            if s.else_body is not None:
                self.block(s.else_body)
        elif k == "while":
            self.cond(s.cond)
            self.loops += 1
            self.block(s.body)
            self.loops -= 1
        elif k == "for":
            self.for_stmt(s)
        elif k in ("break", "continue"):
            if not self.loops:
                self.err("outside-loop", f"`{k}` only works inside a `while` or `for` loop", s.tok)
        elif k == "exprstmt":
            e = s.expr
            t = self.expr(e)
            if e.kind != "call":
                self.err_at("useless-expr", "this line computes a value and throws it away", e)
            elif e.name == "append" and len(e.args) == 2:
                lst, item = (a for _, _, a in e.args)
                if [n for n, _, _ in e.args] == ["item", "list"]:
                    lst, item = item, lst
                fix = (f"`{render(lst)} = append(list: {render(lst)}, item: {render(item)})`" if lst.kind == "name"
                       else None)
                self.err_at("unused-result", "`append` returns a new list; it doesn't change the one you pass", e,
                            fix)
            elif t not in ("Unit", None):
                self.err_at("unused-result", f"the result of `{render(e)}` ({t}) is never used", e,
                            f"`let _ = {render(e)}` if you mean to discard it")

    def check_mutable(self, name, v, tok):
        if v.loop:
            self.err("assign-to-loop-var", f"`{name}` is the loop variable; it takes each value in turn and can't "
                     "be assigned", tok, "to step by something other than 1, count with `while`")
            return False
        if v.param:
            self.err("assign-to-param", f"`{name}` is a parameter, and parameters can't change", tok,
                     f"copy it into a variable first: `var my_{name} = {name}`")
            return False
        if not v.mutable:
            self.err("assign-to-let", f"`{name}` was declared with `let` (line {v.line}), so it can't change",
                     tok, f"declare it with `var {name} = ...` on line {v.line}")
            return False
        return True

    def for_stmt(self, s):
        vt = None
        if s.src is not None:
            src = s.src
            if src.kind == "call" and src.name == "range" and "range" not in self.fns:
                a = [render(x) for _, _, x in src.args]
                v = s.var or "i"
                fix = {1: f"`for {v} in 0 until {a[0]}`", 2: f"`for {v} in {a[0] if a else ''} until "
                       f"{a[1] if len(a) > 1 else ''}`"}.get(len(a), "count with `while` for steps other than 1")
                if len(a) == 3 and a[2] == "-1":
                    stop = src.args[1][2]
                    lit = (stop.value if stop.kind == "int" else -stop.expr.value
                           if stop.kind == "neg" and stop.expr.kind == "int" else None)
                    low = str(lit + 1) if lit is not None else f"{a[1]} + 1"
                    fix = f"`for {v} in {low} through {a[0]} reversed`"
                self.err("unknown-fn", "there's no `range`; a `for` loop counts with words", src.tok, fix)
                for _, _, x in src.args:
                    self.expr(x)
            else:
                t = self.expr(src)
                if is_list(t):
                    vt = elem(t)
                elif t == "Int":
                    self.err_at("not-a-list", f"`for` needs a list or a range, but `{render(src)}` is Int", src,
                                f"`for {s.var} in 0 until {render(src)}`")
                elif t:
                    self.err_at("not-a-list", f"`for` needs a list or a range, but `{render(src)}` is {t}", src)
        elif s.lo is not None:
            self.need(s.lo, self.expr(s.lo), "Int", "a range")
            self.need(s.hi, self.expr(s.hi), "Int", "a range")
            vt = "Int"
        s.var_ty = vt
        self.scopes.append({})
        if s.var:
            prev = self.lookup(s.var)
            if prev:
                self.err("duplicate-name", f"`{s.var}` is already defined on line {prev.line}; a name means one "
                         "thing within a function", s.var_tok, "pick another name for the loop variable")
            else:
                self.scopes[-1][s.var] = Var(vt, False, s.tok.line, loop=True)
        self.loops += 1
        self.block(s.body)
        self.loops -= 1
        self.scopes.pop()

    def setindex(self, s):
        tgt = s.target
        base = tgt.base
        bt = self.expr(base) if base.kind != "name" else None
        if base.kind == "index":
            # grid[i][j] = v: one level at a time, since each level is its own value (D19).
            outer = base.base
            self.err_at("nested-assign", "only one level of indexing can be assigned at a time", tgt,
                        f"`var row = {render(base)}`, then `row[{render(tgt.index)}] = {render(s.expr)}`, "
                        f"then `{render(base)} = row`")
            self.expr(tgt.index)
            self.expr(s.expr)
            return
        if base.kind != "name":
            self.err_at("syntax", f"can't assign into `{render(base)}`; assign to a variable's item: `xs[i] = v`",
                        base)
            return
        v = self.lookup(base.name)
        it = self.expr(tgt.index)
        if v is None:
            self.unknown_name(base.tok)
            self.expr(s.expr)
            return
        base.ty = v.ty
        ok = self.check_mutable(base.name, v, base.tok)
        et = elem(v.ty)
        t = self.expr(s.expr, want=et)
        if v.ty and not is_list(v.ty):
            self.err_at("not-a-list", f"`{base.name}` is {v.ty}, not a list, so it can't be indexed", base)
            return
        self.need(tgt.index, it, "Int", "[...]")
        self.no_negative_index(tgt)
        if ok and et and t and t != et:
            self.err_at("type-mismatch", f"`{base.name}` is {v.ty}, so its items are {et}, but the value is {t}",
                        s.expr)

    def no_negative_index(self, e):
        i = e.index
        if i.kind == "neg" and i.expr.kind == "int":
            b = render(e.base)
            self.err_at("negative-index", "there's no negative indexing; indexes run from 0 to length - 1", i,
                        f"`{b}[length({b}) - {i.expr.value}]`")

    def unknown_name(self, tok, fix=None):
        name = tok.text
        hint = NAME_HINTS.get(name)
        sugg = difflib.get_close_matches(name, self.visible_names(), 1)
        if hint:
            fix = hint
        elif sugg:
            fix = f"did you mean `{sugg[0]}`?"
        elif self.in_example:
            fix = "examples run on their own, so parameters aren't in scope: write the values out"
        self.err("unknown-name", f"`{name}` isn't defined here", tok, fix)

    def need(self, e, t, want, op, other=None):
        if t and t != want:
            fix = None
            if (t, op) == ("String", "+"):
                fix = "join strings with interpolation: `\"{a}{b}\"`"
            elif is_list(t) and op == "*" and e.kind == "list" and len(e.items) == 1 and other is not None:
                fix = f"`repeat(item: {render(e.items[0])}, times: {render(other)})`"
            what = "an index" if op == "[...]" else f"`{op}`"
            self.err_at("type-mismatch", f"{what} needs {want}, but `{render(e)}` is {t}", e, fix)

    def expr(self, e, want=None):
        e.ty = self._expr(e, want)
        return e.ty

    def _expr(self, e, want=None):
        k = e.kind
        if k == "int":
            return "Int"
        if k == "bool":
            return "Bool"
        if k == "str":
            for kind, p in e.parts:
                if kind == "expr" and self.expr(p) == "Unit":
                    self.err_at("unit-value", f"`{render(p)}` returns nothing, so there's nothing to interpolate", p)
            return "String"
        if k == "name":
            if e.name == "_":
                self.err("syntax", "`_` discards a value; it can't be read", e.tok)
                return None
            v = self.lookup(e.name)
            if v:
                return v.ty
            self.unknown_name(e.tok)
            return None
        if k == "neg":
            self.need(e.expr, self.expr(e.expr), "Int", "-")
            return "Int"
        if k == "not":
            self.need(e.expr, self.expr(e.expr), "Bool", "not")
            return "Bool"
        if k == "list":
            if not e.items:
                if is_list(want):
                    return want
                self.err("empty-list-type", "an empty list needs a type", e.tok,
                         "say which, e.g. `let xs: List[Int] = []` or `var xs: List[String] = []`", length=2)
                return None
            first = None
            for i, x in enumerate(e.items):
                t = self.expr(x, want=first or elem(want))
                if t == "Unit":
                    self.err_at("unit-value", f"`{render(x)}` returns nothing, so it can't be a list item", x)
                elif first is None:
                    first = t
                elif t and t != first:
                    self.err_at("type-mismatch", f"a list's items all have one type: the first is {first}, but "
                                f"`{render(x)}` is {t}", x)
            return f"List[{first}]" if first else None
        if k == "index":
            bt, it = self.expr(e.base), self.expr(e.index)
            self.need(e.index, it, "Int", "[...]")
            self.no_negative_index(e)
            if bt == "String":
                self.err_at("not-a-list", "strings can't be indexed yet", e.base)
                return None
            if bt and not is_list(bt):
                self.err_at("not-a-list", f"`{render(e.base)}` is {bt}, not a list, so it can't be indexed", e.base)
                return None
            return elem(bt)
        if k == "bin":
            op = e.op
            lt = self.expr(e.left)
            rt = self.expr(e.right, want=lt if op in ("==", "!=") else None)
            if op == "+" and (is_list(lt) or is_list(rt)):
                fix = None
                if is_list(lt) and e.right.kind == "list" and len(e.right.items) == 1:
                    fix = f"`append(list: {render(e.left)}, item: {render(e.right.items[0])})`"
                self.err_at("type-mismatch", "there's no list `+`" + ("" if fix else "; to join two lists, "
                            "`append` the items of one to the other in a `while` loop"), e, fix)
                return lt if is_list(lt) else None
            if op in ARITH_OPS or op in ("<", "<=", ">", ">="):
                self.need(e.left, lt, "Int", op, other=e.right)
                self.need(e.right, rt, "Int", op, other=e.left)
                return "Int" if op in ARITH_OPS else "Bool"
            if op in ("==", "!="):
                if "Unit" in (lt, rt):
                    self.err_at("unit-value", "a function that returns nothing can't be compared", e)
                elif lt and rt and lt != rt:
                    self.err_at("type-mismatch", f"can't compare {lt} with {rt}", e)
                return "Bool"
            self.need(e.left, lt, "Bool", op)
            self.need(e.right, rt, "Bool", op)
            return "Bool"
        if k == "call":
            return self.call(e, want)
        return None

    def match_args(self, name, pnames, e):
        """Check argument names against the parameters (D4). Returns order, where order[i] is the index of the
        parameter args[i] fills, or None if the count is wrong (already reported)."""
        args = e.args
        names = [n for n, _, _ in args]
        want = f"`{name}({', '.join(p + ': ...' for p in pnames)})`"
        if len(args) != len(pnames):
            self.err("arg-count", f"`{name}` takes {len(pnames)} argument(s), but this call passes {len(args)}",
                     e.tok, want)
            return None
        order = list(range(len(args)))
        if len(pnames) == 1:
            if names[0] is not None and names[0] != pnames[0]:
                self.err("unknown-arg-name", f"`{name}`'s parameter is `{pnames[0]}`, not `{names[0]}`",
                         args[0][1], f"`{pnames[0]}: ...` or no name")
        elif len(pnames) > 1:
            if any(n is None for n in names):
                fixed = f"{name}(" + ", ".join(f"{p}: {render(a)}" for p, (_, _, a) in zip(pnames, args)) + ")"
                self.err("unnamed-arg", f"`{name}` takes more than one argument, so each one must be named",
                         e.tok, f"`{fixed}`")
            else:
                bad = [(n, t) for n, t, _ in args if n not in pnames]
                for n, t in bad:
                    sg = difflib.get_close_matches(n, pnames, 1)
                    self.err("unknown-arg-name", f"`{name}` has no parameter `{n}` (it has {', '.join(pnames)})",
                             t, f"did you mean `{sg[0]}`?" if sg else None)
                if not bad:
                    if len(set(names)) != len(names):
                        self.err("duplicate-arg", "the same argument is given twice", e.tok, want)
                    else:
                        order = [pnames.index(n) for n in names]
                        if names != pnames:
                            by = {n: a for n, _, a in args}
                            fixed = f"{name}(" + ", ".join(f"{p}: {render(by[p])}" for p in pnames) + ")"
                            self.err("arg-order", f"arguments must come in the order `fn {name}` declares them "
                                     f"({', '.join(pnames)})", e.tok, f"`{fixed}`")
        return order

    def unnamed_builtin(self, e):
        """print(x) and length(x): one argument, never named. Returns the argument's type."""
        name = e.name
        if len(e.args) != 1:
            self.err("arg-count", f"`{name}` takes one argument, but this call passes {len(e.args)}", e.tok)
        t = None
        for n, nt, a in e.args:
            if n is not None:
                self.err("unknown-arg-name", f"`{name}`'s argument isn't named", nt, f"`{name}({render(a)})`")
            t = self.expr(a)
            if t == "Unit":
                self.err_at("unit-value", f"`{render(a)}` returns nothing, so there's nothing to {name}", a)
        return t if len(e.args) == 1 else None

    def call(self, e, want=None):
        name = e.name
        if name == "print":
            self.effect("print", None, e)
            self.unnamed_builtin(e)
            return "Unit"
        if name == "length":
            t = self.unnamed_builtin(e)
            if t and t != "String" and not is_list(t):
                self.err_at("type-mismatch", f"`length` takes a list or a String, but `{render(e.args[0][2])}` is {t}",
                            e.args[0][2])
            return "Int"
        if name in ("append", "repeat"):
            return self.list_builtin(e, want)
        f = self.fns.get(name)
        if f is None:
            for _, _, a in e.args:
                self.expr(a)
            sugg = difflib.get_close_matches(name, list(self.fns) + list(BUILTINS), 1)
            fix = CALL_HINTS.get(name) or (f"did you mean `{sugg[0]}`?" if sugg else None)
            self.err("unknown-fn", f"there's no function `{name}`", e.tok, fix)
            return None
        self.effect(name, f, e)
        params, args = f.params, e.args
        order = self.match_args(name, [p[0] for p in params], e)
        if order is None:
            for _, _, a in args:
                self.expr(a)
            return f.ret
        for i, (_, _, a) in enumerate(args):
            pn, pt, _ = params[order[i]]
            t = self.expr(a, want=pt)
            if t == "Unit":
                self.err_at("unit-value", f"`{render(a)}` returns nothing, so it can't be an argument", a)
            elif pt and t and pt != t:
                self.err_at("type-mismatch", f"`{name}`'s `{pn}` is {pt}, but `{render(a)}` is {t}", a)
        return f.ret

    def list_builtin(self, e, want):
        """append(list: List[T], item: T) -> List[T]; repeat(item: T, times: Int) -> List[T]."""
        name, pnames = e.name, BUILTINS[e.name]
        order = self.match_args(name, pnames, e)
        if order is None:
            for _, _, a in e.args:
                self.expr(a)
            return None
        by = {pnames[order[i]]: a for i, (_, _, a) in enumerate(e.args)}
        if name == "append":
            lt = self.expr(by["list"], want=want if is_list(want) else None)
            if lt and not is_list(lt):
                self.err_at("type-mismatch", f"`append`'s `list` must be a list, but `{render(by['list'])}` is {lt}",
                            by["list"])
                lt = None
            it = self.expr(by["item"], want=elem(lt))
            if it == "Unit":
                self.err_at("unit-value", f"`{render(by['item'])}` returns nothing, so it can't be a list item",
                            by["item"])
            elif lt and it and it != elem(lt):
                self.err_at("type-mismatch", f"`{render(by['list'])}` is {lt}, so its items are {elem(lt)}, but "
                            f"`{render(by['item'])}` is {it}", by["item"])
            return lt
        it = self.expr(by["item"], want=elem(want))
        self.need(by["times"], self.expr(by["times"]), "Int", "times")
        if it == "Unit":
            self.err_at("unit-value", f"`{render(by['item'])}` returns nothing, so it can't be a list item", by["item"])
            return None
        return f"List[{it}]" if it else None

    def effect(self, name, f, e):
        uses = f is None or f.uses_io  # f None means the builtin `print`
        if not uses:
            return
        if self.in_example:
            self.err("example-effect", f"examples can't call `{name}`, which uses io", e.tok)
        elif not self.cur.uses_io:
            self.err("missing-effect", f"`{name}` uses io, so `fn {self.cur.name}` must declare `uses io` too",
                     e.tok, f"`{sig(self.cur, uses_io=True)}`")


# ------------------------------------------------------------------ C emitter (D1)

CTYPE = {"Int": "int64_t", "Bool": "bool", "String": "const char *", "Unit": "void"}
SLOT = {"Int": "i", "Bool": "b", "String": "s"}


def ctype(t):
    return "cl_list *" if is_list(t) else CTYPE[t]


def slot(t):
    return "l" if is_list(t) else SLOT[t]


def desc(t):
    """Type descriptor the runtime uses to show, compare and copy values: I, B, S, or L + item descriptor."""
    return "L" + desc(elem(t)) if is_list(t) else t[0]

RUNTIME = r"""#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *cl_file = @FILE@;
__attribute__((noreturn)) static void cl_trap(const char *what, int line, int col) {
    fflush(stdout);
    fprintf(stderr, "%s:%d:%d: runtime error: %s\n", cl_file, line, col, what);
    exit(70);
}
static int64_t cl_add(int64_t a, int64_t b, int l, int c) {
    int64_t r; if (__builtin_add_overflow(a, b, &r)) cl_trap("integer overflow in `+`", l, c); return r; }
static int64_t cl_sub(int64_t a, int64_t b, int l, int c) {
    int64_t r; if (__builtin_sub_overflow(a, b, &r)) cl_trap("integer overflow in `-`", l, c); return r; }
static int64_t cl_mul(int64_t a, int64_t b, int l, int c) {
    int64_t r; if (__builtin_mul_overflow(a, b, &r)) cl_trap("integer overflow in `*`", l, c); return r; }
static int64_t cl_div(int64_t a, int64_t b, int l, int c) {
    if (b == 0) cl_trap("division by zero", l, c);
    if (a == INT64_MIN && b == -1) cl_trap("integer overflow in `/`", l, c);
    return a / b; }
static int64_t cl_mod(int64_t a, int64_t b, int l, int c) {
    if (b == 0) cl_trap("division by zero in `%`", l, c);
    if (b == -1) return 0;
    return a % b; }
static int64_t cl_neg(int64_t a, int l, int c) {
    if (a == INT64_MIN) cl_trap("integer overflow in `-`", l, c); return -a; }
static void cl_print_int(int64_t v) { printf("%lld\n", (long long)v); }
static void cl_print_bool(bool v) { puts(v ? "true" : "false"); }
static void cl_print_str(const char *s) { puts(s); }

/* Strings are immutable, NUL-terminated UTF-8. v0 never frees them (see DESIGN.md, D18). */
static void *cl_alloc(size_t n) {
    void *p = malloc(n);
    if (!p) { fputs("runtime error: out of memory\n", stderr); exit(70); }
    return p;
}
static const char *cl_int_str(int64_t v) {
    char *p = cl_alloc(24); snprintf(p, 24, "%lld", (long long)v); return p; }
static const char *cl_concat(int n, ...) {
    va_list ap; size_t len = 0;
    va_start(ap, n); for (int i = 0; i < n; i++) len += strlen(va_arg(ap, const char *)); va_end(ap);
    char *out = cl_alloc(len + 1), *q = out;
    va_start(ap, n);
    for (int i = 0; i < n; i++) { const char *s = va_arg(ap, const char *); size_t k = strlen(s); memcpy(q, s, k); q += k; }
    va_end(ap);
    *q = 0; return out;
}
static int64_t cl_str_len(const char *s) {  /* in Unicode code points */
    int64_t n = 0; for (; *s; s++) n += ((unsigned char)*s & 0xC0) != 0x80; return n; }

/* Lists (D19) have value semantics: assigning or passing one never creates a shared, mutable alias.
   rc counts the variables and list slots that may refer to a list; a mutation copies the list first
   unless rc == 1. rc may over-count (v0 never frees anything), which only costs an extra copy. */
typedef struct cl_list cl_list;
typedef union { int64_t i; bool b; const char *s; cl_list *l; } cl_val;
struct cl_list { int64_t rc, len, cap; cl_val *items; };
static cl_list *cl_list_new(int64_t cap, int line, int col) {
    if (cap < 4) cap = 4;
    if (cap > ((int64_t)1 << 40) / (int64_t)sizeof(cl_val)) cl_trap("list too large", line, col);
    cl_list *l = cl_alloc(sizeof *l); l->rc = 1; l->len = 0; l->cap = cap;
    l->items = cl_alloc(sizeof(cl_val) * (size_t)cap); return l; }
static cl_list *cl_share(cl_list *l) { l->rc++; return l; }
static cl_list *cl_list_of(int n, ...) {
    cl_list *l = cl_list_new(n, 0, 0); va_list ap; va_start(ap, n);
    for (int i = 0; i < n; i++) l->items[i] = va_arg(ap, cl_val);
    va_end(ap); l->len = n; return l; }
static cl_list *cl_list_copy(cl_list *src, int64_t cap, const char *d) {
    cl_list *l = cl_list_new(cap > src->len ? cap : src->len, 0, 0);
    memcpy(l->items, src->items, sizeof(cl_val) * (size_t)src->len); l->len = src->len;
    if (d[0] == 'L') for (int64_t i = 0; i < l->len; i++) l->items[i].l->rc++;
    return l; }
static void cl_unshare(cl_list **p, int64_t cap, const char *d) {
    if ((*p)->rc > 1) { (*p)->rc--; *p = cl_list_copy(*p, cap, d); } }
static void cl_index_check(cl_list *l, int64_t i, int line, int col) {
    if (i >= 0 && i < l->len) return;
    char m[200];
    if (i < 0) snprintf(m, sizeof m, "index %lld is out of range: indexes start at 0, and there's no negative "
                        "indexing (the last item is at length - 1)", (long long)i);
    else if (l->len == 0) snprintf(m, sizeof m, "index %lld is out of range: the list is empty", (long long)i);
    else snprintf(m, sizeof m, "index %lld is out of range for a list of length %lld (the last index is %lld)",
                  (long long)i, (long long)l->len, (long long)(l->len - 1));
    cl_trap(m, line, col); }
static cl_val cl_list_get(cl_list *l, int64_t i, int line, int col) {
    cl_index_check(l, i, line, col); return l->items[i]; }
static void cl_list_set(cl_list **p, int64_t i, cl_val v, const char *d, int line, int col) {
    cl_index_check(*p, i, line, col); cl_unshare(p, (*p)->len, d);
    if (d[0] == 'L') (*p)->items[i].l->rc--;
    (*p)->items[i] = v; }
static void cl_list_push(cl_list **p, cl_val v, const char *d) {
    cl_unshare(p, (*p)->len * 2 + 1, d);
    cl_list *l = *p;
    if (l->len == l->cap) {
        l->cap *= 2; l->items = realloc(l->items, sizeof(cl_val) * (size_t)l->cap);
        if (!l->items) { fputs("runtime error: out of memory\n", stderr); exit(70); } }
    l->items[l->len++] = v; }
static cl_list *cl_list_appended(cl_list *src, cl_val v, const char *d) {
    cl_list *l = cl_list_copy(src, src->len + 1, d); l->items[l->len++] = v; return l; }
static cl_list *cl_list_repeat(cl_val v, int64_t n, const char *d, int line, int col) {
    if (n < 0) cl_trap("`repeat` needs `times` to be 0 or more", line, col);
    cl_list *l = cl_list_new(n, line, col);
    for (int64_t i = 0; i < n; i++) l->items[i] = v;
    l->len = n;
    if (d[0] == 'L') v.l->rc += n - 1;
    return l; }
static bool cl_list_eq(cl_list *a, cl_list *b, const char *d);
static bool cl_val_eq(cl_val a, cl_val b, const char *d) {
    switch (d[0]) {
    case 'I': return a.i == b.i;
    case 'B': return a.b == b.b;
    case 'S': return strcmp(a.s, b.s) == 0;
    default: return cl_list_eq(a.l, b.l, d + 1); } }
static bool cl_list_eq(cl_list *a, cl_list *b, const char *d) {
    if (a == b) return true;
    if (a->len != b->len) return false;
    for (int64_t i = 0; i < a->len; i++) if (!cl_val_eq(a->items[i], b->items[i], d)) return false;
    return true; }
typedef struct { char *p; size_t len, cap; } cl_buf;
static void cl_put(cl_buf *b, const char *s, size_t n) {
    if (b->len + n + 1 > b->cap) {
        b->cap = (b->len + n + 1) * 2; b->p = realloc(b->p, b->cap);
        if (!b->p) { fputs("runtime error: out of memory\n", stderr); exit(70); } }
    memcpy(b->p + b->len, s, n); b->len += n; b->p[b->len] = 0; }
static void cl_show_into(cl_buf *b, cl_val v, const char *d) {
    char tmp[24];
    switch (d[0]) {
    case 'I': snprintf(tmp, sizeof tmp, "%lld", (long long)v.i); cl_put(b, tmp, strlen(tmp)); break;
    case 'B': cl_put(b, v.b ? "true" : "false", v.b ? 4 : 5); break;
    case 'S':  /* quoted, with the language's own escapes, so it reads back as a literal */
        cl_put(b, "\"", 1);
        for (const char *s = v.s; *s; s++) {
            const char *e = NULL;
            switch (*s) { case '"': e = "\\\""; break; case '\\': e = "\\\\"; break; case '\n': e = "\\n"; break;
                          case '\t': e = "\\t"; break; case '{': e = "\\{"; break; case '}': e = "\\}"; break; }
            if (e) cl_put(b, e, 2); else cl_put(b, s, 1); }
        cl_put(b, "\"", 1); break;
    default:
        cl_put(b, "[", 1);
        for (int64_t i = 0; i < v.l->len; i++) {
            if (i) cl_put(b, ", ", 2);
            cl_show_into(b, v.l->items[i], d + 1); }
        cl_put(b, "]", 1); } }
static const char *cl_show(cl_val v, const char *d) {
    cl_buf b = {0}; cl_put(&b, "", 0); cl_show_into(&b, v, d); return b.p; }
static void cl_hex(const char *s) {
    if (!*s) { putchar('-'); return; }
    for (; *s; s++) printf("%02x", (unsigned char)*s);
}
"""

MAIN = r"""
int main(int argc, char **argv) {
    if (argc > 1 && strcmp(argv[1], "--cl-examples") == 0) return cl_examples();
    f_main();
    return 0;
}
"""

def c_string(t):
    """A C string literal for t: printable ASCII as is, everything else (and ? for trigraphs) in octal."""
    out = []
    for b in t.encode("utf-8"):
        out.append(chr(b) if 32 <= b < 127 and chr(b) not in '"\\?' else f"\\{b:03o}")
    return '"' + "".join(out) + '"'


ARITH_FN = {"+": "cl_add", "-": "cl_sub", "*": "cl_mul", "/": "cl_div", "%": "cl_mod"}


class Emitter:
    def __init__(self, fns, path):
        self.fns, self.path = fns, path
        self.examples = [s for f in fns for s in f.body if s.kind == "example"]

    def emit(self):
        out = [RUNTIME.replace("@FILE@", json.dumps(self.path))]
        for f in self.fns:
            out.append(self.proto(f) + ";")
        self.tmp = 0
        for f in self.fns:
            self.params = {n for n, _, _ in f.params}
            out.append("")
            out.append(self.proto(f) + " {")
            self.block(f.body, 1, out)
            if f.ret != "Unit":
                out.append(f'    cl_trap("reached the end of fn {f.name} without a return", '
                           f"{f.end_tok.line}, {f.end_tok.col});")
            out.append("}")
        out.append("")
        out.append("static int cl_examples(void) {")
        out.append("    int failed = 0;")
        for i, s in enumerate(self.examples):
            out.append(f'    printf("EXRUN {i}\\n"); fflush(stdout);')
            e = s.expr
            if e.kind == "bin" and e.op == "==" and not e.paren and is_list(e.left.ty):
                d = c_string(desc(e.left.ty))
                out.append(f"    {{ cl_list *l = {self.expr(e.left)}; cl_list *r = {self.expr(e.right)};")
                out.append(f'      if (!cl_list_eq(l, r, {c_string(desc(elem(e.left.ty)))})) {{ printf("EXFAILV {i} "); '
                           f"cl_hex(cl_show((cl_val){{.l = l}}, {d})); putchar(' '); "
                           f"cl_hex(cl_show((cl_val){{.l = r}}, {d})); putchar('\\n'); failed++; }} }}")
            elif e.kind == "bin" and e.op == "==" and not e.paren and e.left.ty == "String":
                out.append(f"    {{ const char *l = {self.expr(e.left)}; const char *r = {self.expr(e.right)};")
                out.append(f'      if (strcmp(l, r) != 0) {{ printf("EXFAILS {i} "); cl_hex(l); putchar(\' \'); '
                           'cl_hex(r); putchar(\'\\n\'); failed++; } }')
            elif e.kind == "bin" and e.op == "==" and not e.paren:
                out.append(f"    {{ int64_t l = {self.expr(e.left)}; int64_t r = {self.expr(e.right)};")
                out.append(f'      if (l != r) {{ printf("EXFAIL {i} %lld %lld\\n", (long long)l, (long long)r); '
                           "failed++; } }")
            else:
                out.append(f'    if (!({self.expr(e)})) {{ printf("EXFAIL {i}\\n"); failed++; }}')
        out.append('    printf("EXDONE\\n");')
        out.append("    return failed ? 1 : 0;")
        out.append("}")
        out.append(MAIN)
        return "\n".join(out)

    def proto(self, f):
        ps = ", ".join(f"{ctype(t)} v_{n}" for n, t, _ in f.params) or "void"
        return f"static {ctype(f.ret)} f_{f.name}({ps})"

    def block(self, stmts, depth, out):
        ind = "    " * depth
        for s in stmts:
            k = s.kind
            if k == "example":
                continue
            if k == "let":
                if s.name == "_":
                    out.append(f"{ind}(void)({self.expr(s.expr)});")
                else:
                    out.append(f"{ind}{ctype(s.var_ty)} v_{s.name} = {self.own(s.expr)};")
            elif k == "assign":
                e = s.expr
                if (e.kind == "call" and e.name == "append" and len(e.args) == 2 and e.args[0][2].kind == "name"
                        and e.args[0][2].name == s.name):
                    # xs = append(list: xs, item: x): grow xs in place when nothing else refers to it
                    out.append(f"{ind}cl_list_push(&v_{s.name}, {self.val(e.args[1][2], own=True)}, "
                               f"{c_string(desc(elem(e.ty)))});")
                else:
                    out.append(f"{ind}v_{s.name} = {self.own(e)};")
            elif k == "setindex":
                t = s.target
                out.append(f"{ind}cl_list_set(&v_{t.base.name}, {self.expr(t.index)}, {self.val(s.expr, own=True)}, "
                           f"{c_string(desc(elem(t.base.ty)))}, {t.tok.line}, {t.tok.col});")
            elif k == "return":
                if s.expr is None:
                    out.append(f"{ind}return;")
                elif s.expr.kind == "name" and s.expr.name not in self.params:
                    out.append(f"{ind}return {self.expr(s.expr)};")  # a local's last use: move it out
                else:
                    out.append(f"{ind}return {self.own(s.expr)};")
            elif k == "if":
                for j, (c, body) in enumerate(s.branches):
                    out.append(f"{ind}{'if' if j == 0 else '} else if'} ({self.expr(c)}) {{")
                    self.block(body, depth + 1, out)
                if s.else_body is not None:
                    out.append(f"{ind}}} else {{")
                    self.block(s.else_body, depth + 1, out)
                out.append(f"{ind}}}")
            elif k == "while":
                out.append(f"{ind}while ({self.expr(s.cond)}) {{")
                self.block(s.body, depth + 1, out)
                out.append(f"{ind}}}")
            elif k == "for":
                self.for_stmt(s, depth, out)
            elif k in ("break", "continue"):
                out.append(f"{ind}{k};")
            elif k == "exprstmt":
                out.append(f"{ind}{self.expr(s.expr)};")

    def for_stmt(self, s, depth, out):
        """Bounds and the list are evaluated once. Counting never steps past a bound, so it can't overflow;
        `continue` goes to the C `for`'s step as it should."""
        ind, n = "    " * depth, self.tmp
        self.tmp += 1
        v = f"v_{s.var}"
        if s.src is not None:
            L, K = f"cl_l{n}", f"cl_k{n}"
            shared = s.src.kind in ("name", "index")
            # A snapshot: changing the list inside the loop copies it, so the loop sees the original (D19).
            out.append(f"{ind}{{ cl_list *{L} = {self.own(s.src)};")
            if s.rev:
                out.append(f"{ind}for (int64_t {K} = {L}->len - 1; {K} >= 0; {K}--) {{")
            else:
                out.append(f"{ind}for (int64_t {K} = 0; {K} < {L}->len; {K}++) {{")
            out.append(f"{ind}    {ctype(s.var_ty)} {v} = {L}->items[{K}].{slot(s.var_ty)};")
            self.block(s.body, depth + 1, out)
            out.append(f"{ind}}}" + (f" {L}->rc--;" if shared else "") + " }")
            return
        lo, hi, more = f"cl_lo{n}", f"cl_hi{n}", f"cl_more{n}"
        out.append(f"{ind}{{ int64_t {lo} = {self.expr(s.lo)}, {hi} = {self.expr(s.hi)};")
        if not s.rev and not s.incl:
            out.append(f"{ind}for (int64_t {v} = {lo}; {v} < {hi}; {v}++) {{")
        elif not s.rev:
            out.append(f"{ind}for (int64_t {v} = {lo}, {more} = {lo} <= {hi}; {more}; {more} = {v} < {hi}, "
                       f"{v} += {more}) {{")
        else:
            first, cond = (hi, f"{lo} <= {hi}") if s.incl else (f"{hi} - ({lo} < {hi})", f"{lo} < {hi}")
            out.append(f"{ind}for (int64_t {v} = {first}, {more} = {cond}; {more}; {more} = {v} > {lo}, "
                       f"{v} -= {more}) {{")
        self.block(s.body, depth + 1, out)
        out.append(f"{ind}}} }}")

    def own(self, e):
        """C for e when the result is stored (a variable, list slot or return value): a list read from a
        variable or another list is shared, so a later mutation of either copies first (D19)."""
        c = self.expr(e)
        if is_list(e.ty) and e.kind in ("name", "index"):
            return f"cl_share({c})"
        return c

    def val(self, e, own=False):
        """e wrapped as a cl_val (a list slot)."""
        return f"(cl_val){{.{slot(e.ty)} = {self.own(e) if own else self.expr(e)}}}"

    def show(self, e):
        """C for e as a const char * (print and interpolation)."""
        if e.ty == "String":
            return self.expr(e)
        if e.ty == "Bool":
            return f'({self.expr(e)} ? "true" : "false")'
        if e.ty == "Int":
            return f"cl_int_str({self.expr(e)})"
        return f"cl_show({self.val(e)}, {c_string(desc(e.ty))})"

    def expr(self, e):
        k = e.kind
        if k == "list":
            if not e.items:
                return "cl_list_of(0)"
            return f"cl_list_of({len(e.items)}, " + ", ".join(self.val(x, own=True) for x in e.items) + ")"
        if k == "index":
            return (f"cl_list_get({self.expr(e.base)}, {self.expr(e.index)}, {e.tok.line}, {e.tok.col})"
                    f".{slot(e.ty)}")
        if k == "int":
            return f"INT64_C({e.value})"
        if k == "bool":
            return "true" if e.value else "false"
        if k == "str":
            pieces = [c_string(p) if kind == "text" else self.show(p) for kind, p in e.parts]
            if len(pieces) == 1 and e.parts[0][0] == "text":
                return pieces[0]
            return f"cl_concat({len(pieces)}, " + ", ".join(pieces) + ")"
        if k == "name":
            return f"v_{e.name}"
        if k == "neg":
            return f"cl_neg({self.expr(e.expr)}, {e.tok.line}, {e.tok.col})"
        if k == "not":
            return f"(!{self.expr(e.expr)})"
        if k == "bin":
            l, r = self.expr(e.left), self.expr(e.right)
            if e.op in ARITH_FN:
                return f"{ARITH_FN[e.op]}({l}, {r}, {e.tok.line}, {e.tok.col})"
            if e.op in ("==", "!=") and e.left.ty == "String":
                return f"(strcmp({l}, {r}) {e.op} 0)"
            if e.op in ("==", "!=") and is_list(e.left.ty):
                return f"({'' if e.op == '==' else '!'}cl_list_eq({l}, {r}, {c_string(desc(elem(e.left.ty)))}))"
            op = {"and": "&&", "or": "||"}.get(e.op, e.op)
            return f"({l} {op} {r})"
        if k == "call":
            if e.name == "print":
                a = e.args[0][2]
                if is_list(a.ty):
                    return f"cl_print_str({self.show(a)})"
                kind = {"Bool": "bool", "String": "str"}.get(a.ty, "int")
                return f"cl_print_{kind}({self.expr(a)})"
            if e.name == "length":
                a = e.args[0][2]
                return f"cl_str_len({self.expr(a)})" if a.ty == "String" else f"({self.expr(a)})->len"
            if e.name in ("append", "repeat"):
                by = {n: a for n, _, a in e.args}
                d = c_string(desc(elem(e.ty)))
                if e.name == "append":
                    return f"cl_list_appended({self.expr(by['list'])}, {self.val(by['item'], own=True)}, {d})"
                return (f"cl_list_repeat({self.val(by['item'], own=True)}, {self.expr(by['times'])}, {d}, "
                        f"{e.tok.line}, {e.tok.col})")
            # Arguments are borrowed: parameters can't change, and storing one anywhere shares it.
            return f"f_{e.name}(" + ", ".join(self.expr(a) for _, _, a in e.args) + ")"
        raise AssertionError(f"can't emit {k}")


# ------------------------------------------------------------------ driver


def front_end(path, src):
    d = Diags(path, src)
    fns = Parser(lex(src, d), d).program()
    try:
        Checker(fns, d).run()
    except Exception:
        if not d.has_errors():  # a crash on a clean parse is a compiler bug
            raise
    return d, fns


def render_string(v):
    return '"' + escape_text(v) + '"'


def show_value(v, ty):
    return ("true" if v else "false") if ty == "Bool" else str(v)


def run_examples(exe, em, d):
    """Run the binary's examples; turn failures into diagnostics. Returns how many ran."""
    try:
        r = subprocess.run([exe, "--cl-examples"], capture_output=True, text=True, timeout=10)
        out, err, timed_out = r.stdout, r.stderr, False
    except subprocess.TimeoutExpired as te:
        out = te.stdout.decode() if isinstance(te.stdout, bytes) else (te.stdout or "")
        err, timed_out = "", True
    last, done = None, False
    for line in out.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "EXRUN":
            last = int(parts[1])
        elif parts[0] == "EXDONE":
            done = True
        elif parts[0] == "EXFAILV":
            s = em.examples[int(parts[1])]
            l, r = (bytes.fromhex(x).decode("utf-8", "replace") for x in parts[2:4])
            d.error("example-failed", f"example is false: `{render(s.expr.left)}` is {l}, expected {r}",
                    s.tok.line, s.tok.col, len("example"))
        elif parts[0] == "EXFAILS":
            s = em.examples[int(parts[1])]
            l, r = (render_string(bytes.fromhex(x).decode("utf-8", "replace") if x != "-" else "")
                    for x in parts[2:4])
            d.error("example-failed", f"example is false: `{render(s.expr.left)}` is {l}, expected {r}",
                    s.tok.line, s.tok.col, len("example"))
        elif parts[0] == "EXFAIL":
            s = em.examples[int(parts[1])]
            if len(parts) == 4:
                left, ty = s.expr.left, s.expr.left.ty
                msg = (f"example is false: `{render(left)}` is {show_value(int(parts[2]), ty)}, "
                       f"expected {show_value(int(parts[3]), ty)}")
            else:
                msg = f"example is false: `{render(s.expr)}`"
            d.error("example-failed", msg, s.tok.line, s.tok.col, len("example"))
    if not done and last is not None:
        s = em.examples[last]
        if timed_out:
            d.error("example-timeout", "example didn't finish within 10 s", s.tok.line, s.tok.col, 7)
        else:
            why = err.strip().splitlines()[-1] if err.strip() else "it crashed"
            d.error("example-crashed", f"example stopped the program: {why}", s.tok.line, s.tok.col, 7)
    return len(em.examples)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="clc", description="compiler for claude-lang")
    ap.add_argument("command", choices=["check", "build", "run", "test"])
    ap.add_argument("file")
    ap.add_argument("-o", "--output", help="binary to write (build only)")
    ap.add_argument("--emit-c", action="store_true", help="also write the generated C as <output>.c")
    ap.add_argument("--json", action="store_true", help="diagnostics as JSON on stderr")
    args = ap.parse_args(argv)

    try:
        with open(args.file, encoding="utf-8") as fh:
            src = fh.read()
    except OSError as ex:
        print(f"clc: can't read {args.file}: {ex.strerror}", file=sys.stderr)
        return 2
    d, fns = front_end(args.file, src)
    if d.has_errors() or args.command == "check":
        d.report(args.json)
        return 1 if d.has_errors() else 0

    em = Emitter(fns, args.file)
    csrc = em.emit()
    tmp = tempfile.mkdtemp(prefix="clc-")
    keep_tmp = False
    try:
        cfile = os.path.join(tmp, "out.c")
        with open(cfile, "w") as fh:
            fh.write(csrc)
        if args.command == "build":
            exe = args.output or (args.file[:-3] if args.file.endswith(".cl") else args.file + ".out")
        else:
            exe = os.path.join(tmp, "prog")
        if args.emit_c:
            shutil.copy(cfile, exe + ".c")
        r = subprocess.run(["gcc", "-std=c11", "-O1", "-w", "-o", exe, cfile], capture_output=True, text=True)
        if r.returncode != 0:
            keep_tmp = True
            print(f"clc: internal error: the generated C didn't compile (this is a compiler bug). "
                  f"C kept at {cfile}\n{r.stderr[:4000]}", file=sys.stderr)
            return 2
        n = run_examples(exe, em, d)
        if d.has_errors():
            d.report(args.json)
            if args.command == "build" and os.path.exists(exe):
                os.remove(exe)
            return 1
        d.report(args.json)
        if args.command == "test" and not args.json:
            print(f"{n} example(s) passed", file=sys.stderr)
        if args.command == "run":
            return subprocess.run([exe]).returncode
        return 0
    finally:
        if not keep_tmp:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
