# Best Practices

## io.echo() Must Use f-strings

All `io.echo()` calls **MUST use f-strings** to support echo commands like `{restorecursor}`, `{savecursor}`, `{promptcolor}`, `{valuecolor}`, etc.

```python
# Correct - f-string allows io.echo() to interpret escape sequences:
io.echo(f"{{restorecursor}}{{promptcolor}}{prompt}{{valuecolor}}{result}")

# Wrong - regular string won't process escape sequences:
io.echo("{restorecursor}{promptcolor}...") # BUG: escape sequences not processed
```

The linter rule F541 (f-string without placeholders) is disabled because io.echo commands like `{savecursor}` require f-string syntax to be processed.

## f-string Variable Escaping

When using f-strings with `io.echo()`, remember:
- **Double braces** `{{colorname}}` for io.echo escape sequences
- **Single braces** `{variablename}` for Python variables

```python
# Correct:
io.echo(f"{{labelcolor}}Item: {{valuecolor}}{item.content}{{/all}}\n")

# Wrong (will cause errors or unexpected output):
io.echo(f"{{labelcolor}}Item: {{valuecolor}}{{item.content}}{{/all}}\n")
```

This ensures io.echo receives the escape sequences while Python interpolates the variables.
