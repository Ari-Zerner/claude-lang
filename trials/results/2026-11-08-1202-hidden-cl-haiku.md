# Hidden-input trial 2026-11-08-1202 (cl, haiku)

| task | shown example | ok | wrong | error | verdict | lines | examples |
|---|---|---|---|---|---|---|---|
| balanced | after fix | 9 | 0 | 0 | all ok | 43 | 12 |

Totals over hidden inputs: {'ok': 9, 'wrong': 0, 'error': 0}. Programs with a wrong answer: 0 of 1.

## balanced

`fn balanced(tokens: List[String]) -> Bool`

### attempt 1: build-fail

```cl
fn is_opener(c: String) -> Bool
  example is_opener(c: "(") == true
  example is_opener(c: "]") == false
  return c == "(" or c == "[" or c == "{"
end fn is_opener

fn matching_opener(c: String) -> String
  example matching_opener(c: ")") == "("
  example matching_opener(c: "]") == "["
  example matching_opener(c: "}") == "{"
  if c == ")"
    return "("
  else if c == "]"
    return "["
  else
    return "{"
  end if
end fn matching_opener

fn balanced(tokens: List[String]) -> Bool
  example balanced(tokens: ["(", "[", "]", ")"]) == true
  example balanced(tokens: []) == true
  example balanced(tokens: ["("]) == false
  example balanced(tokens: ["(", "]"]) == false
  example balanced(tokens: ["(", ")", "}"]) == false
  example balanced(tokens: ["{", "(", "}", ")"]) == false
  example balanced(tokens: ["[", "]", "{", "}"]) == true
  var stack = repeat(item: "", times: length(tokens))
  var top = 0
  for t in tokens
    if is_opener(c: t)
      stack[top] = t
      top = top + 1
    else
      if top == 0
        return false
      end if
      top = top - 1
      if stack[top] != matching_opener(c: t)
        return false
      end if
    end if
  end for
  return top == 0
end fn balanced
```

Diagnostics sent back:
```
prog.cl:4:40: error[unclosed-interpolation]: `{` starts an interpolation, but there's no `}`
    4 |   return c == "(" or c == "[" or c == "{"
      |                                        ^
  fix: write `\{` for a literal brace: `"\{"`
prog.cl:10:39: error[unclosed-interpolation]: `{` starts an interpolation, but there's no `}`
   10 |   example matching_opener(c: "}") == "{"
      |                                       ^
  fix: write `\{` for a literal brace: `"\{"`
prog.cl:16:13: error[unclosed-interpolation]: `{` starts an interpolation, but there's no `}`
   16 |     return "{"
      |             ^
  fix: write `\{` for a literal brace: `"\{"`
prog.cl:26:30: error[unclosed-interpolation]: `{` starts an interpolation, but the string ends right after it
   26 |   example balanced(tokens: ["{", "(", "}", ")"]) == false
      |                              ^
  fix: write `\{` for a literal brace: `"\{"`
prog.cl:27:40: error[unclosed-interpolation]: `{` starts an interpolation, but the string ends right after it
   27 |   example balanced(tokens: ["[", "]", "{", "}"]) == true
      |                                        ^
  fix: write `\{` for a literal brace: `"\{"`
5 error(s), 0 warning(s)
```

### attempt 2: shown example OK

```cl
fn is_opener(c: String) -> Bool
  example is_opener(c: "(") == true
  example is_opener(c: "]") == false
  return c == "(" or c == "[" or c == "\{"
end fn is_opener

fn matching_opener(c: String) -> String
  example matching_opener(c: ")") == "("
  example matching_opener(c: "]") == "["
  example matching_opener(c: "\}") == "\{"
  if c == ")"
    return "("
  else if c == "]"
    return "["
  else
    return "\{"
  end if
end fn matching_opener

fn balanced(tokens: List[String]) -> Bool
  example balanced(tokens: ["(", "[", "]", ")"]) == true
  example balanced(tokens: []) == true
  example balanced(tokens: ["("]) == false
  example balanced(tokens: ["(", "]"]) == false
  example balanced(tokens: ["(", ")", "\}"]) == false
  example balanced(tokens: ["\{", "(", "\}", ")"]) == false
  example balanced(tokens: ["[", "]", "\{", "\}"]) == true
  var stack = repeat(item: "", times: length(tokens))
  var top = 0
  for t in tokens
    if is_opener(c: t)
      stack[top] = t
      top = top + 1
    else
      if top == 0
        return false
      end if
      top = top - 1
      if stack[top] != matching_opener(c: t)
        return false
      end if
    end if
  end for
  return top == 0
end fn balanced
```

Hidden inputs: 9 ok, 0 wrong, 0 error
