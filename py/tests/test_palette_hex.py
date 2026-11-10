"""RGB <-> hex helpers in io.palette, and the {rgb:...} inline command that uses them."""

import importlib

import pytest

from bbsengine6.io import palette

echo_mod = importlib.import_module("bbsengine6.io.echo")

pytestmark = pytest.mark.unit


# --- rgb_to_hex -----------------------------------------------------------

def test_rgb_to_hex_yellow():
    assert palette.rgb_to_hex(255, 255, 0) == "FFFF00"


def test_rgb_to_hex_bounds():
    assert palette.rgb_to_hex(0, 0, 0) == "000000"
    assert palette.rgb_to_hex(255, 255, 255) == "FFFFFF"


def test_rgb_to_hex_zero_pads_and_is_uppercase():
    assert palette.rgb_to_hex(1, 171, 15) == "01AB0F"


@pytest.mark.parametrize("value", [-1, 256])
def test_rgb_to_hex_out_of_range_is_value_error(value):
    with pytest.raises(ValueError):
        palette.rgb_to_hex(value, 0, 0)


@pytest.mark.parametrize("value", [1.0, "1", None, True])
def test_rgb_to_hex_non_int_is_type_error(value):
    with pytest.raises(TypeError):
        palette.rgb_to_hex(value, 0, 0)


# --- hex_to_rgb -----------------------------------------------------------

def test_hex_to_rgb_yellow():
    assert palette.hex_to_rgb("FFFF00") == (255, 255, 0)


def test_hex_to_rgb_accepts_hash_and_lowercase():
    assert palette.hex_to_rgb("#ffff00") == (255, 255, 0)


@pytest.mark.parametrize("text", ["FFF", "FFFF000", "GG0000", "", "#12345", "#"])
def test_hex_to_rgb_rejects_malformed(text):
    with pytest.raises(ValueError):
        palette.hex_to_rgb(text)


def test_round_trip_both_ways():
    for triplet in [(0, 0, 0), (255, 255, 255), (1, 171, 15), (128, 64, 200)]:
        assert palette.hex_to_rgb(palette.rgb_to_hex(*triplet)) == triplet
    for text in ["000000", "FFFFFF", "01AB0F"]:
        assert palette.rgb_to_hex(*palette.hex_to_rgb(text)) == text


# --- {rgb:...} inline command --------------------------------------------

def _rgb_text(command: str) -> str:
    tokens = list(echo_mod.tokenize(command))
    return tokens[0].text


@pytest.mark.parametrize(
    "command",
    ["{rgb:#FFFF00}", "{rgb:FFFF00}", "{rgb:255,255,0}"],
)
def test_rgb_command_accepts_hex_and_decimal(command):
    assert _rgb_text(command) == "\x1b[38;2;255;255;0m"


def test_rgb_command_background_with_decimal_triplet():
    assert _rgb_text("{rgb:bg,255,255,0}") == "\x1b[48;2;255;255;0m"


def test_rgb_command_rejects_out_of_range_decimal():
    with pytest.raises(ValueError):
        list(echo_mod.tokenize("{rgb:256,0,0}"))
