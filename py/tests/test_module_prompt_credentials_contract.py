"""The login presentation contract: a callable named by auth.presentation must match _stub_prompt_credentials.

prompt_credentials(*, title, header, width) -> (moniker, password). Checked with the same check_signature rule as
authenticate and the loader's access()/init().
"""

import importlib
import unittest

module = importlib.import_module("bbsengine6.module")


class TestPromptCredentialsContract(unittest.TestCase):
    def test_the_stub_is_keyword_only_with_title_header_width(self):
        import inspect
        params = inspect.signature(module._stub_prompt_credentials).parameters
        self.assertEqual(list(params)[:3], ["title", "header", "width"])
        for name in ("title", "header", "width"):
            self.assertEqual(params[name].kind, inspect.Parameter.KEYWORD_ONLY, name)

    def test_a_conforming_presentation_passes_the_check(self):
        def prompt(*, title="login", header=None, width=25, **kwargs) -> tuple[str, str]:
            return ("", "")

        self.assertIsNone(module.check_signature(prompt, module._stub_prompt_credentials, name="prompt_credentials"))

    def test_a_presentation_without_width_is_rejected(self):
        def prompt(*, title="login", header=None, **kwargs) -> tuple[str, str]:
            return ("", "")

        with self.assertRaises(TypeError):
            module.check_signature(prompt, module._stub_prompt_credentials, name="prompt_credentials")

    def test_resolve_callable_names_the_spec_on_a_bad_presentation(self):
        with self.assertRaises((TypeError, ValueError)) as ctx:
            module.resolve_callable("json:dumps", module._stub_prompt_credentials)
        self.assertIn("json:dumps", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
