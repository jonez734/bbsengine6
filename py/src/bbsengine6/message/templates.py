# bbsengine6/message/templates.py
#
# Pure rendering helpers for the message system. No I/O, no policy.
# Mirrors the layering in casino (where rendering lives outside the
# DAL); bbsengine6.message keeps it out of ``service.py`` because the
# functions are stateless and don't depend on the database layer.

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


def render_template(template: str, variables: Dict[str, Any]) -> str:
    """Render a template with variable substitution.

    Variables are in the format ``{variable_name}`` or ``${variable_name}``.
    """
    if not template:
        return ""

    result = template

    for var_name, var_value in variables.items():
        if var_value is None:
            var_value = ""

        result = result.replace("{" + var_name + "}", str(var_value))
        result = result.replace("$" + var_name, str(var_value))

    return result


def render_message_content(
    content: str,
    template: Optional[str],
    template_vars: Optional[Dict[str, Any]],
) -> str:
    """Render message content with optional template.

    If ``template`` is provided, render it with ``template_vars``.
    Otherwise, return ``content`` as-is.
    """
    if template and template_vars:
        return render_template(template, template_vars)

    if template:
        return template

    return content


def parse_variables_from_content(content: str) -> List[str]:
    """Extract variable names from content.

    Finds all ``{variable}`` and ``$variable`` patterns.
    """
    curly_vars = re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", content)
    dollar_vars = re.findall(r"\$([a-zA-Z_][a-zA-Z0-9_]*)", content)

    variables = list(set(curly_vars + dollar_vars))
    return sorted(variables)


def get_builtin_variables() -> Dict[str, Any]:
    """Built-in variables available for all messages."""
    from datetime import datetime

    return {
        "year": datetime.now().year,
        "month": datetime.now().month,
        "day": datetime.now().day,
        "hour": datetime.now().hour,
        "minute": datetime.now().minute,
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
    }


def validate_template(template: str) -> Tuple[bool, List[str]]:
    """Validate a template string. Returns ``(is_valid, errors)``."""
    errors: List[str] = []

    if not template:
        return True, []

    open_curly = template.count("{")
    close_curly = template.count("}")
    if open_curly != close_curly:
        errors.append(
            f"Unmatched curly braces: {open_curly} open, {close_curly} close"
        )

    dollar_open = len(re.findall(r"\$[a-zA-Z_]", template))
    dollar_close = template.count("}")
    if dollar_open != 0 and dollar_open != dollar_close:
        errors.append(
            f"Unmatched $ variables: {dollar_open} open, {dollar_close} close"
        )

    invalid_vars = re.findall(r"\{[^a-zA-Z_]", template)
    if invalid_vars:
        errors.append(f"Invalid variable syntax: {invalid_vars}")

    return len(errors) == 0, errors
