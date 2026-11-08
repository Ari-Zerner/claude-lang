# Hidden-input trial 2026-11-08-1204 (cl, haiku)

| task | shown example | ok | wrong | error | verdict | lines | examples |
|---|---|---|---|---|---|---|---|
| balanced | first try | 9 | 0 | 0 | all ok | 55 | 14 |

Totals over hidden inputs: {'ok': 9, 'wrong': 0, 'error': 0}. Programs with a wrong answer: 0 of 1.

## balanced

`fn balanced(tokens: List[String]) -> Bool`

### attempt 1: shown example OK

```cl
fn is_opener(c: String) -> Bool
  example is_opener("(") == true
  example is_opener("]") == false
  return c == "(" or c == "[" or c == "{"
end fn is_opener

fn opener_for(c: String) -> Option[String]
  example opener_for("(") == None
  example opener_for(")") == Some("(")
  example opener_for("]") == Some("[")
  example opener_for("}") == Some("{")
  if c == ")"
    return Some("(")
  end if
  if c == "]"
    return Some("[")
  end if
  if c == "}"
    return Some("{")
  end if
  return None
end fn opener_for

fn balanced(tokens: List[String]) -> Bool
  example balanced(tokens: ["(", "[", "]", ")"]) == true
  example balanced(tokens: []) == true
  example balanced(tokens: ["{", "}", "{", "}"]) == true
  example balanced(tokens: ["(", "]"]) == false
  example balanced(tokens: ["("]) == false
  example balanced(tokens: [")"]) == false
  example balanced(tokens: ["(", "[", ")", "]"]) == false
  example balanced(tokens: ["(", ")", ")"]) == false
  var stack: List[String] = []
  for t in tokens
    if is_opener(t)
      stack = append(list: stack, item: t)
    else
      match opener_for(t)
        case Some(want)
          if length(stack) == 0
            return false
          end if
          if stack[length(stack) - 1] != want
            return false
          end if
          var rest: List[String] = []
          for i in 0 until length(stack) - 1
            rest = append(list: rest, item: stack[i])
          end for
          stack = rest
        case None
          return false
      end match
    end if
  end for
  return length(stack) == 0
end fn balanced
```

Hidden inputs: 9 ok, 0 wrong, 0 error
