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
            "uses", "true", "false", "and", "or", "not", "struct", "enum", "match", "case"}
BLOCK_KINDS = ("fn", "if", "while", "for", "struct", "enum", "match")
NAMED_BLOCKS = ("fn", "struct", "enum")
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
    ".": "`.` reads a struct's field (`p.x`); there are no methods: call a function instead, e.g. "
         "`length(xs)` or `xs = append(list: xs, item: x)` (and there are no floats)",
    "'": "strings use double quotes: `\"...\"`",
    "@": "there are no decorators or annotations",
    "?": "there's no `?`: a value that may be missing is `Option[T]` (`Some(x)` or `None`), and `match` "
         "unpacks it",
    "=>": "there's no `=>`: a `case` line holds only the pattern, and the arm's statements go on the lines below",
}
OPTION_METHODS = ("unwrap", "expect", "unwrap_or", "unwrap_or_else", "is_some", "is_none", "is_ok", "is_err",
                  "get", "value", "or_else", "map", "ok", "err")
STRING_ESCAPES = {"n": "\n", "t": "\t", "\\": "\\", '"': '"', "{": "{", "}": "}"}


class Tok:
    __slots__ = ("kind", "text", "line", "col", "parts")

    def __init__(self, kind, text, line, col, parts=None):
        self.kind, self.text, self.line, self.col, self.parts = kind, text, line, col, parts

    def __repr__(self):
        return f"Tok({self.kind},{self.text!r},{self.line}:{self.col})"


INT_LIMIT = None  # Int is unbounded (D26); main() sets 2**63 - 1 for the C backend


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
        if stripped.rstrip() == "}":
            toks.append(Tok("rbrace", "}", lineno, len(line) - len(stripped) + 1))
            toks.append(Tok("nl", "", lineno, len(line) + 1))
            continue
        lex_span(line, 0, len(line), lineno, d, toks)
        if len(toks) > before:
            toks.append(Tok("nl", "", lineno, len(line) + 1))
    d.lexing = False
    toks.append(Tok("eof", "", len(lines), 1))
    return toks


def lex_dot(line, i, n, lineno, d, toks):
    """`.` reads a field (`p.x`). Otherwise catch the usual mistakes: a method call (`xs.append(4)`,
    `s.len()`), a float (`1.5`) and a range (`0..n`). Returns where to resume."""
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
        d.error("bad-char", f"`.` isn't part of the language here; {CHAR_HINTS['.']}", lineno, i + 1)
        return i + 1
    if line[j:j + 1] != "(" and (prev.kind == "name" or prev.text in (")", "]")):
        toks.append(Tok("op", ".", lineno, i + 1))
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
    elif obj and m in OPTION_METHODS:
        fix = f"unpack it with `match {obj}`, then `case Some(x)` and `case None` (or `Ok(x)` / `Err(e)`)"
    elif obj:
        fix = f"call a function with `{obj}` as an argument instead"
    d.error("method-call", f"`.{m}(...)` doesn't exist: there are no methods", lineno, i + 1, end - i, fix)
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
            elif INT_LIMIT is not None and int(digits) > INT_LIMIT:
                d.error("int-too-big", f"`{text}` doesn't fit in the C backend's 64-bit Int", lineno, col, len(text),
                        "the default Lean backend has no limit; drop `--backend c`")
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
        elif line[i:i + 2] == "=>":
            d.error("bad-char", f"`=>` isn't an operator here; {CHAR_HINTS['=>']}", lineno, col, 2)
            i += 2
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
        elif (c == "{" and toks and toks[-1].kind == "name" and toks[-1].text[:1].isupper()
              and "}" in line[i:n] and not in_interp):
            # Point { x: 1, y: 2 } (Rust, Go): recover as the call it should be
            close, nt = line.index("}", i), toks[-1]
            d.error("bad-char", "a struct is made by calling its name, with named fields", lineno, nt.col,
                    close - nt.col + 2, f"`{nt.text}({line[i + 1:close].strip()})`")
            toks.append(Tok("op", "(", lineno, col))
            lex_span(line, i + 1, close, lineno, d, toks)
            toks.append(Tok("op", ")", lineno, close + 1))
            i = close + 1
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
        if c == "{" and line[i + 1:i + 2] == '"':
            # D25: a `{` just before the closing quote can't start an interpolation (nothing follows
            # it), so it's a literal brace: `"{"`, `"set {"`.
            buf.append("{")
            i += 1
            continue
        if c == "{":
            close = line.find("}", i + 1)
            if close == -1 or close >= n:
                # Probably a literal brace (`"{x"`) or a lost `}`. Say so once, keep the brace as text and
                # go on lexing, so the string still ends at its own `"` (no second "unclosed string").
                why = "but there's no `}`"
                end = line.find('"', i + 1)
                fix = "write `\\{` for a literal brace"
                if end != -1:
                    fix += f": `{line[start:i]}\\{{{line[i + 1:end + 1]}`"
                d.error("unclosed-interpolation", f"`{{` starts an interpolation, {why}", lineno, i + 1, 1, fix)
                buf.append("{")
                i += 1
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
    elif k == "field":
        s = f"{render(e.base)}.{e.name}"
    else:
        s = "?"
    return f"({s})" if e.paren else s


def escape_text(t):
    return (t.replace("\\", "\\\\").replace('"', '\\"').replace("{", "\\{").replace("}", "\\}")
            .replace("\n", "\\n").replace("\t", "\\t"))


def opener(kind, name):
    return f"{kind} {name}" if kind in NAMED_BLOCKS else kind


def closer(kind, name):
    return f"end {kind} {name}" if kind in NAMED_BLOCKS else f"end {kind}"


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
OPTION_WORDS = ("Option", "Optional", "Maybe", "option", "optional")
RESULT_WORDS = ("Result", "Either", "result")
LIST_WORDS = ("List", "list", "Vec", "vec", "Vector", "vector", "Array", "array", "Seq", "Sequence", "Slice")
TYPE_HINTS = {"int": "Int", "i64": "Int", "i32": "Int", "Integer": "Int", "integer": "Int", "long": "Int",
              "bool": "Bool", "boolean": "Bool", "Boolean": "Bool",
              "str": "String", "Str": "String", "string": "String", "text": "String", "Text": "String"}
NO_RETURN_TYPES = ("Unit", "Void", "void", "None", "Nothing")
FN_WORDS = ("def", "func", "function", "fun", "proc")
STRUCT_WORDS = ("class", "record", "data", "type", "typedef", "dataclass", "object")
CLOSER_WORDS = {"endif": "if", "fi": "if", "endwhile": "while", "done": "while", "endfn": "fn", "endfor": "for",
                "endstruct": "struct", "endenum": "enum", "endmatch": "match"}
STMT_HINTS = {"elif": "write `else if`", "elsif": "write `else if`", "elseif": "write `else if`",
              "const": "write `let` (or `var` for a variable that changes)",
              "loop": "write `while true`"}
