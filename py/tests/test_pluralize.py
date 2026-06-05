import sys

import pytest

sys.path.insert(0, "src")

from bbsengine6.util import pluralize


pytestmark = pytest.mark.unit


class TestPluralizeBasics:
    """Core singular/plural/zero behavior with default quantity=True."""

    def test_zero_returns_no_plural(self):
        assert pluralize(0, "apple", "apples") == "no apples"

    def test_one_returns_a_singular(self):
        assert pluralize(1, "apple", "apples") == "a apple"

    def test_two_returns_count_plural(self):
        assert pluralize(2, "apple", "apples") == "2 apples"

    def test_many_returns_count_plural(self):
        assert pluralize(42, "apple", "apples") == "42 apples"

    def test_negative_returns_count_plural(self):
        assert pluralize(-3, "apple", "apples") == "-3 apples"


class TestPluralizeEmoji:
    """Emoji prefix must be separated by exactly one space when present,
    and produce no leading space when empty."""

    def test_emoji_with_zero(self):
        assert (
            pluralize(0, "apple", "apples", emoji=":moneybag:")
            == ":moneybag: no apples"
        )

    def test_emoji_with_one(self):
        assert (
            pluralize(1, "apple", "apples", emoji=":moneybag:") == ":moneybag: a apple"
        )

    def test_emoji_with_many(self):
        assert (
            pluralize(5, "apple", "apples", emoji=":moneybag:") == ":moneybag: 5 apples"
        )

    def test_emoji_with_one_no_emoji_does_not_lead_with_space(self):
        # No emoji must not produce a leading space.
        assert pluralize(1, "apple", "apples") == "a apple"
        assert not pluralize(1, "apple", "apples").startswith(" ")

    def test_emoji_empty_string_same_as_omitted(self):
        assert pluralize(5, "apple", "apples", emoji="") == "5 apples"

    def test_no_double_space_with_emoji(self):
        result = pluralize(5, "apple", "apples", emoji=":moneybag:")
        assert "  " not in result


class TestPluralizeQuantity:
    """quantity=False returns only the noun (with emoji prefix)."""

    def test_quantity_false_zero(self):
        assert pluralize(0, "apple", "apples", quantity=False) == "apples"

    def test_quantity_false_one(self):
        assert pluralize(1, "apple", "apples", quantity=False) == "apple"

    def test_quantity_false_many(self):
        assert pluralize(5, "apple", "apples", quantity=False) == "apples"

    def test_quantity_false_with_emoji_zero(self):
        assert (
            pluralize(0, "apple", "apples", quantity=False, emoji=":m:") == ":m: apples"
        )

    def test_quantity_false_with_emoji_one(self):
        assert (
            pluralize(1, "apple", "apples", quantity=False, emoji=":m:") == ":m: apple"
        )

    def test_quantity_false_with_emoji_many(self):
        assert (
            pluralize(5, "apple", "apples", quantity=False, emoji=":m:") == ":m: apples"
        )


class TestPluralizeDeterminer:
    """Determiner controls the article (or count) used with the singular."""

    def test_default_determiner_is_a(self):
        assert pluralize(1, "apple", "apples") == "a apple"

    def test_explicit_a(self):
        assert pluralize(1, "apple", "apples", determiner="a") == "a apple"

    def test_an(self):
        assert pluralize(1, "apple", "apples", determiner="an") == "an apple"

    def test_the(self):
        assert pluralize(1, "apple", "apples", determiner="the") == "the apple"

    def test_empty_determiner_uses_count(self):
        assert pluralize(1, "apple", "apples", determiner="") == "1 apple"


class TestPluralizeAmountCoercion:
    """amount is coerced to int per the type hint."""

    def test_float_truncates(self):
        # int(1.5) == 1 -> singular
        assert pluralize(1.5, "apple", "apples") == "a apple"

    def test_float_zero(self):
        assert pluralize(0.0, "apple", "apples") == "no apples"

    def test_numeric_string(self):
        # int("5") == 5
        assert pluralize("5", "apple", "apples") == "5 apples"

    def test_true_is_one(self):
        assert pluralize(True, "apple", "apples") == "a apple"

    def test_false_is_zero(self):
        assert pluralize(False, "apple", "apples") == "no apples"

    def test_non_numeric_string_raises(self):
        with pytest.raises(ValueError):
            pluralize("not a number", "apple", "apples")

    def test_none_raises(self):
        with pytest.raises(TypeError):
            pluralize(None, "apple", "apples")


class TestPluralizeFootgunDefaultsRemoved:
    """singular and plural are required; calling without them must TypeError."""

    def test_missing_singular_raises(self):
        with pytest.raises(TypeError):
            pluralize(5, plural="apples")  # type: ignore[call-arg]

    def test_missing_plural_raises(self):
        with pytest.raises(TypeError):
            pluralize(5, singular="apple")  # type: ignore[call-arg]

    def test_missing_both_raises(self):
        with pytest.raises(TypeError):
            pluralize(5)  # type: ignore[call-arg]


class TestPluralizeKwargsContract:
    """**kw is silently absorbed (PEP-tolerant). Conflicts surface as TypeError."""

    def test_extra_kwargs_absorbed(self):
        # Caller-side dict spreading (e.g. **coinres) must not raise when
        # the extra keys do not collide with named parameters.
        result = pluralize(
            5,
            "coin",
            "coins",
            emoji=":moneybag:",
            determiner="a",
            quantity=True,
            value=5,
            some_unused_key="ignored",
        )
        assert result == ":moneybag: 5 coins"

    def test_kwarg_binding_singular_conflicts_with_positional(self):
        with pytest.raises(TypeError):
            pluralize(5, "more coin", "more coins", **{"singular": "coin"})

    def test_kwarg_binding_plural_conflicts_with_positional(self):
        with pytest.raises(TypeError):
            pluralize(5, "more coin", "more coins", **{"plural": "coins"})

    def test_kwarg_binding_amount_conflicts(self):
        with pytest.raises(TypeError):
            pluralize(5, "x", "y", **{"amount": 5})


class TestPluralizeFormatting:
    """Locale/format-spec behavior: :d is deterministic, no thousand-seps."""

    def test_large_count_no_thousands_separator(self):
        # If we ever regress to :n, locales would insert commas.
        result = pluralize(1000000, "coin", "coins")
        assert result == "1000000 coins"
        assert "," not in result

    def test_does_not_call_format_with_locale_separator(self):
        result = pluralize(1234567, "x", "y")
        assert result == "1234567 y"


class TestPluralizeEmptyStringsTolerated:
    """Empty singular/plural strings must not raise (per spec)."""

    def test_empty_singular(self):
        # Produces a slightly odd but valid result; not raising is the contract.
        result = pluralize(1, "", "")
        assert result == "a "

    def test_empty_plural(self):
        result = pluralize(5, "", "")
        assert result == "5 "

    def test_empty_zero(self):
        result = pluralize(0, "", "")
        assert result == "no "
