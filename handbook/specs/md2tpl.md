# bbsengine6.md2tpl Specification

## Summary

`md2tpl.py` is a build-time tool that converts markdown files with YAML frontmatter into Smarty `.tmpl` templates for use in the BBS engine web interface.

## Brief Description

A Python CLI tool that parses markdown files, extracts frontmatter metadata, converts the markdown body to HTML, and outputs Smarty templates that extend `blurb.tmpl`. Designed to mirror the SASS workflow: write content in markdown, build to Smarty templates.

## Use Case

Content authors write documentation in markdown (e.g., handbook pages) with frontmatter for metadata. At build time, `md2tpl` converts these to Smarty templates that can be rendered by the BBS engine's web PHP pages.

## Public API

```python
# Command line
python3 -m bbsengine6.md2tpl <input.md> [output.tmpl] [--parent blurb.tmpl]

# Programmatic
from bbsengine6.md2tpl import convert_to_smarty, parse_frontmatter

parse_frontmatter(content: str) -> tuple[dict, str]
convert_to_smarty(md_content: str, input_path: Path, output_path: Path, parent_template: str = "blurb.tmpl") -> str
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `input` | Input markdown file (required) | - |
| `output` | Output template file | `<input>.tmpl` |
| `--parent` | Parent template to extend | `blurb.tmpl` |

## Input Format

### Markdown with Frontmatter

```markdown
---
title: Page Title
description: A brief description
author: John
date: 2026-04-08
---
# Heading

Content here with **bold** and [links](http://example.com).
```

### Markdown without Frontmatter

```markdown
# Heading

Content here...
```

## Output Format

### With Frontmatter

```smarty
{***
 * Generated from page.md
 * DO NOT EDIT DIRECTLY - Edit source file instead
 **}
{if isset($meta.title)}{assign var="meta.title" value=$meta.title}{/if}
{if isset($meta.description)}{assign var="meta.description" value=$meta.description}{/if}
{if isset($meta.author)}{assign var="meta.author" value=$meta.author}{/if}
{if isset($meta.date)}{assign var="meta.date" value=$meta.date}{/if}
{extends file="blurb.tmpl"}
{block name="title"}{$meta.title}{/block}
{block name="content"}
<h1>Heading</h1>
<p>Content here with <strong>bold</strong> and <a href="http://example.com">links</a>.</p>
{/block}
{block name="description"}{$meta.description|default:''}{/block}
```

### Without Frontmatter

```smarty
{***
 * Generated from page.md
 * DO NOT EDIT DIRECTLY - Edit source file instead
 **}
{extends file="blurb.tmpl"}
{block name="title"}{$meta.title|default:"page"}{/block}
{block name="content"}
<h1>Heading</h1>
<p>Content here...</p>
{/block}
{block name="description"}{$meta.description|default:''}{/block}
```

## Frontmatter to Smarty Variable Mapping

| Frontmatter Key | Smarty Variable |
|-----------------|-----------------|
| `title` | `$meta.title` |
| `description` | `$meta.description` |
| `author` | `$meta.author` |
| `date` | `$meta.date` |
| `sigs` | `$meta.sigs` (comma-separated sig paths for cross-posting) |
| `layout` | (reserved for future use) |
| `foo-bar` | `$meta.foo_bar` (hyphens converted to underscores) |

## Parent Template: blurb.tmpl

The generated templates extend `blurb.tmpl`, which provides the following structure:

```smarty
<div class="blurb">
  <div class="header">
    <h1>{$meta.title}</h1>
  </div>
  <div class="body">
    {block name="content"}{$content}{/block}
  </div>
  <div class="metadata">
    {if isset($meta.date)}<span class="date">{$meta.date}</span>{/if}
    {if isset($meta.author)}<span class="author">{$meta.author}</span>{/if}
  </div>
  <div class="footer">
    {block name="footer"}{/block}
  </div>
</div>
```

## Markdown Processing

- **Extensions enabled**: `extra`, `codehilite`
- **Output**: XHTML 5 compliant
- **Frontmatter**: Extracted using regex, parsed as simple `key: value` YAML-like pairs

## Thread Safety

- **Safe**: Pure function with no shared state. Can be called from multiple threads.
- Each invocation creates a new `Markdown` instance.

## Dependencies

- `markdown` (PyPI) -- Markdown parsing
- Standard library: `argparse`, `re`, `sys`, `pathlib`

## Makefile Integration

The handbook directory includes a `convert-tmpl` target:

```makefile
convert-tmpl:
	find . -name "*.md" -not -name "*.md~" | while read f; do \
		PYTHONPATH=/home/opencode/data/work/bbsengine6/py/src python3 -m bbsengine6.md2tpl "$$f"; \
	done
```

## File Location

- Tool: `bbsengine6/py/src/bbsengine6/md2tpl.py`
- Parent template: `bbsengine6/skin/tmpl/blurb.tmpl`
- Dependency declared in: `bbsengine6/py/src/pyproject.toml`

## Known Issues / TODOs

1. Frontmatter parsing is simplistic (regex-based, not full YAML parser). Complex YAML (lists, nested objects) will not parse correctly.
2. No support for `layout` frontmatter to override parent template.
3. No watch mode for auto-rebuild on file changes.
4. No handling of Smarty variable syntax (`{$foo}`) in source markdown -- could cause conflicts.
5. Image/link paths are not rewritten; relative paths remain as-is.