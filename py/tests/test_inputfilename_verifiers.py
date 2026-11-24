"""inputfilename and the file verifiers copied from bbsengine5 work with bbsengine6's inputstring.

inputstring calls verify(buffer, **kwargs); the verifiers take (filename, **kw). inputfilename must not change the
process working directory, and the deprecated verifyFile* names must stay the deprecated aliases, not copies.
"""

import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from bbsengine6 import util


class TestVerifiers(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp()
        os.close(fd)
        self.addCleanup(os.unlink, self.path)

    def test_a_readable_file_passes_the_readable_verifier(self):
        self.assertTrue(util.verifyFileExistsReadable(self.path))

    def test_a_missing_file_fails_the_readable_verifier(self):
        self.assertFalse(util.verifyFileExistsReadable(self.path + ".missing"))

    def test_the_readable_writable_verifier_passes_for_a_writable_file(self):
        self.assertTrue(util.verifyFileExistsReadableWritable(self.path))

    def test_the_verifier_accepts_the_args_keyword_inputstring_passes(self):
        self.assertTrue(util.verifyFileExistsReadable(self.path, args=SimpleNamespace(debug=False)))

    def test_the_deprecated_names_are_the_deprecated_aliases_not_copies(self):
        self.assertTrue(util.verifyFileExistsReadable.__module__ == util.__name__)
        self.assertEqual(util.verifyFileExistsReadable.__name__, "verifyFileExistsReadable")
        self.assertEqual(
            [n for n in dir(util) if n == "verifyFileExistsReadable"].count("verifyFileExistsReadable"), 1)


class TestInputfilename(unittest.TestCase):
    def test_the_working_directory_is_not_changed(self):
        before = os.getcwd()
        with patch.object(util.io, "inputstring", return_value="x"):
            util.inputfilename(None, "name: ", os.path.join(tempfile.gettempdir(), "f.txt"))
        self.assertEqual(os.getcwd(), before)

    def test_inputstring_gets_the_verifier_and_the_default(self):
        seen = {}

        def fake(prompt, default, **kw):
            seen.update(prompt=prompt, default=default, verify=kw.get("verify"))
            return "typed"

        with patch.object(util.io, "inputstring", side_effect=fake):
            result = util.inputfilename(None, "name: ", "/tmp/a.txt", verify=util.verifyFileExistsReadable)
        self.assertEqual(result, "typed")
        self.assertIs(seen["verify"], util.verifyFileExistsReadable)
        self.assertEqual(seen["default"], "/tmp/a.txt")


if __name__ == "__main__":
    unittest.main()
