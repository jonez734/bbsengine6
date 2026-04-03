#!/usr/bin/env python3
"""
convert_markdown.py
Convert markdown files to HTML with clean, consistent styling
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional

try:
    import markdown
    from markdown.extensions import toc, tables, fenced_code, codehilite
except ImportError:
    print("Error: markdown package not installed")
    print("Install with: pip install markdown markdown-extensions pygments")
    sys.exit(1)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        h1, h2, h3, h4, h5, h6 {{
            margin-top: 24px;
            margin-bottom: 16px;
            font-weight: 600;
            line-height: 1.25;
        }}

        h1 {{
            font-size: 2em;
            border-bottom: 2px solid #eee;
            padding-bottom: 0.3em;
        }}

        h2 {{
            font-size: 1.5em;
            border-bottom: 1px solid #eee;
            padding-bottom: 0.3em;
        }}

        h3 {{ font-size: 1.25em; }}
        h4 {{ font-size: 1.1em; }}
        h5 {{ font-size: 1em; }}
        h6 {{ font-size: 0.9em; color: #666; }}

        p {{
            margin-bottom: 16px;
        }}

        a {{
            color: #0366d6;
            text-decoration: none;
        }}

        a:hover {{
            text-decoration: underline;
        }}

        code {{
            background: #f6f8fa;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
            font-size: 0.85em;
        }}

        pre {{
            background: #f6f8fa;
            border: 1px solid #e1e4e8;
            border-radius: 6px;
            padding: 16px;
            overflow-x: auto;
            margin-bottom: 16px;
        }}

        pre code {{
            background: none;
            padding: 0;
            border-radius: 0;
            font-size: 0.9em;
            color: #24292e;
        }}

        blockquote {{
            border-left: 4px solid #ddd;
            padding-left: 16px;
            margin: 16px 0;
            color: #666;
        }}

        ul, ol {{
            margin-left: 32px;
            margin-bottom: 16px;
        }}

        li {{
            margin-bottom: 8px;
        }}

        table {{
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 16px;
        }}

        table th {{
            background: #f6f8fa;
            padding: 8px 12px;
            border: 1px solid #e1e4e8;
            text-align: left;
            font-weight: 600;
        }}

        table td {{
            padding: 8px 12px;
            border: 1px solid #e1e4e8;
        }}

        table tr:nth-child(even) {{
            background: #f6f8fa;
        }}

        img {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
        }}

        .toc {{
            background: #f6f8fa;
            padding: 16px;
            border-radius: 6px;
            margin-bottom: 24px;
        }}

        .toc ul {{
            margin-left: 16px;
        }}

        .toc a {{
            color: #0366d6;
        }}

        .metadata {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid #eee;
        }}

        .nav {{
            margin-top: 40px;
            padding-top: 16px;
            border-top: 1px solid #eee;
            font-size: 0.9em;
        }}

        .nav a {{
            margin-right: 16px;
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 20px;
            }}

            h1 {{ font-size: 1.5em; }}
            h2 {{ font-size: 1.2em; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        {content}
        <div class="nav">
            <a href="/handbook/">← Back to Handbook</a>
        </div>
    </div>
</body>
</html>
"""


def get_markdown_title(file_path: Path) -> str:
    """Extract title from markdown file (first H1 heading or filename)."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("# "):
                    return line[2:].strip()
    except Exception:
        pass

    return file_path.stem.replace("_", " ").replace("-", " ").title()


def convert_md_to_html(md_file: Path, output_dir: Optional[Path] = None) -> bool:
    """Convert a single markdown file to HTML."""
    if not md_file.exists():
        print(f"Error: File not found: {md_file}")
        return False

    if output_dir is None:
        output_dir = md_file.parent

    output_dir.mkdir(parents=True, exist_ok=True)

    html_file = output_dir / md_file.stem / "index.html"
    html_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(md_file, "r", encoding="utf-8") as f:
            md_content = f.read()

        # Configure markdown extensions
        extensions = [
            "toc",
            "tables",
            "fenced_code",
            "codehilite",
            "extra",
        ]

        md = markdown.Markdown(extensions=extensions)
        html_content = md.convert(md_content)

        title = get_markdown_title(md_file)
        final_html = HTML_TEMPLATE.format(title=title, content=html_content)

        with open(html_file, "w", encoding="utf-8") as f:
            f.write(final_html)

        print(f"✓ Converted: {md_file} → {html_file}")
        return True

    except Exception as e:
        print(f"✗ Error converting {md_file}: {e}")
        return False


def convert_directory(directory: Path, recursive: bool = True) -> int:
    """Convert all markdown files in a directory."""
    if not directory.exists():
        print(f"Error: Directory not found: {directory}")
        return 1

    md_files = []
    pattern = "**/*.md" if recursive else "*.md"

    for md_file in directory.glob(pattern):
        # Skip backup files and node_modules
        if any(part.startswith(".") for part in md_file.parts):
            continue
        if "node_modules" in md_file.parts:
            continue
        md_files.append(md_file)

    if not md_files:
        print(f"No markdown files found in {directory}")
        return 1

    print(f"Converting {len(md_files)} markdown files...")
    converted = sum(1 for f in md_files if convert_md_to_html(f))

    print(f"\nCompleted: {converted}/{len(md_files)} files converted")
    return 0 if converted == len(md_files) else 1


def main():
    parser = argparse.ArgumentParser(
        description="Convert markdown files to HTML with clean styling"
    )
    parser.add_argument(
        "path",
        help="Path to markdown file or directory",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output directory (defaults to input directory)",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        default=True,
        help="Convert recursively (default: True)",
    )

    args = parser.parse_args()
    path = Path(args.path)

    if path.is_file():
        success = convert_md_to_html(path, args.output)
        return 0 if success else 1
    elif path.is_dir():
        return convert_directory(path, recursive=args.recursive)
    else:
        print(f"Error: {path} is not a file or directory")
        return 1


if __name__ == "__main__":
    sys.exit(main())
