#!/usr/bin/env python
"""
Demo script showing TUI template system features.

Usage:
    python demo_template.py

This demo showcases:
- Loading built-in templates
- Variable substitution
- Site template override
- echo_template() convenience function
"""

import sys
import os
import tempfile

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from bbsengine6 import io


def demo_builtin_templates():
    """Show built-in templates."""
    print("\n" + "=" * 60)
    print("DEMO: Built-in Templates")
    print("=" * 60)

    templates = ["menu.tpl", "form.tpl", "confirm.tpl", "list.tpl", "header.tpl"]

    for tpl in templates:
        content = io.load_template(tpl)
        print(f"\n--- {tpl} ---")
        # Show first few lines
        lines = content.split("\n")[:3]
        for line in lines:
            print(f"  {line}")
        if len(content.split("\n")) > 3:
            print("  ...")


def demo_variable_substitution():
    """Show variable substitution."""
    print("\n" + "=" * 60)
    print("DEMO: Variable Substitution")
    print("=" * 60)

    # Simple substitution - use io.echo() to process {var:xxx} commands
    result = io.load_template("menu.tpl", title="Main Menu", item1="Files", item2="Mail")
    print("\n--- menu.tpl with variables (via io.echo()) ---")
    io.echo(result)

    # Form template
    result = io.load_template("form.tpl", title="User Profile", label="Username", value="alice")
    print("\n--- form.tpl with variables (via io.echo()) ---")
    io.echo(result)

    # Confirm template
    result = io.load_template("confirm.tpl", title="Delete", message="Delete this file?")
    print("\n--- confirm.tpl with variables (via io.echo()) ---")
    io.echo(result)


def demo_echo_template():
    """Show echo_template() convenience function."""
    print("\n" + "=" * 60)
    print("DEMO: echo_template() Function")
    print("=" * 60)
    print("\n--- Using echo_template() directly outputs to terminal ---\n")

    # This will render and output to terminal
    io.echo_template("header.tpl", title="Welcome")

    print()
    io.echo_template("list.tpl", title="Your Files", item="document.pdf")

    print()
    io.echo_template("menu.tpl", title="Main Menu", item1="Read Mail", item2="Write Mail")


def demo_site_template_override():
    """Show site template override."""
    print("\n" + "=" * 60)
    print("DEMO: Site Template Override")
    print("=" * 60)

    # Create a temporary site template
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create custom menu.tpl
        custom_menu = os.path.join(tmpdir, "menu.tpl")
        with open(custom_menu, "w") as f:
            f.write("""CUSTOM SITE TEMPLATE
==================
Title: {title}
Option 1: {item1}
Option 2: {item2}
[X] Exit
""")

        # Set site template directory
        io.setvar("template_dir", tmpdir)

        print(f"\n--- Using custom template from {tmpdir} ---")
        result = io.load_template("menu.tpl", title="Custom Title", item1="Option A", item2="Option B")
        print(result)

        # Clean up
        io.setvar("template_dir", None)


def demo_preserves_runtime_vars():
    """Show that runtime variables are preserved."""
    print("\n" + "=" * 60)
    print("DEMO: Runtime Variables Preserved")
    print("=" * 60)

    print("\n--- Template raw (before io.echo processes {var:xxx}) ---")
    result = io.load_template("menu.tpl", title="Test")
    print(result[:80] + "...")

    print("\n--- Template after io.echo() processes {var:xxx} commands ---")
    io.echo(result)


def main():
    print("=" * 60)
    print("BBSENGINE6 TUI TEMPLATE SYSTEM DEMO")
    print("=" * 60)

    demo_builtin_templates()
    demo_variable_substitution()
    demo_echo_template()
    demo_site_template_override()
    demo_preserves_runtime_vars()

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("""
API Summary:
-----------
io.load_template(name, **vars)  -> str
    Load template and substitute {varname} placeholders

io.echo_template(name, **vars)  -> None
    Load, substitute, and output to terminal

io.setvar("template_dir", path)  -> None
    Set site-specific template directory (overrides built-in)

Templates are searched in order:
1. Site-specific template_dir (if set)
2. Built-in bbsengine6/tpl/ directory
""")


if __name__ == "__main__":
    main()