LINE_END_HINTS = {"is": "there's no `is`: compare with `==` (`x == None`), or unpack an Option with `match`",
                  "then": "no `then`: the block starts on the next line",
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
        # Struct names, so a type can name a struct declared further down.
        self.struct_names = {toks[j + 1].text for j in range(len(toks) - 1)
                             if toks[j].kind == "kw" and toks[j].text in ("struct", "enum")
                             and toks[j + 1].kind == "name"}

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
        """Returns (fns, structs)."""
        fns, structs = [], []
        while True:
            while self.at("nl"):
                self.next()
            t = self.peek()
            if t.kind == "eof":
                return fns, structs
            if t.kind == "kw" and t.text == "fn":
                fns.append(self.fn_decl())
                continue
            if t.kind == "kw" and t.text in ("struct", "enum"):
                structs.append(self.struct_decl(kind=t.text))
                continue
            if t.kind == "name" and t.text in STRUCT_WORDS and self.at("name", k=1):
                n = self.peek(1).text
                self.d.error("syntax", f"`{t.text}` isn't a keyword; a type with fields is declared with `struct`",
                             t.line, t.col, len(t.text), f"`struct {n}`, then one `field: Type` per line, then "
                             f"`end struct {n}`")
                structs.append(self.struct_decl(habit=True))
                continue
            if t.kind == "rbrace":
                self.next()
                self.d.error("stray-closer", "`}` doesn't close anything (and blocks end with `end <kind>`)",
                             t.line, t.col, 1, "remove this line")
                self.end_line()
                continue
            if t.kind == "name" and t.text in FN_WORDS:
                self.d.error("syntax", f"`{t.text}` isn't a keyword; functions are declared with `fn`",
                             t.line, t.col, len(t.text), "write `fn`")
                fns.append(self.fn_decl())
                continue
            self.d.error("top-level", f"only `fn`, `struct` and `enum` declarations can appear at the top level, found "
                         f"{describe(t)}",
                         t.line, t.col, len(t.text))
            self.skip_line()

    def parse_type(self, ret=False):
        t = self.peek()
        if t.kind != "name":
            self.fail("syntax", f"expected a type (Int, Bool, String, List[...] or a struct), found {describe(t)}", t)
        self.next()
        if (t.text in OPTION_WORDS or t.text in RESULT_WORDS) and (self.at_op("[") or self.at_op("<")):
            return self.generic_type(t)
        if t.text in LIST_WORDS or (t.text not in TYPES and t.text not in self.struct_names
                                    and (self.at_op("[") or self.at_op("<"))):
            return self.list_type(t)
        ty = self.simple_type(t, ret)
        if ty and self.at_op("[") and self.at_op("]", 1):  # Int[] (Java/C#)
            b = self.next()
            self.next()
            self.d.error("unknown-type", "list types are written `List[...]`", b.line, b.col, 2, f"`List[{ty}]`")
            return f"List[{ty}]"
        return ty

    def generic_type(self, t):
        """`Option[T]`, `Result[T, E]` (D24), after the name; recovers from `Optional[T]`, `Option<T>`, `Either`."""
        base, n = ("Option", 1) if t.text in OPTION_WORDS else ("Result", 2)
        b = self.next()
        close = ">" if b.text == "<" else "]"
        args = [self.parse_type()]
        while self.at_op(","):
            self.next()
            args.append(self.parse_type())
        self.expect_op(close, f"to close `{t.text}{b.text}...`")
        shown = f"{base}[{', '.join(a or '...' for a in args)}]"
        if len(args) != n:
            want = "Option[T]: one type" if base == "Option" else "Result[T, E]: the value's type and the error's"
            self.d.error("unknown-type", f"`{base}` takes {n} type(s), as in {want}", t.line, t.col, len(t.text))
            return None
        if t.text != base or close == ">":
            self.d.error("unknown-type", f"this type is written `{base}[...]`", t.line, t.col, len(t.text),
                         f"`{shown}`")
        return shown if all(args) else None

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
        if t.text in TYPES or t.text in self.struct_names:
            return t.text
        if t.text in NO_RETURN_TYPES:
            msg = "functions that return nothing leave out `-> ...`" if ret else f"`{t.text}` isn't a type"
            self.d.error("unknown-type", msg, t.line, t.col, len(t.text))
            return "Unit" if ret else None
        known = list(TYPES) + sorted(self.struct_names)
        hint = TYPE_HINTS.get(t.text) or next(iter(difflib.get_close_matches(t.text, known, 1)), None)
        structs = (f" and this file's structs and enums ({', '.join(sorted(self.struct_names))})"
                   if self.struct_names else "")
        sep = "," if self.struct_names else " and"
        self.d.error("unknown-type", f"unknown type `{t.text}`; the types are Int, Bool, String{sep} List[...]{structs}",
                     t.line, t.col,
                     len(t.text), f"write `{hint}`" if hint else None)
        return hint  # recover with the likely meaning, so one wrong name doesn't cascade

    def struct_decl(self, habit=False, kind="struct"):
        """`struct Name`, one `field: Type` per line, `end struct Name` (D22); or `enum Name`, one variant per
        line, `end enum Name` (D24). habit: the keyword was `class`, `record`... (already reported), so the
        rest of the line is skipped quietly."""
        kw = self.next()
        name, name_tok, fields = "?", kw, []
        try:
            name_tok = self.expect_name(f"for the {kind}")
            name = name_tok.text
            if habit:
                self.skip_line()
            elif self.at_op(":") or self.at_op("("):
                t = self.peek()
                what = "fields" if kind == "struct" else "variants"
                item = "`field: Type`" if kind == "struct" else "variant"
                self.d.error("syntax", f"the {what} go on the lines below, one per line", t.line, t.col, len(t.text),
                             f"`{kind} {name}`, then {item} lines, then `end {kind} {name}`")
                self.skip_line()
            else:
                self.end_line()
        except ParseError:
            self.skip_line()
        self.stack.append([kind, kw.line, name])
        end_tok = None
        while True:
            while self.at("nl"):
                self.next()
            t = self.peek()
            new_decl = t.kind == "name" and t.text in STRUCT_WORDS + FN_WORDS and self.at("name", k=1)
            if t.kind == "eof" or (t.kind == "kw" and t.text in NAMED_BLOCKS) or new_decl:
                more = "" if t.kind == "eof" else f" before the next `{t.text}`"
                self.d.error("unclosed-block", f"`{kind} {name}` (line {kw.line}) is never closed{more}",
                             t.line, t.col, max(1, len(t.text)), self.closer_fix(kind, name, kw.line, t.line))
                break
            if t.kind == "kw" and t.text == "end":
                if self.closer_line() == "mine":
                    end_tok = t
                    break
                continue
            if t.kind == "rbrace":
                self.rbrace(kind, name)
                end_tok = t
                break
            if t.kind == "name" and t.text in CLOSER_WORDS and self.at("nl", k=1):
                self.d.error("closer-kind", f"`{t.text}` isn't a keyword; write `end {kind} {name}`",
                             t.line, t.col, len(t.text), f"`end {kind} {name}`")
                self.skip_line()
                break
            try:
                f = self.field_decl(name) if kind == "struct" else self.variant_decl(name)
                if f:
                    fields.append(f)
            except ParseError:
                self.skip_line()
        self.stack.pop()
        if kind == "enum":
            return Node("enum", kw, name=name, name_tok=name_tok, variants=fields, end_tok=end_tok)
        return Node("struct", kw, name=name, name_tok=name_tok, fields=fields, end_tok=end_tok)

    def variant_decl(self, ename):
        """`Name` or `Name(field: Type, ...)`, one variant per line (D24). Returns (name, fields, tok)."""
        t = self.expect_name(f"for a variant of `enum {ename}`")
        fields = []
        if self.at_op("("):
            p = self.next()
            if self.at_op(")"):
                c = self.next()
                self.d.error("syntax", "a variant with no fields is written without `()`", p.line, p.col, 2,
                             f"`{t.text}`")
            else:
                while True:
                    ft = self.expect_name(f"for a field of `{t.text}`, e.g. `{t.text}(value: Int)`")
                    self.expect_op(":", f"after `{ft.text}`: each field is `name: Type`")
                    fields.append((ft.text, self.parse_type(), ft))
                    if self.at_op(","):
                        self.next()
                        continue
                    self.expect_op(")", f"to close `{t.text}(...`")
                    break
        self.end_line()
        return (t.text, fields, t)

    def field_decl(self, sname):
        t = self.peek()
        if t.kind == "kw" and t.text in ("let", "var"):
            self.next()
            self.d.error("syntax", f"fields are written without `{t.text}`: `name: Type`", t.line, t.col,
                         len(t.text), "drop it; a struct's fields change only through a `var` holding the struct")
            t = self.peek()
        if t.kind != "name":
            if t.kind == "kw" and t.text in ("fn",):
                self.fail("syntax", "a struct holds only fields; functions go outside it, taking the struct as a "
                          "parameter", t)
            self.fail("syntax", f"a struct holds only fields, one per line (`name: Type`), found {describe(t)}", t)
        if t.text in FN_WORDS:
            self.fail("syntax", "a struct holds only fields; functions go outside it, taking the struct as a "
                      "parameter", t)
        self.next()
        if self.at_op(","):
            c = self.peek()
            self.fail("syntax", "one field per line, each with its own type", c, f"`{t.text}: Type` on its own line")
        self.expect_op(":", f"and a type after field `{t.text}`, e.g. `{t.text}: Int`")
        ty = self.parse_type()
        if self.at_op(",") or self.at_op(";"):
            c = self.next()
            self.d.error("syntax", f"fields don't end with `{c.text}`: one field per line", c.line, c.col, 1,
                         "drop it")
        self.end_line()
        return (t.text, ty, t)

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
            if t.kind == "rbrace":
                self.rbrace(kind, name)
                return stmts, "end", t
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
            if t.kind == "kw" and t.text == "case":
                if kind == "match":
                    return stmts, "case", t
                self.d.error("stray-case", f"`case` belongs to a `match`, but the innermost open block is "
                             f"`{opener(kind, name)}` (line {line})", t.line, t.col, 4)
                self.skip_line()
                continue
            if kind == "match" and t.kind == "name" and t.text == "default":
                self.d.error("syntax", "`default` isn't a keyword; the arm that catches everything else is `case _`",
                             t.line, t.col, 7, "`case _`")
                return stmts, "case", t
            if t.kind == "kw" and t.text == "else":
                if kind == "match":
                    self.d.error("syntax", "a `match` has no `else`; the arm that catches everything else is "
                                 "`case _`", t.line, t.col, 4, "`case _`")
                    return stmts, "case", t
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

    def rbrace(self, kind, name):
        """A line that is only `}` closes the innermost block (recovery for brace habits)."""
        t = self.next()
        self.d.error("closer-kind", f"blocks don't use braces; this closes `{opener(kind, name)}`, which ends with "
                     f"`{closer(kind, name)}`", t.line, t.col, 1, f"`{closer(kind, name)}`")
        self.end_line()

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
            if kind in NAMED_BLOCKS:
                if self.at("name"):
                    nt = self.next()
                    if nt.text != name:
                        self.d.error("closer-name", f"`end {kind} {nt.text}` is closing `{kind} {name}` (line {line})",
                                     nt.line, nt.col, len(nt.text), f"`end {kind} {name}`")
                else:
                    self.d.error("closer-name", f"`end {kind}` must repeat the {'function' if kind == 'fn' else kind}'s"
                                 " name", start_tok.line, start_tok.col, len(f"end {kind}"), f"`end {kind} {name}`")
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
            if w == "match":
                return self.match_stmt()
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
            if t.text in ("switch", "when", "select") and not self.at_op("=", 1) and not self.at_op("(", 1) \
                    and not self.at("nl", k=1):
                self.d.error("syntax", f"`{t.text}` isn't a keyword; write `match`", t.line, t.col, len(t.text),
                             "`match <value>`, then `case` lines, then `end match`")
                return self.match_stmt()
            if self.at_op("=", 1):
                self.next()
                self.next()
                e = self.expr()
                self.end_line()
                return Node("assign", t, name=t.text, expr=e)
        e = self.expr()
        if self.at_op("="):
            eq = self.next()
            if e.kind not in ("index", "field"):
                self.fail("syntax", f"can't assign to `{render(e)}`; only a variable, a list item `xs[i]` or a field "
                          "`p.x` can be assigned", eq)
            v = self.expr()
            self.end_line()
            return Node("setindex" if e.kind == "index" else "setfield", t, target=e, expr=v)
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
        if self.at_kw("let") or self.at_kw("var"):
            lt = self.peek()
            self.d.error("syntax", "there's no `if let`; unpack an Option or Result with `match`", lt.line, lt.col,
                         len(lt.text), "`match <value>`, then `case Some(x)` and `case None`, then `end match`")
            self.skip_line()
            cond = None
        else:
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

    def match_stmt(self):
        """match <expr>, then `case <pattern>` arms, then `end match` (D24)."""
        kw = self.next()
        subj = self.cond_line()
        self.stack.append(["match", kw.line, None])
        arms = []
        body, how, _ = self.block_body()
        if body:
            b = body[0].tok
            self.d.error("syntax", "a `match` holds only `case` arms; every statement goes inside one", b.line, b.col,
                         1, "start the first arm with `case <variant>` above this line")
        while how == "case":
            ct = self.next()
            pat = None
            if ct.text in ("else", "default"):
                pat = Node("pat", ct, variant="_", binds=[], paren=False)
                self.skip_line()
            else:
                try:
                    pat = self.pattern()
                except ParseError:
                    self.skip_line()
            body, how, _ = self.block_body()
            arms.append((pat, body, ct))
        self.stack.pop()
        return Node("match", kw, subj=subj, arms=arms)

    def pattern(self):
        """`_`, `Variant`, `Variant(name)`, `Variant(field, field)`, `Variant(field: name, ...)` (D24)."""
        t = self.expect_name("after `case`: a variant, like `case Some(x)`, or `_`")
        if self.at_op(".") and self.at("name", k=1):
            self.next()
            v = self.next()
            self.d.error("syntax", "variants are written without their enum's name", t.line, t.col,
                         len(t.text) + 1 + len(v.text), f"`case {v.text}`")
            t = v
        n = Node("pat", t, variant=t.text, binds=[], paren=False)
        if self.at_op("("):
            n.paren = True
            self.next()
            while not self.at_op(")"):
                b = self.expect_name("to bind, like `case Some(x)`")
                if self.at_op(":"):
                    self.next()
                    nb = self.expect_name(f"after `{b.text}:`, the name to bind it to")
                    n.binds.append((b.text, nb.text, nb))
                else:
                    n.binds.append((None, b.text, b))
                if self.at_op(","):
                    self.next()
                elif not self.at_op(")"):
                    self.fail("syntax", f"expected `,` or `)` in the pattern, found {describe(self.peek())}",
                              self.peek())
            self.next()
        self.end_line()
        return n

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
        while self.at_op("[") or self.at_op("."):
            b = self.next()
            if b.text == ".":
                ft = self.expect_name("for the field after `.`")
                n = Node("field", ft, base=e, name=ft.text)
            else:
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
            if t.text == "new" and self.at("name") and self.at_op("(", 1):
                e = self.atom()
                self.d.error("syntax", "there's no `new`: a struct is made by calling its name", t.line, t.col, 3,
                             f"`{render(e)}`")
                return e
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


def is_option(t):
    return bool(t) and t.startswith("Option[")


def is_result(t):
    return bool(t) and t.startswith("Result[")


def type_args(t):
    """"Result[List[Int], String]" -> ["List[Int]", "String"]."""
    parts, depth, cur = [], 0, ""
    for ch in t[t.index("[") + 1:-1]:
        depth += {"[": 1, "]": -1}.get(ch, 0)
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    return parts + [cur.strip()]


BUILTIN_VARIANTS = ("Some", "None", "Ok", "Err")


def elem(t):
    return t[5:-1] if is_list(t) else None
_NO_NULL = "there's no null; a value that may be missing is `Option[T]`, made with `Some(x)` or `None`"
NAME_HINTS = {"True": "write `true`", "False": "write `false`", "TRUE": "write `true`",
              "FALSE": "write `false`", "null": _NO_NULL, "nil": _NO_NULL, "NULL": _NO_NULL,
              "undefined": _NO_NULL, "Nothing": _NO_NULL, "Null": _NO_NULL}


class Var:
    def __init__(self, ty, mutable, line, param=False, loop=False, over=None):
        self.ty, self.mutable, self.line, self.param, self.loop = ty, mutable, line, param, loop
        self.over = over  # for a loop variable walking a list variable: that variable's name


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
        if s.kind == "match" and s.arms and all(returns(b) for _, b, _ in s.arms):
            return True  # a match covers every case (or it's an error), so this holds
    return False


def breaks(stmts):
    """Is there a `break` for the enclosing loop in these statements (not counting inner loops)?"""
    for s in stmts:
        if s.kind == "break":
            return True
        if s.kind == "if" and (any(breaks(b) for _, b in s.branches) or breaks(s.else_body or [])):
            return True
        if s.kind == "match" and any(breaks(b) for _, b, _ in s.arms):
            return True
    return False


def sig(f, uses_io=None):
    io = f.uses_io if uses_io is None else uses_io
    ps = ", ".join(f"{n}: {t or '?'}" for n, t, _ in f.params)
    return f"fn {f.name}({ps})" + (f" -> {f.ret}" if f.ret not in ("Unit", None) else "") + (" uses io" if io else "")


class Checker:
    def __init__(self, fns, structs, d):
        self.d, self.fns, self.all = d, {}, fns
        self.in_example = False
        self.structs, self.enums, self.variants = {}, {}, {}
        enums = [st for st in structs if st.kind == "enum"]
        structs = [st for st in structs if st.kind != "enum"]
        for st in structs:
            if st.name == "?":
                continue
            if (st.name in TYPES or st.name in LIST_WORDS or st.name in BUILTINS or st.name in BUILTIN_VARIANTS
                    or st.name in ("Option", "Result")):
                self.err("reserved-name", f"`{st.name}` is built in and can't be redefined", st.name_tok)
            elif st.name in self.structs:
                self.err("duplicate-struct", f"`struct {st.name}` is already defined on line "
                         f"{self.structs[st.name].tok.line}", st.name_tok)
            else:
                self.structs[st.name] = st
            seen = {}
            for fname, _, ftok in st.fields:
                if fname in seen:
                    self.err("duplicate-name", f"field `{fname}` is already declared on line {seen[fname]}", ftok)
                seen.setdefault(fname, ftok.line)
            if not st.fields:
                self.err("empty-struct", f"`struct {st.name}` has no fields", st.name_tok,
                         "add one `name: Type` line per field")
        self.check_struct_cycles()
        self.declare_enums(enums)
        for f in fns:
            if f.name == "?":
                continue
            if f.name in BUILTINS or f.name in BUILTIN_VARIANTS:
                self.err("reserved-name", f"`{f.name}` is built in and can't be redefined", f.name_tok)
            elif f.name in self.structs:
                self.err("duplicate-fn", f"`{f.name}` is already the name of the struct on line "
                         f"{self.structs[f.name].tok.line}, and calling it makes one", f.name_tok)
            elif f.name in self.variants:
                self.err("duplicate-fn", f"`{f.name}` is already a variant of `enum {self.variants[f.name][0]}`",
                         f.name_tok)
            elif f.name in self.fns:
                self.err("duplicate-fn", f"`fn {f.name}` is already defined on line {self.fns[f.name].tok.line}",
                         f.name_tok)
            else:
                self.fns[f.name] = f

    def declare_enums(self, enums):
        """enum Name / variants / end enum Name (D24). Variant names are global, like functions."""
        for en in enums:
            if en.name == "?":
                continue
            if (en.name in TYPES or en.name in LIST_WORDS or en.name in BUILTINS or en.name in BUILTIN_VARIANTS
                    or en.name in ("Option", "Result")):
                self.err("reserved-name", f"`{en.name}` is built in and can't be redefined", en.name_tok)
                continue
            if en.name in self.structs or en.name in self.enums:
                other = self.structs.get(en.name) or self.enums.get(en.name)
                self.err("duplicate-struct", f"`{en.name}` is already defined on line {other.tok.line}", en.name_tok)
                continue
            self.enums[en.name] = en
            if not en.variants:
                self.err("empty-enum", f"`enum {en.name}` has no variants", en.name_tok,
                         "add one variant per line, like `Done` or `Moved(x: Int)`")
            for idx, (vname, fields, vtok) in enumerate(en.variants):
                if vname in self.variants:
                    self.err("duplicate-name", f"`{vname}` is already a variant of `enum {self.variants[vname][0]}`; "
                             "variant names are used without their enum's name, so each must be unique", vtok)
                elif vname in BUILTIN_VARIANTS:
                    self.err("reserved-name", f"`{vname}` is built in (it's part of `Option` or `Result`)", vtok)
                elif vname in self.structs or vname in self.enums or vname in BUILTINS or vname in TYPES:
                    self.err("duplicate-name", f"`{vname}` is already the name of a type or built-in", vtok)
                else:
                    self.variants[vname] = (en.name, idx, fields)
                seen = {}
                for fname, _, ftok in fields:
                    if fname in seen:
                        self.err("duplicate-name", f"field `{fname}` is already declared on line {seen[fname]}", ftok)
                    seen.setdefault(fname, ftok.line)

    def check_struct_cycles(self):
        """A struct can't contain itself except through a list: there's no null, so it could never be made."""
        def direct(t):  # struct types reached without going through a List
            return [t] if t in self.structs else []
        reported = set()
        for name, st in self.structs.items():
            stack, seen = [(name, [name])], set()
            while stack:
                cur, path = stack.pop()
                for fname, ft, ftok in self.structs[cur].fields:
                    for nxt in direct(ft):
                        if nxt == name and name not in reported:
                            reported.update(path)
                            via = " -> ".join(path + [name])
                            self.err("recursive-struct", f"`{name}` contains itself ({via}), so one could never be "
                                     "made: there's no null", st.name_tok,
                                     f"hold the inner ones in a list, which can be empty: `{fname}: List[{ft}]`")
                        elif nxt not in seen:
                            seen.add(nxt)
                            stack.append((nxt, path + [nxt]))

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
                self.err_at("type-mismatch", f"`{s.name}` is declared {s.ann}, but the value is {t}", s.expr,
                            self.wrap_fix(s.expr, t, s.ann))
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
                self.err_at("type-mismatch", f"`{s.name}` is {v.ty}, but the value is {t}", s.expr,
                            self.wrap_fix(s.expr, t, v.ty))
        elif k in ("setindex", "setfield"):
            self.set_path(s)
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
                    fix = self.wrap_fix(s.expr, t, ret)
                    if fix and (is_option(ret) or is_result(ret)):
                        fix = "`return " + fix[1:]
                    self.err_at("type-mismatch", f"`fn {self.cur.name}` returns {ret}, but this is {t}", s.expr, fix)
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
        elif k == "match":
            self.match_stmt(s)
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
                root = lst
                while root.kind in ("index", "field"):
                    root = root.base
                fix = (f"`{render(lst)} = append(list: {render(lst)}, item: {render(item)})`" if root.kind == "name"
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
                over = s.src.name if s.src is not None and s.src.kind == "name" and vt else None
                self.scopes[-1][s.var] = Var(vt, False, s.tok.line, loop=True, over=over)
        self.loops += 1
        self.block(s.body)
        self.loops -= 1
        self.scopes.pop()

    def match_stmt(self, s):
        """match x / case Variant(bindings) ... / end match: exhaustive, no fall-through (D24)."""
        t = self.expr(s.subj)
        vs = self.variants_of(t)
        if t and vs is None:
            self.err_at("not-an-enum", f"`match` needs an enum, Option or Result, but `{render(s.subj)}` is {t}",
                        s.subj, "use `if` / `else if` to compare it" if t in TYPES else None)
        what = f"enum {t}" if t in self.enums else t
        seen, wild = {}, None
        for pat, body, ct in s.arms:
            self.scopes.append({})
            if pat is not None:
                pat.slots = []
                if wild is not None:
                    self.err("unreachable-case", f"this `case` comes after `case _` (line {wild.tok.line}), so it can "
                             "never run", pat.tok, "move `case _` to the end")
                if pat.variant == "_":
                    if pat.paren:
                        self.err("syntax", "`case _` matches anything and binds nothing", pat.tok, "`case _`")
                    wild = wild or pat
                elif vs is not None:
                    names = [v[0] for v in vs]
                    if pat.variant not in names:
                        info = self.variants.get(pat.variant)
                        sg = difflib.get_close_matches(pat.variant, names, 1)
                        where = (f" (it's a variant of `enum {info[0]}`)" if info else
                                 " (it's part of Option)" if pat.variant in ("Some", "None") else
                                 " (it's part of Result)" if pat.variant in ("Ok", "Err") else "")
                        self.err("unknown-variant", f"`{what}` has no variant `{pat.variant}`{where}; its variants "
                                 f"are {', '.join(names)}", pat.tok, f"did you mean `case {sg[0]}`?" if sg else None)
                    elif pat.variant in seen:
                        self.err("unreachable-case", f"`case {pat.variant}` already appears on line {seen[pat.variant]}",
                                 pat.tok, "merge the two arms")
                    else:
                        seen[pat.variant] = pat.tok.line
                        pat.tag = names.index(pat.variant)
                        self.bind_pattern(pat, vs[pat.tag][1])
            self.block(body)
            self.scopes.pop()
        if vs is not None and wild is None:
            missing = [v for v in vs if v[0] not in seen]
            if missing:
                lines = ", ".join(f"`case {v}" + (f"({', '.join(f[0] for f in fs)})`" if fs else "`")
                                  for v, fs in missing)
                self.err("non-exhaustive", f"this `match` doesn't handle {', '.join(v[0] for v in missing)}; every "
                         f"variant of `{what}` needs a `case` (or end with `case _`)", s.tok, f"add {lines}")

    def variants_of(self, t):
        """[(variant, fields)] for a type `match` can take apart (in tag order), else None."""
        if t in self.enums:
            return [(v, fs) for v, fs, _ in self.enums[t].variants]
        if is_option(t):
            return [("Some", [("value", type_args(t)[0], None)]), ("None", [])]
        if is_result(t):
            a = type_args(t)
            return [("Ok", [("value", a[0], None)]), ("Err", [("error", a[1], None)])]
        return None

    def wrap_fix(self, e, t, want):
        """A fix for a type mismatch between T and Option[T] / Result[T, E], either way round."""
        if not t or not want or e is None:
            return None
        r = render(e)
        if is_option(t) and type_args(t)[0] == want:
            return (f"`{r}` may be missing, so unpack it first: `match {r}`, then `case Some(x)` (use `x` there) "
                    "and `case None`, then `end match`")
        if is_result(t) and type_args(t)[0] == want:
            return (f"`{r}` may be an error, so unpack it first: `match {r}`, then `case Ok(x)` (use `x` there) "
                    "and `case Err(e)`, then `end match`")
        if is_option(want) and type_args(want)[0] == t:
            return f"`Some({r})`"
        if is_result(want):
            a, b = type_args(want)
            if t == a:
                return f"`Ok({r})`"
            if t == b:
                return f"`Err({r})`"
        return None

    def builtin_variant(self, e, want):
        """Some(x), Ok(x), Err(e) (D24); `None` is in _expr."""
        name = e.name
        fname = "error" if name == "Err" else "value"
        if len(e.args) != 1:
            for _, _, a in e.args:
                self.expr(a)
            self.err("arg-count", f"`{name}` holds exactly one value, but this passes {len(e.args)}", e.tok,
                     f"`{name}(...)`")
            return None
        n, ntok, a = e.args[0]
        if n is not None and n != fname:
            self.err("unknown-arg-name", f"`{name}`'s field is `{fname}`, not `{n}`", ntok, f"`{name}({render(a)})`")
        e.order = [0]
        if name == "Some":
            inner = type_args(want)[0] if is_option(want) else None
            t = self.expr(a, want=inner)
            e.variant = ("Option", 0)
            if t == "Unit":
                self.err_at("unit-value", f"`{render(a)}` returns nothing, so there's nothing to hold", a)
                return None
            if inner and t and t != inner:
                self.err_at("type-mismatch", f"this is {want}, so `Some` holds {inner}, but `{render(a)}` is {t}", a,
                            self.wrap_fix(a, t, inner))
                return want
            return want if is_option(want) else (f"Option[{t}]" if t else None)
        e.variant = ("Result", 0 if name == "Ok" else 1)
        if not is_result(want):
            t = self.expr(a)
            if want:
                self.err_at("type-mismatch", f"`{name}(...)` is a Result, but this needs {want}", e,
                            f"if it can fail, make the type `Result[{want}, ...]`")
            else:
                self.err_at("needs-type", f"`{name}(...)` needs its full Result type known here", e,
                            "use it where the type is known: a `return` from a function returning `Result[T, E]`, "
                            "an argument, or `let r: Result[Int, String] = ...`")
            return None
        exp = type_args(want)[0 if name == "Ok" else 1]
        t = self.expr(a, want=exp)
        if t and t != exp:
            self.err_at("type-mismatch", f"this is {want}, so `{name}` holds {exp}, but `{render(a)}` is {t}", a,
                        self.wrap_fix(a, t, exp))
        return want

    def bind_pattern(self, pat, fields):
        v, fnames = pat.variant, [f[0] for f in fields]
        if not fields:
            if pat.paren:
                self.err("syntax", f"`{v}` has no fields, so its case is written `case {v}`", pat.tok, f"`case {v}`")
            return
        targets = []
        if len(fields) == 1 and len(pat.binds) == 1 and pat.binds[0][0] is None:
            targets.append((0, pat.binds[0][1], pat.binds[0][2]))
        elif (len(pat.binds) == len(fields) and all(f is None for f, _, _ in pat.binds)
              and not any(n in fnames for _, n, _ in pat.binds)):
            # case Move(a, b): positional, which could silently swap fields; say which is which
            fixed = ", ".join(f"{fn}: {n}" for fn, (_, n, _) in zip(fnames, pat.binds))
            self.err("unnamed-bind", f"`{v}` has more than one field, so a pattern binds them by name, not position",
                     pat.binds[0][2], f"`case {v}({fixed})`")
            targets = [(k, n, t) for k, (_, n, t) in enumerate(pat.binds)]
        else:
            used = set()
            for fld, name, tok in pat.binds:
                key = fld or name
                if key not in fnames:
                    sg = difflib.get_close_matches(key, fnames, 1)
                    fix = (f"`{sg[0]}: {key}` binds the field `{sg[0]}` to the name `{key}`" if sg and fld is None
                           else f"did you mean `{sg[0]}`?" if sg else None)
                    self.err("no-field", f"`{v}` has no field `{key}` (it has {', '.join(fnames)}); in a pattern, a "
                             "bare name binds the field with that name", tok, fix)
                    continue
                if key in used:
                    self.err("duplicate-name", f"the field `{key}` is bound twice", tok)
                    continue
                used.add(key)
                targets.append((fnames.index(key), name, tok))
        for k, name, tok in targets:
            if name == "_":
                continue
            prev = self.lookup(name)
            if prev:
                self.err("duplicate-name", f"`{name}` is already defined on line {prev.line}; a name means one thing "
                         "within a function", tok, f"bind it to another name: `{fnames[k]}: other_name`")
                continue
            self.scopes[-1][name] = Var(fields[k][1], False, tok.line)
            pat.slots.append((k, name, fields[k][1]))

    def set_path(self, s):
        """xs[i] = v, p.x = v, and any deeper path: ps[i].score = v, grid[i][j] = v, a.b.c = v (D23).
        The root must be a `var`; every level is its own value, so only the copy being changed changes."""
        tgt = s.target
        root = tgt
        while root.kind in ("index", "field"):
            root = root.base
        if root.kind != "name":
            self.err_at("syntax", f"can't assign into `{render(root)}`; assign to a variable or a part of one: "
                        "`xs[i] = v`, `p.x = v`, `ps[i].x = v`", root)
            self.expr(s.expr)
            return
        v = self.lookup(root.name)
        if v is None:
            self.unknown_name(root.tok)
            self.expr(s.expr)
            return
        if v.loop and v.over:
            # for p in ps / p.score = ...: p is a copy, so this would change nothing anyone can see.
            i = next(n for n in ("i", "j", "k", "idx", "index") if self.lookup(n) is None)
            rest = render(tgt)[len(root.name):]
            self.err("assign-to-loop-var", f"`{root.name}` is a copy of each item of `{v.over}`, so changing it "
                     f"wouldn't change `{v.over}`", root.tok,
                     f"loop over the indexes: `for {i} in 0 until length({v.over})`, then "
                     f"`{v.over}[{i}]{rest} = ...`, using `{v.over}[{i}]` where you used `{root.name}`")
            self.expr(tgt)
            self.expr(s.expr)
            return
        ok = self.check_mutable(root.name, v, root.tok)
        tt = self.expr(tgt)
        if tgt.kind == "index":
            self.no_negative_index(tgt)
        t = self.expr(s.expr, want=tt)
        if ok and tt and t and t != tt:
            b = tgt.base
            if tgt.kind == "index" and b.ty:
                self.err_at("type-mismatch", f"`{render(b)}` is {b.ty}, so its items are {tt}, but the value is {t}",
                            s.expr, self.wrap_fix(s.expr, t, tt))
            else:
                self.err_at("type-mismatch", f"`{render(tgt)}` is {tt}, but the value is {t}", s.expr,
                            self.wrap_fix(s.expr, t, tt))

    def field_type(self, e, bt):
        """The type of field e.name of a value of type bt, or None (reported)."""
        if bt is None:
            return None
        b = render(e.base)
        if bt not in self.structs:
            fix = None
            if (is_list(bt) or bt == "String") and e.name in ("len", "length", "size", "count"):
                fix = f"`length({b})`"
            what = "a list" if is_list(bt) else bt
            self.err("no-field", f"`{b}` is {bt}; only structs have fields, and {what} has none", e.tok, fix)
            return None
        st = self.structs[bt]
        for fname, ft, _ in st.fields:
            if fname == e.name:
                e.index_of = [f[0] for f in st.fields].index(fname)
                return ft
        names = [f[0] for f in st.fields]
        sg = difflib.get_close_matches(e.name, names, 1)
        self.err("no-field", f"`struct {bt}` has no field `{e.name}` (it has {', '.join(names)})", e.tok,
                 f"did you mean `{b}.{sg[0]}`?" if sg else None)
        return None

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
            self.err_at("type-mismatch", f"{what} needs {want}, but `{render(e)}` is {t}", e,
                        fix or self.wrap_fix(e, t, want))

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
            if e.name == "None":
                e.variant = ("Option", 1)
                if is_option(want):
                    return want
                if want:
                    self.err_at("type-mismatch", f"`None` is an empty Option, but this needs {want}", e,
                                f"if it can be missing, make the type `Option[{want}]` and use `Some(x)` for a value")
                else:
                    self.err_at("needs-type", "`None` needs its type known here", e,
                                "say which, e.g. `var best: Option[Int] = None`")
                return None
            if e.name in self.variants:
                en, idx, fields = self.variants[e.name]
                if fields:
                    self.err("arg-count", f"`{e.name}` has fields, so making one gives each a value", e.tok,
                             f"`{e.name}(" + ", ".join(f"{f[0]}: ..." for f in fields) + ")`")
                    return en
                e.variant = (en, idx)
                return en
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
                    self.err_at("type-mismatch", f"can't compare {lt} with {rt}", e,
                                self.wrap_fix(e.right, rt, lt) or self.wrap_fix(e.left, lt, rt))
                return "Bool"
            self.need(e.left, lt, "Bool", op)
            self.need(e.right, rt, "Bool", op)
            return "Bool"
        if k == "field":
            return self.field_type(e, self.expr(e.base))
        if k == "call":
            return self.call(e, want)
        return None

    def match_args(self, name, pnames, e, what="parameter", decl=None):
        """Check argument names against the parameters (D4). Returns order, where order[i] is the index of the
        parameter args[i] fills, or None if the count is wrong (already reported)."""
        args = e.args
        names = [n for n, _, _ in args]
        want = f"`{name}({', '.join(p + ': ...' for p in pnames)})`"
        decl = decl or (f"`fn {name}`" if what == "parameter" else f"`struct {name}`")
        if len(args) != len(pnames):
            if what == "field":
                given = {n for n, _, _ in args}
                missing = [p for p in pnames if p not in given]
                miss = ""
                if missing and None not in given:
                    miss = f" (missing {', '.join(missing)})"
                    by = {n: a for n, _, a in args}
                    want = f"`{name}(" + ", ".join(f"{p}: {render(by[p]) if p in by else '...'}" for p in pnames) + ")`"
                self.err("arg-count", f"`{name}` has {len(pnames)} field(s), and making one gives every field a "
                         f"value, but this passes {len(args)}{miss}", e.tok, want)
            else:
                self.err("arg-count", f"`{name}` takes {len(pnames)} argument(s), but this call passes {len(args)}",
                         e.tok, want)
            return None
        order = list(range(len(args)))
        if len(pnames) == 1:
            if names[0] is not None and names[0] != pnames[0]:
                self.err("unknown-arg-name", f"`{name}`'s {what} is `{pnames[0]}`, not `{names[0]}`",
                         args[0][1], f"`{pnames[0]}: ...` or no name")
        elif len(pnames) > 1:
            if any(n is None for n in names):
                fixed = f"{name}(" + ", ".join(f"{p}: {render(a)}" for p, (_, _, a) in zip(pnames, args)) + ")"
                self.err("unnamed-arg", f"`{name}` has more than one field, so each value is named with its field"
                         if what == "field" else f"`{name}` takes more than one argument, so each one must be named",
                         e.tok, f"`{fixed}`")
            else:
                bad = [(n, t) for n, t, _ in args if n not in pnames]
                for n, t in bad:
                    sg = difflib.get_close_matches(n, pnames, 1)
                    self.err("unknown-arg-name", f"`{name}` has no {what} `{n}` (it has {', '.join(pnames)})",
                             t, f"did you mean `{sg[0]}`?" if sg else None)
                if not bad:
                    if len(set(names)) != len(names):
                        self.err("duplicate-arg", "the same argument is given twice", e.tok, want)
                    else:
                        order = [pnames.index(n) for n in names]
                        if names != pnames:
                            by = {n: a for n, _, a in args}
                            fixed = f"{name}(" + ", ".join(f"{p}: {render(by[p])}" for p in pnames) + ")"
                            self.err("arg-order", f"arguments must come in the order {decl} declares them "
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
        if name in self.structs:
            e.ctor = True
            return self.construct(e, self.structs[name].fields)
        if name in ("Some", "Ok", "Err"):
            return self.builtin_variant(e, want)
        if name in self.variants:
            en, idx, fields = self.variants[name]
            e.variant = (en, idx)
            if not fields:
                self.err("arg-count", f"`{name}` has no fields, so it's written without `()`", e.tok, f"`{name}`")
                for _, _, a in e.args:
                    self.expr(a)
                e.order = []
                e.args = []
                return en
            self.construct(e, fields, decl=f"`{name}`")
            return en
        f = self.fns.get(name)
        if f is None:
            for _, _, a in e.args:
                self.expr(a)
            sugg = difflib.get_close_matches(name, list(self.fns) + list(BUILTINS) + list(self.structs)
                                             + list(self.variants), 1)
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
                self.err_at("type-mismatch", f"`{name}`'s `{pn}` is {pt}, but `{render(a)}` is {t}", a,
                            self.wrap_fix(a, t, pt))
        return f.ret

    def construct(self, e, fields, decl=None):
        """Point(x: 1, y: 2) or Moved(x: 1, y: 2): every field, named, in the declared order, like any
        call (D4)."""
        order = self.match_args(e.name, [f[0] for f in fields], e, what="field", decl=decl)
        for i, (_, _, a) in enumerate(e.args):
            if order is None:
                self.expr(a)
                continue
            fn, ft, _ = fields[order[i]]
            t = self.expr(a, want=ft)
            if t == "Unit":
                self.err_at("unit-value", f"`{render(a)}` returns nothing, so it can't be a field", a)
            elif ft and t and ft != t:
                self.err_at("type-mismatch", f"`{e.name}`'s `{fn}` is {ft}, but `{render(a)}` is {t}", a,
                            self.wrap_fix(a, t, ft))
        e.order = order
        return e.name

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


STRUCT_IDS = {}  # struct name -> index in the runtime's cl_recs table; set by Emitter
ENUM_IDS = {}  # enum name -> index in the runtime's cl_enums table (D24); set by Emitter


def is_ref(t):
    """Lists and structs: a cl_list * with copy-on-write (D19, D22)."""
    return bool(t) and (is_list(t) or is_option(t) or is_result(t) or t in STRUCT_IDS or t in ENUM_IDS)


def ctype(t):
    return "cl_list *" if is_ref(t) else CTYPE[t]


def slot(t):
    return "l" if is_ref(t) else SLOT[t]


def desc(t):
    """Type descriptor the runtime uses to show, compare and copy values: I, B, S, L + item descriptor,
    or R + the struct's index in cl_recs."""
    if is_list(t):
        return "L" + desc(elem(t))
    if t in STRUCT_IDS:
        return f"R{STRUCT_IDS[t]}"
    if t in ENUM_IDS:
        return f"E{ENUM_IDS[t]}"
    if is_option(t):
        return "O" + desc(type_args(t)[0])
    if is_result(t):
        a, b = type_args(t)
        return "Q" + desc(a) + desc(b)
    return t[0]

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
    int64_t q = a / b;  /* Euclidean (D27): a == b * (a / b) + a % b with 0 <= a % b < |b| */
    if (a % b < 0) q += b > 0 ? -1 : 1;
    return q; }
static int64_t cl_mod(int64_t a, int64_t b, int l, int c) {
    if (b == 0) cl_trap("division by zero in `%`", l, c);
    if (b == -1) return 0;
    int64_t r = a % b;
    if (r < 0) r = b > 0 ? r + b : r - b;  /* never negative (D27); r - b can't overflow, since r < 0 */
    return r; }
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
/* A struct value (D22) is a cl_list with one item per field, so it shares the lists' copy-on-write.
   Descriptors: I, B, S, L + item descriptor, R + index into cl_recs. */
typedef struct { const char *name; int n; const char *const *fields; const char *const *descs; } cl_rec_info;
@RECS@
/* An enum value (D24) is a cl_list too: item 0 is the variant's index, items 1.. its fields. */
typedef struct { const char *name; int nv; const cl_rec_info *vs; } cl_enum_info;
@ENUMS@
#define CL_REF(d) ((d)[0] == 'L' || (d)[0] == 'R' || (d)[0] == 'E' || (d)[0] == 'O' || (d)[0] == 'Q')
/* Option (O + T) and Result (Q + T + E) are tagged like enums: Some/Ok 0, None/Err 1, value in item 1. */
static const char *cl_desc_skip(const char *d) {
    switch (*d) {
    case 'L': case 'O': return cl_desc_skip(d + 1);
    case 'Q': return cl_desc_skip(cl_desc_skip(d + 1));
    case 'R': case 'E': d++; while (*d >= '0' && *d <= '9') d++; return d;
    default: return d + 1; } }
static const cl_enum_info *cl_enum(const char *d) { return &cl_enums[atoi(d + 1)]; }
static const cl_rec_info *cl_rec(const char *d) { return &cl_recs[atoi(d + 1)]; }
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
    if (CL_REF(d)) for (int64_t i = 0; i < l->len; i++) l->items[i].l->rc++;
    return l; }
static cl_list *cl_rec_copy(cl_list *src, const char *d) {
    const cl_rec_info *r = cl_rec(d);
    cl_list *l = cl_list_new(src->len, 0, 0);
    memcpy(l->items, src->items, sizeof(cl_val) * (size_t)src->len); l->len = src->len;
    for (int k = 0; k < r->n; k++) if (CL_REF(r->descs[k])) l->items[k].l->rc++;
    return l; }
static void cl_rec_set(cl_list **p, int k, cl_val v, const char *d) {
    if ((*p)->rc > 1) { (*p)->rc--; *p = cl_rec_copy(*p, d); }
    if (CL_REF(cl_rec(d)->descs[k])) (*p)->items[k].l->rc--;
    (*p)->items[k] = v; }
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
    if (CL_REF(d)) (*p)->items[i].l->rc--;
    (*p)->items[i] = v; }
