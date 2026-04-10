# md2tpl.py
# Converts markdown files with frontmatter to Smarty .tmpl files

import argparse
import re
import sys
from pathlib import Path

import markdown


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and body from markdown content."""
    frontmatter = {}
    body = content

    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1)
        body = content[fm_match.end() :]

        for line in fm_text.split("\n"):
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()

                if key == "sigs" and "," in value:
                    frontmatter[key] = [v.strip() for v in value.split(",")]
                else:
                    frontmatter[key] = value

    return frontmatter, body


def convert_to_smarty(
    md_content: str,
    input_path: Path,
    output_path: Path,
    parent_template: str = "blurb.tmpl",
) -> str:
    """Convert markdown to Smarty template."""
    frontmatter, body = parse_frontmatter(md_content)

    md = markdown.Markdown(extensions=["extra", "codehilite"])
    html_body = md.convert(body)

    frontmatter_lines = []
    for key, value in frontmatter.items():
        safe_key = key.replace("-", "_")

        if key == "sigs" and isinstance(value, list):
            sigpath_str = ",".join(value)
            frontmatter_lines.append(
                f'{{assign var="meta.sigs" value="{sigpath_str}"}}'
            )
        else:
            frontmatter_lines.append(
                f'{{if isset($meta.{safe_key})}}{{assign var="meta.{safe_key}" value=$meta.{safe_key}}}{{/if}}'
            )

    frontmatter_assign = "\n".join(frontmatter_lines) if frontmatter_lines else ""

    header_value = f'{{$meta.header|default:"{input_path.stem}"}}'

    tmpl = f'''{{***
 * Generated from {input_path.name}
 * DO NOT EDIT DIRECTLY - Edit source file instead
 **}}
{frontmatter_assign}
{{extends file="{parent_template}"}}
{{block name="header"}}{header_value}{{/block}}
{{block name="content"}}
{html_body}
{{/block}}
'''
    return tmpl


def main():
    parser = argparse.ArgumentParser(description="Convert markdown to Smarty templates")
    parser.add_argument("input", type=Path, help="Input markdown file")
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        help="Output template file (default: same name with .tmpl)",
    )
    parser.add_argument(
        "--parent", default="blurb.tmpl", help="Parent template to extend"
    )
    args = parser.parse_args()

    input_path = args.input
    if not input_path.exists():
        print(f"Error: Input file '{input_path}' not found", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = args.output
    else:
        output_path = input_path.with_suffix(".tmpl")

    md_content = input_path.read_text(encoding="utf-8")
    tmpl_content = convert_to_smarty(md_content, input_path, output_path, args.parent)

    output_path.write_text(tmpl_content, encoding="utf-8")
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()
