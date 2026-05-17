"""
Test suite for TUI template system in io/echo.py.
"""

import os
import sys
import pytest
import tempfile

# Import from io to trigger loading of echo submodule, then get the module
import bbsengine6.io  # noqa: F401

echo_module = sys.modules["bbsengine6.io.echo"]


pytestmark = pytest.mark.unit


class TestGetTemplateDirs:
    """Test _get_template_dirs() function."""

    def test_returns_list(self):
        """Returns a list."""
        result = echo_module._get_template_dirs()
        assert isinstance(result, list)

    def test_builtin_tpl_dir_included(self):
        """Built-in tpl directory is included."""
        result = echo_module._get_template_dirs()
        # Verify there's a tpl directory that exists
        assert any(os.path.isdir(d) and d.endswith("tpl") for d in result)

    def test_site_template_dir_when_set(self):
        """Site template_dir is included when set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            echo_module.setvar("template_dir", tmpdir)
            try:
                result = echo_module._get_template_dirs()
                assert tmpdir in result
            finally:
                echo_module.setvar("template_dir", None)

    def test_site_template_takes_priority(self):
        """Site template_dir takes priority over built-in."""
        with tempfile.TemporaryDirectory() as tmpdir:
            echo_module.setvar("template_dir", tmpdir)
            try:
                result = echo_module._get_template_dirs()
                assert result[0] == tmpdir
            finally:
                echo_module.setvar("template_dir", None)

    def test_no_site_template_works(self):
        """Works when no site template_dir is set."""
        echo_module.setvar("template_dir", None)
        result = echo_module._get_template_dirs()
        assert len(result) >= 1


class TestLoadTemplate:
    """Test _load_template() function."""

    def test_load_existing_template(self):
        """Can load an existing template."""
        result = echo_module._load_template("menu.tpl")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_menu_template_contains_title_placeholder(self):
        """Menu template contains title placeholder."""
        result = echo_module._load_template("menu.tpl")
        assert "{title}" in result

    def test_load_nonexistent_template_raises(self):
        """Loading non-existent template raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            echo_module._load_template("nonexistent.tpl")

    def test_load_all_builtin_templates(self):
        """All built-in templates can be loaded."""
        templates = ["menu.tpl", "form.tpl", "confirm.tpl", "list.tpl", "header.tpl"]
        for tpl in templates:
            result = echo_module._load_template(tpl)
            assert isinstance(result, str)
            assert len(result) > 0


class TestLoadTemplateWithVars:
    """Test load_template() function with variable substitution."""

    def test_simple_variable_substitution(self):
        """Simple variable substitution works."""
        result = echo_module.load_template("menu.tpl", title="Main Menu")
        assert "{title}" not in result
        assert "Main Menu" in result

    def test_multiple_variables(self):
        """Multiple variables are substituted."""
        result = echo_module.load_template(
            "menu.tpl", title="Main Menu", item1="Files", item2="Mail"
        )
        assert "{title}" not in result
        assert "{item1}" not in result
        assert "{item2}" not in result
        assert "Main Menu" in result
        assert "Files" in result
        assert "Mail" in result

    def test_unused_variables_remain(self):
        """Unused variables (not in template) are replaced with empty string."""
        result = echo_module.load_template("menu.tpl", title="Test", extra="unused")
        assert "{title}" not in result
        # "extra" is not a placeholder in menu.tpl, so {extra} is replaced with empty string
        assert "{extra}" not in result
        # "unused" value doesn't appear because the placeholder didn't exist
        assert "unused" not in result

    def test_empty_string_variable(self):
        """Empty string variable is substituted."""
        result = echo_module.load_template("menu.tpl", title="")
        assert "{title}" not in result

    def test_numeric_variable(self):
        """Numeric variable is converted to string."""
        result = echo_module.load_template("list.tpl", item=42)
        assert "{item}" not in result
        assert "42" in result

    def test_special_characters_in_variable(self):
        """Special characters in variables are handled."""
        result = echo_module.load_template("menu.tpl", title="Test & <test>")
        assert "Test & <test>" in result

    def test_preserves_runtime_variables(self):
        """Runtime variables like {var:xxx} are preserved."""
        result = echo_module.load_template("menu.tpl", title="Test")
        assert "{var:titlecolor}" in result
        assert "{var:normalcolor}" in result


