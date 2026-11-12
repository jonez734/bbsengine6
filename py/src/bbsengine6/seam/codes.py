"""The result-code vocabulary (ui-seam.md, section 4). Defined once, here.

A game adds its own refusal codes to this enum, and nowhere else. The generic codes apply to every
game. A game code names a refusal, never a message.
"""

from enum import Enum


class ErrorCode(str, Enum):
    OK = "ok"
    TABLE_NOT_FOUND = "table_not_found"
    NOT_AT_TABLE = "not_at_table"
    INVALID_BET = "invalid_bet"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    INVALID_ACTION = "invalid_action"
    FORBIDDEN = "forbidden"
    SERVICE_ERROR = "service_error"
