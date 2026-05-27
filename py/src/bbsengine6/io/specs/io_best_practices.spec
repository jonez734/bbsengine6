# asimov.io Best Practices

## Echo Commands in F-strings

When using echo commands (like `{f6}`, `{bell}`, `{curpos:1,1}`) inside f-strings, you must escape the curly braces:

```python
# Correct - f-string with echo command
echo(f"{{f6}}Some text")

# Incorrect - will cause "f6 is not defined" error
echo(f"{f6}Some text")
```

**Rule:** If you see an error like `"f6" is not defined`, check if the code is inside an f-string and escape the braces with double `{{` and `}}`.

### Common Echo Commands to Escape

| Command | F-string写法 |
|---------|-------------|
| `{f6}` | `{{f6}}` |
| `{bell}` | `{{bell}}` |
| `{curpos:1,1}` | `{{curpos:1,1}}` |
| `{yellow}` | `{{yellow}}` |

## Completer Class

When subclassing `Completer`, override the `get_matches` method:

```python
class MyCompleter(Completer):
    def get_matches(self, prefix, **kwargs):
        # Your logic here
        return ["match1", "match2"]
```

Pass to inputstring:
```python
inputstring("Prompt: ", completer=MyCompleter())
```

Or pass a function:
```python
def my_func(prefix, **kwargs):
    return ["match1", "match2"]

inputstring("Prompt: ", completer=Completer(my_func))
```

## Passing args to Input Functions

When using `inputchoice`, `inputboolean`, `inputstring`, or other input functions in a module, you must pass `args` (and optionally `pool`) to enable notification checking:

```python
# Correct - pass args to enable notifications
ch = io.inputchoice("Select:", "ABC", args=args, **kwargs)
result = io.inputboolean("Continue?", "Y", args=args)
text = io.inputstring("Name: ", args=args)

# Incorrect - will cause errors when notifications are checked
ch = io.inputchoice("Select:", "ABC")
```

The `args` parameter provides the database connection info needed for `notify.count()` to check for pending notifications. If you have a pool already, you can pass `pool` instead of (or in addition to) `args`.

### Pattern for Module Functions

When wrapping input functions in your own module:

```python
def my_module_main(args, **kwargs):
    # Pass args to input functions so notifications work
    ch = io.inputchoice("Select:", "ABC", args=args, **kwargs)
    
    # If you call submodules, pass kwargs through
    result = other_module.some_function(args, **kwargs)
```