class TestEchoTemplate:
    """Test echo_template() function."""

    def test_echo_template_returns_none(self):
        """echo_template returns None (outputs to stdout)."""
        result = echo_module.echo_template("menu.tpl", title="Test")
        assert result is None

    def test_echo_template_with_variables(self):
        """echo_template works with variables."""
        result = echo_module.echo_template(
            "confirm.tpl", title="Confirm", message="Are you sure?"
        )
        assert result is None

    def test_echo_template_all_builtins(self):
        """All built-in templates work with echo_template."""
        echo_module.echo_template("menu.tpl", title="Test", item1="A", item2="B")
        echo_module.echo_template("form.tpl", title="Test", label="Name", value="John")
        echo_module.echo_template("confirm.tpl", title="Test", message="Question")
        echo_module.echo_template("list.tpl", title="Test", item="Item 1")
        echo_module.echo_template("header.tpl", title="Test")


class TestTemplatePriority:
    """Test template loading priority."""

    def test_site_template_overrides_builtin(self):
        """Site template overrides built-in template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_template = os.path.join(tmpdir, "menu.tpl")
            with open(custom_template, "w") as f:
                f.write("CUSTOM TEMPLATE {title}")

            echo_module.setvar("template_dir", tmpdir)
            try:
                result = echo_module.load_template("menu.tpl", title="Test")
                assert "CUSTOM TEMPLATE" in result
                assert "Test" in result
            finally:
                echo_module.setvar("template_dir", None)

    def test_builtin_used_when_no_site_template(self):
        """Built-in template is used when no site template."""
        echo_module.setvar("template_dir", None)
        result = echo_module.load_template("menu.tpl", title="Test")
        assert "===" in result


class TestTemplateEdgeCases:
    """Test edge cases."""

    def test_template_with_no_variables(self):
        """Template with no variables works."""
        result = echo_module.load_template("header.tpl", title="Test")
        assert "Test" in result

    def test_missing_required_variable(self):
        """Missing variable leaves placeholder (intentional behavior)."""
        result = echo_module.load_template("menu.tpl")
        assert "{title}" in result

    def test_template_file_not_found_with_context(self):
        """Error message includes template name."""
        with pytest.raises(FileNotFoundError) as exc_info:
            echo_module._load_template("missing.tpl")
        assert "missing.tpl" in str(exc_info.value)

    def test_empty_template_name(self):
        """Empty template name raises error."""
        with pytest.raises(FileNotFoundError):
            echo_module._load_template("")


class TestTemplateIntegrity:
    """Test template file integrity."""

    def test_menu_template_structure(self):
        """Menu template has expected structure."""
        result = echo_module._load_template("menu.tpl")
        lines = result.split("\n")
        assert len(lines) == 4
        assert "{title}" in lines[0]
        assert "[1]" in lines[1]
        assert "[2]" in lines[2]
        assert "[X]" in lines[3]

    def test_confirm_template_structure(self):
        """Confirm template has expected structure."""
        result = echo_module._load_template("confirm.tpl")
        assert "{title}" in result
        assert "{message}" in result
        assert "[Y]" in result
        assert "[N]" in result

    def test_form_template_structure(self):
        """Form template has expected structure."""
        result = echo_module._load_template("form.tpl")
        assert "{title}" in result
        assert "{label}" in result
        assert "{value}" in result

    def test_list_template_structure(self):
        """List template has expected structure."""
        result = echo_module._load_template("list.tpl")
        assert "{title}" in result
        assert "{item}" in result

    def test_header_template_structure(self):
        """Header template has expected structure."""
        result = echo_module._load_template("header.tpl")
        assert "{title}" in result
        assert "{acs:vline}" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
