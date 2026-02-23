# Best Practices

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
