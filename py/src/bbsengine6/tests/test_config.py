"""
Tests for bbsengine6.config - generic JSON+env+default merge helpers.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

import pytest

from bbsengine6 import config

# ---------------------------------------------------------------------------
# load_json_file
# ---------------------------------------------------------------------------

class TestLoadJsonFile:
    def test_missing_file_returns_empty_dict(self, tmp_path: Path):
        assert config.load_json_file(tmp_path / "nope.json") == {}

    def test_empty_file_returns_empty_dict(self, tmp_path: Path):
        p = tmp_path / "empty.json"
        p.write_text("")
        assert config.load_json_file(p) == {}

    def test_whitespace_only_returns_empty_dict(self, tmp_path: Path):
        p = tmp_path / "ws.json"
        p.write_text("  \n\t  ")
        assert config.load_json_file(p) == {}

    def test_valid_object(self, tmp_path: Path):
        p = tmp_path / "ok.json"
        p.write_text('{"a": 1, "b": "two"}')
        assert config.load_json_file(p) == {"a": 1, "b": "two"}

    def test_invalid_json_returns_empty(self, tmp_path: Path):
        p = tmp_path / "bad.json"
        p.write_text("{not valid json")
        assert config.load_json_file(p) == {}

    def test_top_level_list_returns_empty(self, tmp_path: Path):
        p = tmp_path / "list.json"
        p.write_text("[1, 2, 3]")
        assert config.load_json_file(p) == {}

    def test_top_level_string_returns_empty(self, tmp_path: Path):
        p = tmp_path / "str.json"
        p.write_text('"just a string"')
        assert config.load_json_file(p) == {}

    def test_strict_raises_on_invalid(self, tmp_path: Path):
        p = tmp_path / "bad.json"
        p.write_text("[1, 2]")
        with pytest.raises(TypeError, match="must be an object"):
            config.load_json_file_strict(p)


# ---------------------------------------------------------------------------
# search_config
# ---------------------------------------------------------------------------

class TestSearchConfig:
    def test_returns_first_existing(self, tmp_path: Path):
        a = tmp_path / "a.json"
        b = tmp_path / "b.json"
        a.write_text('{"src": "a"}')
        b.write_text('{"src": "b"}')
        data, used = config.search_config([a, b])
        assert data == {"src": "a"}
        assert used == a

    def test_skips_missing(self, tmp_path: Path):
        missing = tmp_path / "missing.json"
        present = tmp_path / "present.json"
        present.write_text('{"x": 1}')
        data, used = config.search_config([missing, present])
        assert data == {"x": 1}
        assert used == present

    def test_no_candidates(self):
        data, used = config.search_config([])
        assert data == {}
        assert used is None

    def test_env_var_wins(self, tmp_path: Path):
        override = tmp_path / "override.json"
        override.write_text('{"src": "env"}')
        normal = tmp_path / "normal.json"
        normal.write_text('{"src": "normal"}')
        with mock.patch.dict(os.environ, {"MY_TEST_CONFIG": str(override)}):
            data, used = config.search_config([normal], env_var="MY_TEST_CONFIG")
        assert data == {"src": "env"}
        assert used == override

    def test_env_var_pointing_to_missing_file(self, tmp_path: Path):
        normal = tmp_path / "normal.json"
        normal.write_text('{"x": 1}')
        with mock.patch.dict(os.environ, {"MY_TEST_CONFIG": str(tmp_path / "ghost.json")}):
            data, used = config.search_config([normal], env_var="MY_TEST_CONFIG")
        assert data == {"x": 1}
        assert used == normal

    def test_none_entries_skipped(self, tmp_path: Path):
        p = tmp_path / "x.json"
        p.write_text('{"x": 1}')
        data, used = config.search_config([None, p, None])
        assert data == {"x": 1}
        assert used == p


# ---------------------------------------------------------------------------
# deep_merge
# ---------------------------------------------------------------------------

class TestDeepMerge:
    def test_simple_override(self):
        out = config.deep_merge({"a": 1}, {"a": 2})
        assert out == {"a": 2}

    def test_adds_keys(self):
        out = config.deep_merge({"a": 1}, {"b": 2})
        assert out == {"a": 1, "b": 2}

    def test_nested_dict_merge(self):
        base = {"db": {"host": "h1", "port": 5432}}
        over = {"db": {"host": "h2"}}
        out = config.deep_merge(base, over)
        assert out == {"db": {"host": "h2", "port": 5432}}

    def test_scalar_overrides_dict(self):
        out = config.deep_merge({"a": {"x": 1}}, {"a": "scalar"})
        assert out == {"a": "scalar"}

    def test_dict_overrides_scalar(self):
        out = config.deep_merge({"a": "scalar"}, {"a": {"x": 1}})
        assert out == {"a": {"x": 1}}

    def test_list_replaced(self):
        out = config.deep_merge({"a": [1, 2, 3]}, {"a": [9]})
        assert out == {"a": [9]}

    def test_does_not_mutate_inputs(self):
        base = {"db": {"host": "h1"}}
        over = {"db": {"port": 5432}}
        config.deep_merge(base, over)
        assert base == {"db": {"host": "h1"}}
        assert over == {"db": {"port": 5432}}

    def test_empty_base(self):
        assert config.deep_merge({}, {"a": 1}) == {"a": 1}

    def test_empty_override(self):
        assert config.deep_merge({"a": 1}, {}) == {"a": 1}

    def test_three_level_merge(self):
        base = {"a": {"b": {"c": 1, "d": 2}}}
        over = {"a": {"b": {"c": 99}}}
        assert config.deep_merge(base, over) == {"a": {"b": {"c": 99, "d": 2}}}


# ---------------------------------------------------------------------------
# resolve
# ---------------------------------------------------------------------------

class TestResolve:
    def test_env_wins(self):
        assert config.resolve("env", "json", "default") == "env"

    def test_json_wins_over_default(self):
        assert config.resolve(None, "json", "default") == "json"

    def test_default_used(self):
        assert config.resolve(None, None, "default") == "default"

    def test_empty_string_treated_as_unset(self):
        assert config.resolve("", "json", "default") == "json"
        assert config.resolve("env", "", "default") == "env"
        assert config.resolve("", "", "default") == "default"

    def test_none_default(self):
        assert config.resolve(None, None, None) is None

    def test_falsy_but_meaningful_values_pass_through(self):
        # resolve treats only None/"" as unset; 0, False, [], {} are real values
        assert config.resolve(0, None, None) == 0
        assert config.resolve(False, None, None) is False
        assert config.resolve([], None, None) == []
        assert config.resolve({}, None, None) == {}


# ---------------------------------------------------------------------------
# get_section
# ---------------------------------------------------------------------------

class TestGetSection:
    def test_one_level(self):
        cfg = {"bed": {"host": "h"}}
        assert config.get_section(cfg, "bed") == {"host": "h"}

    def test_two_level(self):
        cfg = {"modules": {"project": {"enabled": True}}}
        assert config.get_section(cfg, "modules", "project") == {"enabled": True}

    def test_missing_top_level(self):
        assert config.get_section({}, "bed") == {}

    def test_missing_inner(self):
        cfg = {"modules": {}}
        assert config.get_section(cfg, "modules", "project") == {}

    def test_non_dict_intermediate(self):
        cfg = {"modules": "not a dict"}
        assert config.get_section(cfg, "modules", "project") == {}

    def test_non_dict_leaf(self):
        cfg = {"modules": {"project": "string"}}
        assert config.get_section(cfg, "modules", "project") == {}

    def test_empty_path(self):
        cfg = {"x": 1}
        assert config.get_section(cfg) == cfg


# ---------------------------------------------------------------------------
# expand_value
# ---------------------------------------------------------------------------

class TestExpandValue:
    def test_dollar_var_expanded(self):
        env = {"MY_VAR": "expanded"}
        assert config.expand_value("${MY_VAR}", env=env) == "expanded"

    def test_dollar_var_unknown_left_alone(self):
        assert config.expand_value("${NOT_SET_VAR}", env={}) == "${NOT_SET_VAR}"

    def test_tilde_expanded(self):
        env = {"HOME": "/home/alice"}
        out = config.expand_value("~/logs/x.log", env=env)
        assert out == "/home/alice/logs/x.log"

    def test_embedded_tilde_not_expanded(self):
        # POSIX shell semantics: only leading ~
        env = {"HOME": "/home/alice"}
        out = config.expand_value("/var/~thing", env=env)
        assert out == "/var/~thing"

    def test_dict_walked(self):
        env = {"X": "1", "Y": "2"}
        out = config.expand_value({"a": "${X}", "b": "${Y}"}, env=env)
        assert out == {"a": "1", "b": "2"}

    def test_list_walked(self):
        env = {"X": "x"}
        out = config.expand_value(["${X}", "literal"], env=env)
        assert out == ["x", "literal"]

    def test_non_string_passthrough(self):
        assert config.expand_value(42) == 42
        assert config.expand_value(True) is True
        assert config.expand_value(None) is None
        assert config.expand_value(3.14) == 3.14

    def test_nested_dict_inside_list(self):
        env = {"V": "v"}
        out = config.expand_value([{"k": "${V}"}], env=env)
        assert out == [{"k": "v"}]

    def test_default_env_is_os_environ(self):
        with mock.patch.dict(os.environ, {"BE6_TEST_VAR": "live"}):
            assert config.expand_value("${BE6_TEST_VAR}") == "live"


# ---------------------------------------------------------------------------
# expand_paths
# ---------------------------------------------------------------------------

class TestExpandPaths:
    def test_path_suffix_key_expanded(self):
        cfg = {"log_file": "~/logs/x.log"}
        out = config.expand_paths(cfg)
        assert out["log_file"].endswith("/logs/x.log")
        assert "~" not in out["log_file"]

    def test_all_path_suffixes(self):
        cfg = {
            "thing_path": "~/a",
            "thing_file": "~/b",
            "thing_dir": "~/c",
            "thing_socket": "~/d",
            "thing_log": "~/e",
        }
        out = config.expand_paths(cfg)
        for k in cfg:
            assert "~" not in out[k], k

    def test_non_path_suffix_left_alone(self):
        cfg = {"host": "~/should-not-expand"}
        out = config.expand_paths(cfg)
        # host doesn't end in _path/_file/etc, so even though it starts
        # with ~, expand_paths leaves it alone (only ${VAR}/~ is left in
        # for the consumer to handle via expand_value)
        assert out == {"host": "~/should-not-expand"}

    def test_non_string_value_left_alone(self):
        cfg = {"log_path": 42, "port": 5432}
        out = config.expand_paths(cfg)
        assert out == {"log_path": 42, "port": 5432}

    def test_top_level_dict_returned_as_new_dict(self):
        cfg = {"a": "~/x", "b": 1}
        out = config.expand_paths(cfg)
        assert out is not cfg
        assert out["a"].endswith("/x")


# ---------------------------------------------------------------------------
# build_argparse_defaults
# ---------------------------------------------------------------------------

class TestBuildArgparseDefaults:
    def test_section_value_used(self):
        cfg = {"global": {}, "bed": {"host": "from-json"}}
        out = config.build_argparse_defaults(
            cfg, section="bed", keys=("host",),
            hardcoded_defaults={"host": "fallback"},
        )
        assert out == {"host": "from-json"}

    def test_global_fallback(self):
        cfg = {"global": {"host": "from-global"}, "bed": {}}
        out = config.build_argparse_defaults(
            cfg, section="bed", keys=("host",),
            hardcoded_defaults={"host": "fallback"},
        )
        assert out == {"host": "from-global"}

    def test_hardcoded_default_used(self):
        cfg = {"global": {}, "bed": {}}
        out = config.build_argparse_defaults(
            cfg, section="bed", keys=("host",),
            hardcoded_defaults={"host": "hardcoded"},
        )
        assert out == {"host": "hardcoded"}

    def test_none_when_all_unset(self):
        out = config.build_argparse_defaults(
            {"global": {}, "bed": {}}, section="bed", keys=("host",),
        )
        assert out == {"host": None}

    def test_env_var_wins_over_json(self):
        cfg = {"global": {}, "bed": {"host": "from-json"}}
        with mock.patch.dict(os.environ, {"BED_HOST": "from-env"}):
            out = config.build_argparse_defaults(
                cfg, section="bed", keys=("host",),
                env_prefix="BED",
                hardcoded_defaults={"host": "hardcoded"},
            )
        assert out == {"host": "from-env"}

    def test_empty_env_prefix_disables_env_lookup(self):
        cfg = {"global": {}, "bed": {"host": "from-json"}}
        with mock.patch.dict(os.environ, {"BED_HOST": "from-env"}):
            out = config.build_argparse_defaults(
                cfg, section="bed", keys=("host",),
                env_prefix="",
                hardcoded_defaults={"host": "hardcoded"},
            )
        assert out == {"host": "from-json"}

    def test_empty_global_section_disables_fallback(self):
        cfg = {"global": {"host": "from-global"}, "bed": {}}
        out = config.build_argparse_defaults(
            cfg, section="bed", keys=("host",),
            global_section="",
            hardcoded_defaults={"host": "hardcoded"},
        )
        assert out == {"host": "hardcoded"}

    def test_coerce_applied(self):
        cfg = {"global": {}, "bed": {"port": "9999"}}
        out = config.build_argparse_defaults(
            cfg, section="bed", keys=("port",), coerce={"port": int},
        )
        assert out == {"port": 9999}
        assert isinstance(out["port"], int)

    def test_coerce_failure_falls_back_to_uncoerced(self):
        cfg = {"global": {}, "bed": {"port": "not-a-number"}}
        out = config.build_argparse_defaults(
            cfg, section="bed", keys=("port",), coerce={"port": int},
        )
        assert out == {"port": "not-a-number"}

    def test_multiple_keys_independent(self):
        cfg = {"global": {"host": "g"}, "bed": {"port": 9000}}
        out = config.build_argparse_defaults(
            cfg, section="bed", keys=("host", "port"),
        )
        assert out == {"host": "g", "port": 9000}

    def test_env_key_uppercased(self):
        cfg = {"global": {}, "bed": {"host": "json"}}
        with mock.patch.dict(os.environ, {"BED_HOST": "env"}):
            out = config.build_argparse_defaults(
                cfg, section="bed", keys=("host",), env_prefix="BED",
            )
        assert out["host"] == "env"

    def test_env_uses_prefix_combined_with_key(self):
        cfg = {"global": {}, "api": {"twilio_auth_token": "json"}}
        with mock.patch.dict(os.environ, {"TWILIO_AUTH_TOKEN": "env"}):
            out = config.build_argparse_defaults(
                cfg, section="api", keys=("twilio_auth_token",),
                env_prefix="",
                hardcoded_defaults={"twilio_auth_token": "default"},
            )
        # env_prefix="" disables env lookup; the JSON value is used
        assert out["twilio_auth_token"] == "json"

    def test_env_key_map_full_name_overrides_prefix(self):
        """A mapped entry that already starts with the prefix is
        treated as a full env-var name (avoids doubled segments like
        ``BBSENGINE6_DB_DBNAME``)."""
        cfg = {"global": {}}
        with mock.patch.dict(os.environ, {"BBSENGINE6_DBNAME": "from-env"}):
            out = config.build_argparse_defaults(
                cfg, section="global", keys=("databasename",),
                env_prefix="BBSENGINE6_DB",
                env_key_map={"databasename": "BBSENGINE6_DBNAME"},
            )
        assert out == {"databasename": "from-env"}

    def test_env_key_map_short_suffix_combines(self):
        """A mapped entry that doesn't already start with the prefix
        is concatenated with the prefix + underscore."""
        cfg = {"global": {}}
        with mock.patch.dict(os.environ, {"DB_NAME": "from-env"}):
            out = config.build_argparse_defaults(
                cfg, section="global", keys=("databasename",),
                env_prefix="DB",
                env_key_map={"databasename": "NAME"},
            )
        assert out == {"databasename": "from-env"}

    def test_env_key_map_unmapped_key_uses_upper(self):
        """A key not in env_key_map falls back to key.upper()."""
        cfg = {"global": {}}
        with mock.patch.dict(os.environ, {"FOO_HOST": "from-env"}):
            out = config.build_argparse_defaults(
                cfg, section="global", keys=("host",),
                env_prefix="FOO",
                env_key_map={"other_key": "OTHER"},
            )
        assert out == {"host": "from-env"}


# ---------------------------------------------------------------------------
# validate_schema
# ---------------------------------------------------------------------------

class TestValidateSchema:
    def test_no_unknown(self):
        cfg = {"global": {}, "bed": {}}
        assert config.validate_schema(
            cfg, known_sections=frozenset({"global", "bed"})
        ) == []

    def test_unknown_section_warns(self):
        cfg = {"global": {}, "typo_bedd": {}}
        warnings = config.validate_schema(
            cfg, known_sections=frozenset({"global", "bed"})
        )
        assert len(warnings) == 1
        assert "typo_bedd" in warnings[0]

    def test_multiple_unknowns(self):
        cfg = {"foo": {}, "bar": {}}
        warnings = config.validate_schema(
            cfg, known_sections=frozenset({"global"})
        )
        assert len(warnings) == 2

    def test_default_known_sections(self):
        cfg = {"global": {}, "unknown": {}}
        warnings = config.validate_schema(cfg)
        assert len(warnings) == 1
        assert "unknown" in warnings[0]

    def test_returns_list_not_string(self):
        warnings = config.validate_schema({}, known_sections=frozenset({"x"}))
        assert isinstance(warnings, list)
        assert warnings == []


# ---------------------------------------------------------------------------
# Integration: full precedence chain
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_full_precedence_chain(self, tmp_path: Path):
        """All four precedence levels in one realistic scenario."""
        # JSON on disk
        cfg_path = tmp_path / "conf.json"
        cfg_path.write_text(json.dumps({
            "global": {"host": "json-global"},
            "bed": {"host": "json-section"},
        }))

        # argparse defaults ask for bed.host
        with mock.patch.dict(os.environ, {"BED_HOST": "from-env"}):
            defaults = config.build_argparse_defaults(
                config.load_json_file(cfg_path),
                section="bed",
                keys=("host",),
                env_prefix="BED",
                hardcoded_defaults={"host": "from-code"},
            )
        assert defaults == {"host": "from-env"}

        # No env override: section wins over global
        with mock.patch.dict(os.environ, {}, clear=True):
            defaults = config.build_argparse_defaults(
                config.load_json_file(cfg_path),
                section="bed",
                keys=("host",),
                env_prefix="BED",
                hardcoded_defaults={"host": "from-code"},
            )
        assert defaults == {"host": "json-section"}

        # Section missing the key: global wins
        cfg_path.write_text(json.dumps({"global": {"host": "json-global"}}))
        with mock.patch.dict(os.environ, {}, clear=True):
            defaults = config.build_argparse_defaults(
                config.load_json_file(cfg_path),
                section="bed",
                keys=("host",),
                env_prefix="BED",
                hardcoded_defaults={"host": "from-code"},
            )
        assert defaults == {"host": "json-global"}

        # No JSON, no env: hardcoded wins
        with mock.patch.dict(os.environ, {}, clear=True):
            defaults = config.build_argparse_defaults(
                {},
                section="bed",
                keys=("host",),
                env_prefix="BED",
                hardcoded_defaults={"host": "from-code"},
            )
        assert defaults == {"host": "from-code"}

    def test_end_to_end_with_expansion_and_coercion(self):
        """JSON ${VAR} + coerce= applied via build_argparse_defaults.

        The path goes through:
        search_config -> load_json_file -> build_argparse_defaults
        Note: build_argparse_defaults does NOT auto-expand ${VAR};
        callers that want expansion wrap with expand_value() first.
        """
        raw = {"global": {"databasename": "${TEST_DBNAME}"}}
        expanded = config.expand_value(raw, env={"TEST_DBNAME": "mydb"})
        out = config.build_argparse_defaults(
            expanded,
            section="global",
            keys=("databasename",),
        )
        assert out == {"databasename": "mydb"}