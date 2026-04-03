#!/usr/bin/env python3
"""
app.py
Flask application for serving markdown documentation with runtime conversion
Serves .md files as styled HTML without pre-conversion
"""

import os
import mimetypes
from pathlib import Path
from functools import lru_cache

from flask import Flask, render_template_string, abort, redirect, url_for
from markupsafe import escape

try:
    import markdown
    from markdown.extensions import toc, tables, fenced_code, codehilite, extra
except ImportError:
    print("Error: markdown package not installed")
    print("Install with: pip install markdown pygments")
    exit(1)

# Configuration
HANDBOOK_DIR = Path(__file__).parent
MAX_CACHE_SIZE = 128

# HTML template for rendering
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - BBSEngine Documentation</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .breadcrumb {
            font-size: 0.9em;
            margin-bottom: 24px;
            color: #666;
        }

        .breadcrumb a {
            color: #0366d6;
            text-decoration: none;
        }

        .breadcrumb a:hover {
            text-decoration: underline;
        }

        .breadcrumb span {
            margin: 0 8px;
        }

        h1, h2, h3, h4, h5, h6 {
            margin-top: 24px;
            margin-bottom: 16px;
            font-weight: 600;
            line-height: 1.25;
        }

        h1 {
            font-size: 2em;
            border-bottom: 2px solid #eee;
            padding-bottom: 0.3em;
            margin-top: 0;
        }

        h2 {
            font-size: 1.5em;
            border-bottom: 1px solid #eee;
            padding-bottom: 0.3em;
        }

        h3 { font-size: 1.25em; }
        h4 { font-size: 1.1em; }
        h5 { font-size: 1em; }
        h6 { font-size: 0.9em; color: #666; }

        p {
            margin-bottom: 16px;
        }

        a {
            color: #0366d6;
            text-decoration: none;
        }

        a:hover {
            text-decoration: underline;
        }

        code {
            background: #f6f8fa;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
            font-size: 0.85em;
        }

        pre {
            background: #f6f8fa;
            border: 1px solid #e1e4e8;
            border-radius: 6px;
            padding: 16px;
            overflow-x: auto;
            margin-bottom: 16px;
        }

        pre code {
            background: none;
            padding: 0;
            border-radius: 0;
            font-size: 0.9em;
            color: #24292e;
        }

        blockquote {
            border-left: 4px solid #ddd;
            padding-left: 16px;
            margin: 16px 0;
            color: #666;
        }

        ul, ol {
            margin-left: 32px;
            margin-bottom: 16px;
        }

        li {
            margin-bottom: 8px;
        }

        table {
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 16px;
        }

        table th {
            background: #f6f8fa;
            padding: 8px 12px;
            border: 1px solid #e1e4e8;
            text-align: left;
            font-weight: 600;
        }

        table td {
            padding: 8px 12px;
            border: 1px solid #e1e4e8;
        }

        table tr:nth-child(even) {
            background: #f6f8fa;
        }

        img {
            max-width: 100%;
            height: auto;
            border-radius: 4px;
        }

        .toc {
            background: #f6f8fa;
            padding: 16px;
            border-radius: 6px;
            margin-bottom: 24px;
        }

        .toc ul {
            margin-left: 16px;
        }

        .toc a {
            color: #0366d6;
        }

        .toc-title {
            font-weight: 600;
            margin-bottom: 12px;
        }

        .nav {
            margin-top: 40px;
            padding-top: 16px;
            border-top: 1px solid #eee;
            font-size: 0.9em;
        }

        .nav a {
            margin-right: 16px;
            display: inline-block;
        }

        .last-modified {
            font-size: 0.85em;
            color: #999;
            margin-top: 8px;
        }

        .directory-index {
            margin: 24px 0;
        }

        .directory-index h2 {
            border-bottom: 1px solid #eee;
            padding-bottom: 8px;
        }

        .file-list {
            list-style: none;
            margin-left: 0;
        }

        .file-list li {
            padding: 8px;
            margin: 4px 0;
            background: #f6f8fa;
            border-radius: 4px;
        }

        .file-list a {
            color: #0366d6;
        }

        .file-icon {
            margin-right: 8px;
        }

        @media (max-width: 768px) {
            .container {
                padding: 20px;
            }

            h1 { font-size: 1.5em; }
            h2 { font-size: 1.2em; }

            .breadcrumb {
                font-size: 0.8em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        {{ breadcrumb_html | safe }}
        {{ content | safe }}
        <div class="nav">
            <a href="/handbook/">← Back to Handbook</a>
        </div>
    </div>
</body>
</html>
"""

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False


def get_markdown_extensions():
    """Get configured markdown extensions."""
    return [
        'toc',
        'tables',
        'fenced_code',
        'codehilite',
        'extra',
    ]


@lru_cache(maxsize=MAX_CACHE_SIZE)
def convert_markdown(content: str) -> str:
    """Convert markdown content to HTML with caching."""
    md = markdown.Markdown(extensions=get_markdown_extensions())
    return md.convert(content)


def get_markdown_title(content: str) -> str:
    """Extract title from markdown content (first H1 heading)."""
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('# '):
            return line[2:].strip()
    return 'Documentation'


def get_breadcrumb(path: str) -> tuple:
    """Generate breadcrumb navigation."""
    parts = [p for p in path.split('/') if p]
    breadcrumb = [('Handbook', '/handbook/')]

    current_path = '/handbook'
    for part in parts[:-1]:
        current_path += f'/{part}'
        breadcrumb.append((part.replace('-', ' ').title(), current_path + '/'))

    if parts and parts[-1]:
        breadcrumb.append((parts[-1].replace('-', ' ').replace('.md', '').title(), None))

    return breadcrumb


def render_breadcrumb(breadcrumb: list) -> str:
    """Render breadcrumb HTML."""
    html_parts = []
    for i, (label, url) in enumerate(breadcrumb):
        if url:
            html_parts.append(f'<a href="{url}">{escape(label)}</a>')
        else:
            html_parts.append(escape(label))

        if i < len(breadcrumb) - 1:
            html_parts.append('<span>/</span>')

    return f'<div class="breadcrumb">{"".join(html_parts)}</div>'


def list_directory(directory: Path) -> str:
    """Generate HTML listing for a directory."""
    try:
        items = sorted(directory.iterdir())
    except PermissionError:
        return '<p>Permission denied</p>'

    html = '<div class="directory-index"><h2>Contents</h2><ul class="file-list">'

    # Parent directory link
    if directory != HANDBOOK_DIR:
        parent = directory.parent.relative_to(HANDBOOK_DIR)
        parent_url = f'/handbook/{parent}/' if str(parent) != '.' else '/handbook/'
        html += f'<li><span class="file-icon">📁</span><a href="{parent_url}">..</a></li>'

    # List items
    for item in items:
        # Skip hidden files and backups
        if item.name.startswith('.') or item.name.endswith(('~', '.bak', '.swp')):
            continue

        relative = item.relative_to(HANDBOOK_DIR)
        item_url = f'/handbook/{relative}/'

        if item.is_dir():
            icon = '📁'
            label = item.name
        elif item.suffix == '.md':
            icon = '📄'
            label = item.stem
        else:
            icon = '📎'
            label = item.name

        html += f'<li><span class="file-icon">{icon}</span><a href="{item_url}">{escape(label)}</a></li>'

    html += '</ul></div>'
    return html


@app.route('/handbook/')
def index():
    """Serve handbook index."""
    return serve_markdown('index.md')


@app.route('/handbook/<path:path>')
def serve_file(path: str):
    """
    Serve markdown or other files from handbook directory.
    Handles both /path/to/file and /path/to/file.md
    """
    # Remove trailing slash
    path = path.rstrip('/')

    # Try to find the file
    file_path = HANDBOOK_DIR / path

    # Check for markdown file without extension
    if not file_path.exists() and not file_path.suffix:
        markdown_path = HANDBOOK_DIR / f'{path}.md'
        if markdown_path.exists():
            return serve_markdown(f'{path}.md')

    # Check if it's a directory
    if file_path.is_dir():
        # Try index.md in directory
        index_path = file_path / 'index.md'
        if index_path.exists():
            return serve_markdown(str(index_path.relative_to(HANDBOOK_DIR)))

        # Generate directory listing
        breadcrumb = get_breadcrumb(path)
        breadcrumb_html = render_breadcrumb(breadcrumb)
        content = list_directory(file_path)
        title = path.split('/')[-1].replace('-', ' ').title() or 'Handbook'

        return render_template_string(
            HTML_TEMPLATE,
            title=title,
            breadcrumb_html=breadcrumb_html,
            content=content,
        )

    # Serve markdown file
    if file_path.suffix == '.md':
        return serve_markdown(path)

    # Serve other files (CSS, images, etc.)
    if file_path.exists() and file_path.is_file():
        with open(file_path, 'rb') as f:
            mime_type, _ = mimetypes.guess_type(str(file_path))
            response = app.make_response(f.read())
            if mime_type:
                response.headers['Content-Type'] = mime_type
            return response

    abort(404)


def serve_markdown(file_path: str) -> str:
    """Serve a markdown file converted to HTML."""
    full_path = HANDBOOK_DIR / file_path

    if not full_path.exists():
        abort(404)

    if not full_path.is_file():
        abort(404)

    if not str(full_path.relative_to(HANDBOOK_DIR)).startswith('..'):
        abort(403)  # Directory traversal attempt

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        abort(500)

    # Convert markdown to HTML
    html_content = convert_markdown(content)
    title = get_markdown_title(content)
    breadcrumb = get_breadcrumb(str(full_path.relative_to(HANDBOOK_DIR)))
    breadcrumb_html = render_breadcrumb(breadcrumb)

    return render_template_string(
        HTML_TEMPLATE,
        title=title,
        breadcrumb_html=breadcrumb_html,
        content=html_content,
    )


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Not Found - BBSEngine Documentation</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                padding: 40px;
                color: #333;
            }
            .container {
                max-width: 600px;
                margin: 0 auto;
            }
            h1 { color: #d32f2f; }
            a { color: #0366d6; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>404 - Not Found</h1>
            <p>The documentation page you requested could not be found.</p>
            <p><a href="/handbook/">← Back to Handbook</a></p>
        </div>
    </body>
    </html>
    """), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Server Error - BBSEngine Documentation</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                padding: 40px;
                color: #333;
            }
            .container {
                max-width: 600px;
                margin: 0 auto;
            }
            h1 { color: #d32f2f; }
            a { color: #0366d6; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>500 - Server Error</h1>
            <p>An error occurred while processing your request.</p>
            <p><a href="/handbook/">← Back to Handbook</a></p>
        </div>
    </body>
    </html>
    """), 500


if __name__ == '__main__':
    # Development server (not for production!)
    print("Development server running on http://localhost:5000/handbook/")
    app.run(debug=True, host='localhost', port=5000)
