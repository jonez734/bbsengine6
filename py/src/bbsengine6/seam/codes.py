"""The result-code vocabulary (front-end-seam.md, section 4). Defined once, here.

An application adds its own refusal codes to its own enum, and nowhere else. The generic codes apply
to every application. An application code names a refusal, never a message.
"""

from enum import Enum


class ErrorCode(str, Enum):
    OK = "ok"
    SCOPE_NOT_FOUND = "scope_not_found"
    NOT_IN_SCOPE = "not_in_scope"
    INVALID_ACTION = "invalid_action"
    FORBIDDEN = "forbidden"
    NOT_AUTHENTICATED = "not_authenticated"
    SERVICE_ERROR = "service_error"
