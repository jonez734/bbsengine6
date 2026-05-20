# notify/utils.py
# Helper classes for notify demo system: validators, template engine, formatters, config

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict


class AsciiValidator:
    """Validates that input contains only printable ASCII characters."""

    # Printable ASCII range: 0x20 (space) to 0x7E (tilde)
    PRINTABLE_ASCII_MIN = 0x20
    PRINTABLE_ASCII_MAX = 0x7E

    @staticmethod
    def is_valid_char(char: str) -> bool:
        """Check if a single character is valid printable ASCII."""
        if len(char) != 1:
            return False
        code = ord(char)
        return (
            AsciiValidator.PRINTABLE_ASCII_MIN
            <= code
            <= AsciiValidator.PRINTABLE_ASCII_MAX
        )

    @staticmethod
    def is_valid_string(text: str) -> bool:
        """Check if entire string is valid printable ASCII."""
        if not text:
            return True
        return all(AsciiValidator.is_valid_char(c) for c in text)

    @staticmethod
    def validate_or_raise(text: str, context: str = "input") -> None:
        """Raise ValueError if text is not valid printable ASCII."""
        if not AsciiValidator.is_valid_string(text):
            invalid_chars = [
                (i, c, ord(c))
                for i, c in enumerate(text)
                if not AsciiValidator.is_valid_char(c)
            ]
            char_list = "; ".join(
                f"pos {i}: {repr(c)} (0x{code:02x})" for i, c, code in invalid_chars
            )
            raise ValueError(
                f"Invalid characters in {context}: {char_list}. "
                f"Only printable ASCII (0x20-0x7E) allowed."
            )


class TemplateEngine:
    """Renders message templates with variable substitution."""

    DEFAULT_TEMPLATE = "{sender}: {message}"

    @staticmethod
    def validate_template(template: str) -> None:
        """Validate template syntax and required variables."""
        if len(template) > 500:
            raise ValueError(f"Template too long: {len(template)} > 500 chars")

        invalid_pattern = r"\{[^}]*[^a-zA-Z0-9_{}]\}"
        if re.search(invalid_pattern, template):
            raise ValueError("Invalid variable syntax in template")

        if "{message}" not in template:
            raise ValueError("Template must contain {message} variable")

    @staticmethod
    def render(template: str, variables: Dict[str, str]) -> str:
        """Render template with variables, safe string substitution only."""
        TemplateEngine.validate_template(template)

        required = {"{message}"}
        for var in required:
            if var not in template:
                raise ValueError(f"Missing required variable: {var}")

        variable_pattern = r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}"
        used_vars = set(re.findall(variable_pattern, template))

        for var in used_vars:
            if var not in variables:
                raise ValueError(f"Variable {{{var}}} not provided")

        result = template
        for var, value in variables.items():
            result = result.replace(f"{{{var}}}", str(value))

        return result

    @staticmethod
    def get_required_variables(template: str) -> set[str]:
        """Extract set of variable names from template."""
        variable_pattern = r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}"
        return set(re.findall(variable_pattern, template))


class EchoProcessor:
    """Processes echo commands safely."""

    ECHO_PATTERN = r"^!?echo\s+(.*)$"

    @staticmethod
    def is_echo_command(text: str) -> bool:
        """Check if text is an echo command."""
        return bool(re.match(EchoProcessor.ECHO_PATTERN, text, re.IGNORECASE))

    @staticmethod
    def process_echo(text: str) -> str:
        """Execute echo command and return output."""
        match = re.match(EchoProcessor.ECHO_PATTERN, text, re.IGNORECASE)
        if not match:
            raise ValueError("Not an echo command")

        args = match.group(1).strip()

        AsciiValidator.validate_or_raise(args, "echo args")

        try:
            result = subprocess.run(
                ["echo", args],
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            output = result.stdout.rstrip("\n")

            AsciiValidator.validate_or_raise(output, "echo output")

            return output
        except subprocess.TimeoutExpired:
            raise ValueError("Echo command timed out")
        except Exception as e:
            raise ValueError(f"Echo command failed: {e}")


class TimestampFormatter:
    """Formats timestamps in compact format with timezone information."""

    @staticmethod
    def format_compact(dt: Any) -> str:
        """Format datetime as compact timestamp with timezone."""
        if dt is None:
            return "N/A"

        if isinstance(dt, str):
            try:
                if "T" in dt:
                    dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
                else:
                    dt = datetime.fromisoformat(dt)
            except (ValueError, AttributeError):
                return dt

        if not isinstance(dt, datetime):
            return str(dt)

        if dt.tzinfo is None:
            tz_str = "UTC"
        else:
            tz_name = dt.tzname()
            if tz_name and len(tz_name) <= 4:
                tz_str = tz_name
            else:
                offset = dt.strftime("%z")
                if offset:
                    tz_str = f"UTC{offset[:3]}:{offset[3:]}"
                else:
                    tz_str = "UTC"

        today = datetime.now(tz=dt.tzinfo if dt.tzinfo else timezone.utc).date()
        msg_date = dt.date()

        if msg_date == today:
            return f"{dt.strftime('%H:%M:%S')} {tz_str}"
        else:
            return f"{dt.strftime('%Y-%m-%d %H:%M:%S')} {tz_str}"


@dataclass
class DemoConfig:
    """Configuration for the message demo."""

    moniker: str
    template: str = TemplateEngine.DEFAULT_TEMPLATE
    max_messages: int = 50
    check_timeout: float = 2.0
    urgency: str = "ROUTINE"
    enable_echo_commands: bool = True
    rate_limit: int = 100
    clear_prompt_on_timeout: bool = False

    def validate(self) -> None:
        """Validate configuration."""
        if not self.moniker or len(self.moniker) > 50:
            raise ValueError(f"Invalid moniker: {self.moniker}")

        AsciiValidator.validate_or_raise(self.moniker, "moniker")
        TemplateEngine.validate_template(self.template)

        if self.max_messages < 1:
            raise ValueError(f"max_messages must be >= 1, got {self.max_messages}")

        if self.check_timeout <= 0:
            raise ValueError(f"check_timeout must be > 0, got {self.check_timeout}")

        if self.rate_limit < 1:
            raise ValueError(f"rate_limit must be >= 1, got {self.rate_limit}")

        if not isinstance(self.clear_prompt_on_timeout, bool):
            raise ValueError("clear_prompt_on_timeout must be boolean")


__all__ = [
    "AsciiValidator",
    "TemplateEngine",
    "EchoProcessor",
    "TimestampFormatter",
    "DemoConfig",
]