/* Assignment paths (D23): ps[i].score = v steps down with cl_list_at / cl_rec_at, which make each level
   unique (copying it if shared) and return the slot holding the next level. */
static cl_list **cl_list_at(cl_list **p, int64_t i, const char *d, int line, int col) {
    cl_index_check(*p, i, line, col); cl_unshare(p, (*p)->len, d); return &(*p)->items[i].l; }
static cl_list **cl_rec_at(cl_list **p, int k, const char *d) {
    if ((*p)->rc > 1) { (*p)->rc--; *p = cl_rec_copy(*p, d); }
    return &(*p)->items[k].l; }
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
    if (CL_REF(d)) v.l->rc += n - 1;
    return l; }
static bool cl_list_eq(cl_list *a, cl_list *b, const char *d);
static bool cl_val_eq(cl_val a, cl_val b, const char *d) {
    switch (d[0]) {
    case 'I': return a.i == b.i;
    case 'B': return a.b == b.b;
    case 'S': return strcmp(a.s, b.s) == 0;
    case 'R': {
        if (a.l == b.l) return true;
        const cl_rec_info *r = cl_rec(d);
        for (int k = 0; k < r->n; k++) if (!cl_val_eq(a.l->items[k], b.l->items[k], r->descs[k])) return false;
        return true; }
    case 'O': case 'Q': {
        if (a.l == b.l) return true;
        int64_t t = a.l->items[0].i;
        if (t != b.l->items[0].i) return false;
        if (d[0] == 'O') return t == 1 || cl_val_eq(a.l->items[1], b.l->items[1], d + 1);
        return cl_val_eq(a.l->items[1], b.l->items[1], t == 0 ? d + 1 : cl_desc_skip(d + 1)); }
    case 'E': {
        if (a.l == b.l) return true;
        if (a.l->items[0].i != b.l->items[0].i) return false;
        const cl_rec_info *r = &cl_enum(d)->vs[a.l->items[0].i];
        for (int k = 0; k < r->n; k++) if (!cl_val_eq(a.l->items[k + 1], b.l->items[k + 1], r->descs[k])) return false;
        return true; }
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
    case 'R': {  /* Point(x: 1, y: 2), the way one is made */
        const cl_rec_info *r = cl_rec(d);
        cl_put(b, r->name, strlen(r->name)); cl_put(b, "(", 1);
        for (int k = 0; k < r->n; k++) {
            if (k) cl_put(b, ", ", 2);
            cl_put(b, r->fields[k], strlen(r->fields[k])); cl_put(b, ": ", 2);
            cl_show_into(b, v.l->items[k], r->descs[k]); }
        cl_put(b, ")", 1); break; }
    case 'O': case 'Q': {  /* Some(3), None, Ok(3), Err("bad") */
        int64_t t = v.l->items[0].i;
        if (d[0] == 'O' && t == 1) { cl_put(b, "None", 4); break; }
        const char *name = d[0] == 'O' ? "Some" : t == 0 ? "Ok" : "Err";
        cl_put(b, name, strlen(name)); cl_put(b, "(", 1);
        cl_show_into(b, v.l->items[1], d[0] == 'Q' && t == 1 ? cl_desc_skip(d + 1) : d + 1);
        cl_put(b, ")", 1); break; }
    case 'E': {  /* Moved(x: 1, y: 2), or a bare Done */
        const cl_rec_info *r = &cl_enum(d)->vs[v.l->items[0].i];
        cl_put(b, r->name, strlen(r->name));
        if (r->n) {
            cl_put(b, "(", 1);
            for (int k = 0; k < r->n; k++) {
                if (k) cl_put(b, ", ", 2);
                cl_put(b, r->fields[k], strlen(r->fields[k])); cl_put(b, ": ", 2);
                cl_show_into(b, v.l->items[k + 1], r->descs[k]); }
            cl_put(b, ")", 1); }
        break; }
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
    def __init__(self, fns, structs, path):
        self.fns, self.path = fns, path
        self.structs = [st for st in structs if st.name != "?" and st.kind == "struct"]
        self.enums = [st for st in structs if st.name != "?" and st.kind == "enum"]
        STRUCT_IDS.clear()
        STRUCT_IDS.update({st.name: i for i, st in enumerate(self.structs)})
        ENUM_IDS.clear()
        ENUM_IDS.update({en.name: i for i, en in enumerate(self.enums)})
        self.examples = [s for f in fns for s in f.body if s.kind == "example"]

    def recs(self):
        """The cl_recs table: each struct's name, field names and field descriptors."""
        out, rows = [], []
        for i, st in enumerate(self.structs):
            out.append(f"static const char *const cl_rf{i}[] = {{" + ", ".join(c_string(f[0]) for f in st.fields)
                       + "};")
            out.append(f"static const char *const cl_rd{i}[] = {{" + ", ".join(c_string(desc(f[1])) for f in st.fields)
                       + "};")
            rows.append(f"{{{c_string(st.name)}, {len(st.fields)}, cl_rf{i}, cl_rd{i}}}")
        out.append("static const cl_rec_info cl_recs[] = {" + (", ".join(rows) or "{0}") + "};")
        return "\n".join(out)

    def enum_table(self):
        """The cl_enums table: each enum's name and, per variant, its name, field names and descriptors."""
        out, rows = [], []
        for i, en in enumerate(self.enums):
            vs = []
            for j, (vname, fields, _) in enumerate(en.variants):
                if fields:
                    out.append(f"static const char *const cl_ef{i}_{j}[] = {{"
                               + ", ".join(c_string(f[0]) for f in fields) + "};")
                    out.append(f"static const char *const cl_ed{i}_{j}[] = {{"
                               + ", ".join(c_string(desc(f[1])) for f in fields) + "};")
                    vs.append(f"{{{c_string(vname)}, {len(fields)}, cl_ef{i}_{j}, cl_ed{i}_{j}}}")
                else:
                    vs.append(f"{{{c_string(vname)}, 0, NULL, NULL}}")
            out.append(f"static const cl_rec_info cl_ev{i}[] = {{" + ", ".join(vs) + "};")
            rows.append(f"{{{c_string(en.name)}, {len(en.variants)}, cl_ev{i}}}")
        out.append("static const cl_enum_info cl_enums[] = {" + (", ".join(rows) or "{0}") + "};")
        return "\n".join(out)

    def emit(self):
        out = [RUNTIME.replace("@FILE@", json.dumps(self.path)).replace("@RECS@", self.recs())
               .replace("@ENUMS@", self.enum_table())]
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
            if e.kind == "bin" and e.op == "==" and not e.paren and is_ref(e.left.ty):
                d = c_string(desc(e.left.ty))
                out.append(f"    {{ cl_list *l = {self.expr(e.left)}; cl_list *r = {self.expr(e.right)};")
                out.append(f'      if (!cl_val_eq((cl_val){{.l = l}}, (cl_val){{.l = r}}, {d})) {{ printf("EXFAILV {i} "); '
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
            elif k in ("setfield", "setindex"):
                out.extend(ind + line for line in self.set_path(s))
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
            elif k == "match":
                # An `if` chain, never `switch`, so a `break` in an arm reaches the enclosing loop (D24).
                self.tmp += 1
                m = f"cl_m{self.tmp}"
                out.append(f"{ind}{{ cl_list *{m} = {self.expr(s.subj)};")
                arms = [(pat, body) for pat, body, _ in s.arms if pat is not None]
                for j, (pat, body) in enumerate(arms):
                    cond = "1" if pat.variant == "_" else f"{m}->items[0].i == {pat.tag}"
                    out.append(f"{ind}{'if' if j == 0 else '} else if'} ({cond}) {{")
                    for fk, name, ty in pat.slots:
                        out.append(f"{ind}    {ctype(ty)} v_{name} = {m}->items[{fk + 1}].{slot(ty)};")
                        self.params.add(name)  # borrowed from the matched value, like a parameter
                    self.block(body, depth + 1, out)
                if arms:
                    out.append(f"{ind}}}")
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
            shared = s.src.kind in ("name", "index", "field")
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

    def set_path(self, s):
        """C for xs[i] = v, p.x = v and deeper paths (D23). The value is computed first, then the indexes
        left to right, then the path is walked; so `t.kids[0] = t` stores the old `t`, never a cycle."""
        tgt, e = s.target, s.expr
        steps = []
        n = tgt
        while n.kind in ("index", "field"):
            steps.append(n)
            n = n.base
        steps.reverse()
        pure = all(x.kind == "field" or x.index.kind in ("int", "name") for x in steps)
        if (e.kind == "call" and e.name == "append" and len(e.args) == 2 and pure
                and render(next(a for nm, _, a in e.args if nm == "list")) == render(tgt)):
            # ps[i].items = append(list: ps[i].items, item: x): grow the list in place, as for a variable
            item = next(a for nm, _, a in e.args if nm == "item")
            lines = [f"{{ cl_val cl_nv = {self.val(item, own=True)};"]
            idx = {id(x): self.expr(x.index) for x in steps if x.kind == "index"}
            lines.append(f"  cl_list_push({self.path_ptr(tgt, idx)}, cl_nv, {c_string(desc(elem(tgt.ty)))}); }}")
            return lines
        lines = [f"{{ cl_val cl_nv = {self.val(e, own=True)};"]
        idx = {}
        for j, x in enumerate(steps):
            if x.kind == "index":
                idx[id(x)] = f"cl_i{j}"
                lines.append(f"  int64_t cl_i{j} = {self.expr(x.index)};")
        b = self.path_ptr(tgt.base, idx)
        if tgt.kind == "index":
            lines.append(f"  cl_list_set({b}, {idx[id(tgt)]}, cl_nv, {c_string(desc(tgt.ty))}, {tgt.tok.line}, "
                         f"{tgt.tok.col}); }}")
        else:
            lines.append(f"  cl_rec_set({b}, {tgt.index_of}, cl_nv, {c_string(desc(tgt.base.ty))}); }}")
        return lines

    def path_ptr(self, e, idx):
        """C for a cl_list ** to the slot holding e, a list or struct reached from a variable, making each
        level on the way unique."""
        if e.kind == "name":
            return f"&v_{e.name}"
        b = self.path_ptr(e.base, idx)
        if e.kind == "index":
            return f"cl_list_at({b}, {idx[id(e)]}, {c_string(desc(e.ty))}, {e.tok.line}, {e.tok.col})"
        return f"cl_rec_at({b}, {e.index_of}, {c_string(desc(e.base.ty))})"

    def own(self, e):
        """C for e when the result is stored (a variable, list slot or return value): a list read from a
        variable or another list is shared, so a later mutation of either copies first (D19)."""
        c = self.expr(e)
        if is_ref(e.ty) and e.kind in ("name", "index", "field"):
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
        if k == "field":
            return f"({self.expr(e.base)})->items[{e.index_of}].{slot(e.ty)}"
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
            if getattr(e, "variant", None):
                return f"cl_list_of(1, (cl_val){{.i = INT64_C({e.variant[1]})}})"
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
            if e.op in ("==", "!=") and is_ref(e.left.ty) and not is_list(e.left.ty):
                return (f"({'' if e.op == '==' else '!'}cl_val_eq((cl_val){{.l = {l}}}, (cl_val){{.l = {r}}}, "
                        f"{c_string(desc(e.left.ty))}))")
            if e.op in ("==", "!=") and is_list(e.left.ty):
                return f"({'' if e.op == '==' else '!'}cl_list_eq({l}, {r}, {c_string(desc(elem(e.left.ty)))}))"
            op = {"and": "&&", "or": "||"}.get(e.op, e.op)
            return f"({l} {op} {r})"
        if k == "call":
            if e.name == "print":
                a = e.args[0][2]
                if is_ref(a.ty):
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
            if getattr(e, "variant", None):  # Moved(x: 1, y: 2): the tag, then the fields in declared order
                vals = [None] * len(e.args)
                for i, (_, _, a) in enumerate(e.args):
                    vals[e.order[i]] = self.val(a, own=True)
                return (f"cl_list_of({len(vals) + 1}, (cl_val){{.i = INT64_C({e.variant[1]})}}"
                        + "".join(", " + v for v in vals) + ")")
            if getattr(e, "ctor", False):  # Point(x: 1, y: 2): fields in declared order
                vals = [None] * len(e.args)
                for i, (_, _, a) in enumerate(e.args):
                    vals[e.order[i]] = self.val(a, own=True)
                return f"cl_list_of({len(vals)}, " + ", ".join(vals) + ")"
            # Arguments are borrowed: parameters can't change, and storing one anywhere shares it.
            return f"f_{e.name}(" + ", ".join(self.expr(a) for _, _, a in e.args) + ")"
        raise AssertionError(f"can't emit {k}")


# ------------------------------------------------------------------ driver


def front_end(path, src):
    d = Diags(path, src)
    fns, structs = Parser(lex(src, d), d).program()
    try:
        Checker(fns, structs, d).run()
    except Exception:
        if not d.has_errors():  # a crash on a clean parse is a compiler bug
            raise
    return d, fns, structs


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
    example_diags(out, err, timed_out, em, d)
    return len(em.examples)


def example_diags(out, err, timed_out, em, d):
    """Turn the EXRUN/EXFAIL/EXDONE lines either backend prints for its examples into diagnostics."""
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


def lean_tools():
    """lean and its bundled leanc (which isn't on PATH; it sits next to the real lean binary)."""
    lean = shutil.which("lean")
    if lean is None:
        return None, None
    return lean, os.path.join(os.path.dirname(os.path.realpath(lean)), "leanc")


def probe_lean(lean, psrc, tmp):
    """Elaborate D28's termination probe and return the `#print axioms` lines, which are all `read_probe` needs.
    They're cached by the probe's text and the Lean install (`~/.cache/clc/probe/`), so rebuilding a program
    whose functions and types haven't changed skips the probe (~1-3 s CPU). A timeout isn't cached: everything
    stays partial for that build."""
    import hashlib
    key = hashlib.sha256((os.path.realpath(lean) + "\0" + psrc).encode()).hexdigest()
    cache = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "clc", "probe")
    path = os.path.join(cache, key + ".txt")
    try:
        with open(path) as fh:
            return fh.read()
    except OSError:
        pass
    pfile = os.path.join(tmp, "Probe.lean")
    with open(pfile, "w") as fh:
        fh.write(psrc)
    try:
        r = subprocess.run([lean, pfile], capture_output=True, text=True, timeout=120, cwd=tmp)
    except subprocess.TimeoutExpired:
        return ""
    found = "".join(ln + "\n" for ln in r.stdout.splitlines() if ln.startswith("'"))
    try:
        os.makedirs(cache, exist_ok=True)
        with open(path + ".tmp", "w") as fh:
            fh.write(found)
        os.replace(path + ".tmp", path)
    except OSError:
        pass  # no cache this time
    return found


def lean_main(args, d, fns, structs):
    """The Lean backend (D26): emit Lean, elaborate it (running the examples), then build with leanc."""
    import cl_lean
    try:
        em = cl_lean.LeanEmitter(fns, structs, args.file)
        lsrc = em.emit()
    except cl_lean.Unsupported as ex:
        print(f"clc: the Lean backend doesn't support {ex} yet", file=sys.stderr)
        return 3
    lean, leanc = lean_tools()
    if lean is None:
        print("clc: the Lean backend needs `lean` on PATH", file=sys.stderr)
        return 2
    tmp = tempfile.mkdtemp(prefix="clc-")
    keep_tmp = False
    try:
        lfile, cfile = os.path.join(tmp, "Main.lean"), os.path.join(tmp, "main.c")
        if em.recursive_fns:
            # D28: which recursive functions can Lean prove stop, and with which measure? One extra elaboration,
            # since trying candidates inside one file would need `import Lean` (40-60 s here).
            psrc = em.emit(probe=True)
            em.read_probe(probe_lean(lean, psrc, tmp))
            lsrc = em.emit()
        with open(lfile, "w") as fh:
            fh.write(lsrc)
        if args.command == "build":
            exe = os.path.abspath(args.output or (args.file[:-3] if args.file.endswith(".cl") else args.file + ".out"))
        else:
            exe = os.path.join(tmp, "prog")
        if args.emit_lean:
            shutil.copy(lfile, exe + ".lean")
        try:
            # `test` needs only elaboration, which runs the examples; the C is for building a binary.
            cmd = [lean, lfile] if args.command == "test" else [lean, "-c", cfile, lfile]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=tmp)
            out, err, code, timed_out = r.stdout, r.stderr, r.returncode, False
        except subprocess.TimeoutExpired as te:
            out = te.stdout.decode() if isinstance(te.stdout, bytes) else (te.stdout or "")
            err, code, timed_out = "", None, True
        lean_errors = [ln for ln in out.splitlines() if ln.startswith(lfile + ":") and ": error" in ln]
        if lean_errors or (code not in (0, 70) and not timed_out):
            keep_tmp = True
            shown = "\n".join(ln for ln in out.splitlines() if not ln.startswith("EX"))
            print(f"clc: internal error: the generated Lean didn't check (this is a compiler bug). "
                  f"Lean kept at {lfile}\n{shown[:4000]}{err[:2000]}", file=sys.stderr)
            return 2
        example_diags(out, err, timed_out, em, d)
        if not d.has_errors() and args.command in ("build", "run"):
            r = None
            if args.command == "run":
                # A throwaway binary links against Lean's shared runtime: ~0.6 s instead of ~4 s for the static
                # link, which pulls in the whole Lean compiler library and garbage-collects it. Same speed once
                # running (+~10 ms start-up). `build` stays static, so its binary works without Lean installed.
                lib = os.path.join(os.path.dirname(leanc), "..", "lib", "lean")
                r = subprocess.run([leanc, cfile, "-O1", "-o", exe, "-nodefaultlibs", "-L" + lib, "-lInit_shared",
                                    "-lleanshared", "-lleanshared_1", "-lleanshared_2", "-Wl,-rpath," + lib, "-lc",
                                    "-lm", "-lpthread", "-ldl"], capture_output=True, text=True)
            if r is None or r.returncode != 0:  # building, or no shared runtime in this Lean: link statically
                r = subprocess.run([leanc, cfile, "-O1", "-o", exe], capture_output=True, text=True)
            if r.returncode != 0:
                keep_tmp = True
                print(f"clc: internal error: leanc failed (this is a compiler bug). C kept at {cfile}\n"
                      f"{r.stderr[:4000]}", file=sys.stderr)
                return 2
        d.report(args.json)
        if d.has_errors():
            return 1
        if args.command == "test" and not args.json:
            print(f"{len(em.examples)} example(s) passed", file=sys.stderr)
        if args.command == "run":
            return subprocess.run([exe]).returncode
        return 0
    finally:
        if not keep_tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="clc", description="compiler for claude-lang")
    ap.add_argument("command", choices=["check", "build", "run", "test"])
    ap.add_argument("file")
    ap.add_argument("-o", "--output", help="binary to write (build only)")
    ap.add_argument("--emit-c", action="store_true", help="also write the generated C as <output>.c")
    ap.add_argument("--json", action="store_true", help="diagnostics as JSON on stderr")
    ap.add_argument("--backend", choices=["lean", "c"], default="lean",
                    help="code generator: Lean 4 (D26, the default) or C (faster to build; Int is 64-bit there)")
    ap.add_argument("--emit-lean", action="store_true", help="also write the generated Lean as <output>.lean")
    args = ap.parse_args(argv)

    try:
        with open(args.file, encoding="utf-8") as fh:
            src = fh.read()
    except OSError as ex:
        print(f"clc: can't read {args.file}: {ex.strerror}", file=sys.stderr)
        return 2
    global INT_LIMIT
    INT_LIMIT = 2**63 - 1 if args.backend == "c" else None
    d, fns, structs = front_end(args.file, src)
    if d.has_errors() or args.command == "check":
        d.report(args.json)
        return 1 if d.has_errors() else 0

    if args.backend == "lean":
        return lean_main(args, d, fns, structs)
    em = Emitter(fns, structs, args.file)
    csrc = em.emit()
    tmp = tempfile.mkdtemp(prefix="clc-")
    keep_tmp = False
    try:
        cfile = os.path.join(tmp, "out.c")
        with open(cfile, "w") as fh:
            fh.write(csrc)
        if args.command == "build":
            exe = os.path.abspath(args.output or (args.file[:-3] if args.file.endswith(".cl") else args.file + ".out"))
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
